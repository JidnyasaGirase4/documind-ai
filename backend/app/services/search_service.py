"""Keyword, semantic and hybrid search over the passages (chunks) of documents the caller may read.

Order of operations (security first):
  1. the set of searchable documents is resolved in MySQL from access_service + the requested filters;
  2. keyword matching (FULLTEXT) and the Chroma query are both restricted to that set;
  3. every Chroma hit is re-read from MySQL and dropped unless its document is still in the set;
  4. metadata, collections and counts are produced only for those documents.
Nothing is cached, so a revoked share disappears from the very next search."""

import logging
import math
import re
from dataclasses import dataclass

from sqlalchemy import and_, literal, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.document import Document, DocumentChunk
from app.models.knowledge import Category, Collection, CollectionDocument, DocumentTag, Tag
from app.models.user import User
from app.repositories import document_repository as doc_repo
from app.schemas.search import SearchRequest
from app.services import access_service, knowledge_service, vector_service
from app.services.embedding_service import EmbeddingError, get_embedder

logger = logging.getLogger("documind.search")

MAX_TERMS = 8
MAX_PHRASES = 4
MAX_PASSAGES_PER_DOCUMENT = 3
MAX_SEMANTIC_DOCUMENTS = 5000  # upper bound on ids passed to Chroma's $in filter
FT_MIN_TOKEN = 3  # InnoDB ignores shorter words
# Words InnoDB's default FULLTEXT stopword list drops; they are verified in Python instead of sent to the index.
FT_STOPWORDS = {"about", "are", "com", "for", "from", "how", "that", "the", "this", "was", "what", "when", "where", "who", "will", "with", "und", "www"}


class SearchUnavailable(Exception):
    """The semantic half of a search could not run (embedding model or vector store)."""


@dataclass
class Query:
    raw: str
    phrases: list[str]
    terms: list[str]
    semantic_text: str

    @property
    def units(self) -> list[str]:
        return [*self.phrases, *self.terms]

    @property
    def words(self) -> list[str]:
        """Every individual word of the query (phrase words included), de-duplicated, in order."""
        out: list[str] = []
        for unit in self.units:
            for w in re.findall(r"\w+", unit):
                if w not in out:
                    out.append(w)
        return out


def parse_query(raw: str) -> Query:
    """Splits "quoted phrases" from loose words. Punctuation and operator characters are discarded, never executed."""
    phrases: list[str] = []
    for m in re.finditer(r'"([^"]*)"', raw):
        p = " ".join(re.findall(r"\w+", m.group(1).lower()))
        if p and p not in phrases:
            phrases.append(p[:100])
    loose = re.sub(r'"[^"]*"', " ", raw).replace('"', " ")
    terms: list[str] = []
    for w in re.findall(r"\w+", loose.lower()):
        if w not in terms:
            terms.append(w[:50])
    if not phrases and not terms:
        raise AppError(422, "INVALID_QUERY", "Enter at least one word or number to search for.")
    semantic_text = " ".join(loose.split()) or " ".join(phrases)
    return Query(raw=raw, phrases=phrases[:MAX_PHRASES], terms=terms[:MAX_TERMS], semantic_text=semantic_text)


# ----------------------------------------------------------------- scope
def _allowed_ids_stmt(db: Session, user: User, req: SearchRequest):
    """SELECT of document ids the caller may search: readable (own or shared) AND ready AND matching every filter."""
    stmt = select(Document.id).where(Document.id.in_(access_service.readable_document_ids(user.id)), Document.processing_status == "ready")
    if req.collection_id is not None:
        access_service.get_collection(db, user.id, req.collection_id)  # 404 unless owner/member
        stmt = stmt.where(Document.id.in_(select(CollectionDocument.document_id).where(CollectionDocument.collection_id == req.collection_id)))
    if req.category_id is not None:
        stmt = stmt.where(Document.category_id.is_(None) if req.category_id == 0 else Document.category_id == req.category_id)
    if req.tag_id is not None:
        stmt = stmt.where(Document.id.in_(select(DocumentTag.document_id).where(DocumentTag.tag_id == req.tag_id)))
    if req.file_type is not None:
        stmt = stmt.where(Document.mime_type.in_(("application/pdf", "application/x-pdf")))
    return stmt


# --------------------------------------------------------------- matching
def _unit_regex(unit: str) -> re.Pattern:
    """A unit matches at the start of a word, so "retent" finds "retention" but "tent" does not; spaces in a phrase match
    any whitespace."""
    body = r"\s+".join(re.escape(w) for w in unit.split())
    return re.compile(r"(?<!\w)" + body, re.I)


@dataclass
class Match:
    score: float
    first_pos: int
    phrases_hit: int


def _analyse(text: str, q: Query, require_all: bool) -> Match | None:
    """Verifies a passage really contains the query and scores it from the text itself (not from the index):
    3 per exact phrase plus, per term, 1 + ln(1 + occurrences); +2 when unquoted words appear together in query order."""
    score, first, hit_units, phrases_hit = 0.0, None, 0, 0
    for unit in q.units:
        found = list(_unit_regex(unit).finditer(text))
        if not found:
            continue
        hit_units += 1
        if unit in q.phrases:
            phrases_hit += 1
            score += 3.0 + math.log(len(found))
        else:
            score += 1.0 + math.log(1 + len(found))
        pos = found[0].start()
        first = pos if first is None else min(first, pos)
    if hit_units == 0 or (require_all and hit_units < len(q.units)):
        return None
    if len(q.terms) > 1 and not q.phrases and _unit_regex(" ".join(q.terms)).search(text):
        score += 2.0  # the loose words appear together, in query order: treated like a phrase hit
    return Match(score, first or 0, phrases_hit)


def _snippet(text: str, pos: int) -> str:
    n = settings.search_snippet_chars
    if len(text) <= n:
        return text
    start = max(0, pos - n // 4)
    if start > 0:
        cut = text.find(" ", start)
        start = cut + 1 if 0 <= cut < pos else start
    end = min(len(text), start + n)
    if end < len(text):
        cut = text.rfind(" ", start, end)
        end = cut if cut > start else end
    return ("…" if start > 0 else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def _like(value: str):
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


@dataclass
class ChunkHit:
    chunk_id: int
    document_id: int
    page: int
    text: str  # whitespace-normalised
    kw_score: float | None = None
    kw_rank: int | None = None
    similarity: float | None = None
    sem_rank: int | None = None
    score: float = 0.0
    first_pos: int | None = None  # where the first query match starts in `text` (for the snippet)


def _is_current_version():
    """Only passages of a document's CURRENT version are searchable; superseded versions stay in history only."""
    return DocumentChunk.version_id == select(Document.current_version_id).where(Document.id == DocumentChunk.document_id).correlate(DocumentChunk).scalar_subquery()


def _keyword_chunks(db: Session, allowed, q: Query, require_all: bool) -> tuple[list[ChunkHit], bool]:
    limit = settings.search_candidates
    fetch = limit * 4  # headroom: some index candidates fail the exact-phrase / word-start check below
    ft_words = [w for w in q.words if len(w) >= FT_MIN_TOKEN and w not in FT_STOPWORDS and "_" not in w]
    cols = (DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.page_number, DocumentChunk.extracted_text)
    if ft_words:
        boolean = " ".join(f"{'+' if require_all else ''}{w}*" for w in ft_words)
        rel = DocumentChunk.extracted_text.match(boolean).label("rel")  # FULLTEXT relevance, BOOLEAN MODE
        stmt = select(*cols, rel).where(DocumentChunk.extracted_text.match(boolean), DocumentChunk.document_id.in_(allowed), _is_current_version()).order_by(rel.desc(), DocumentChunk.id)
    else:  # only short / stop words: no usable index entries, so a bounded LIKE scan inside the allowed documents
        likes = [DocumentChunk.extracted_text.like(_like(w), escape="\\") for w in q.words]
        stmt = select(*cols, literal(0).label("rel")).where(DocumentChunk.document_id.in_(allowed), _is_current_version(), and_(*likes) if require_all else or_(*likes)).order_by(DocumentChunk.id)
    rows = db.execute(stmt.limit(fetch)).all()
    out: list[ChunkHit] = []
    max_rel = max((float(r.rel or 0) for r in rows), default=0.0) or 1.0
    for r in rows:
        text = " ".join(r.extracted_text.split())
        m = _analyse(text, q, require_all)
        if m is None:
            continue
        hit = ChunkHit(r.id, r.document_id, r.page_number, text, kw_score=m.score + 0.5 * float(r.rel or 0) / max_rel, first_pos=m.first_pos)
        out.append(hit)
    out.sort(key=lambda h: (-h.kw_score, h.chunk_id))
    out = out[:limit]
    for i, h in enumerate(out, 1):
        h.kw_rank = i
    return out, len(rows) >= fetch


def _semantic_chunks(db: Session, allowed, q: Query) -> list[ChunkHit]:
    allowed_ids = list(db.scalars(allowed.limit(MAX_SEMANTIC_DOCUMENTS)))
    if not allowed_ids:
        return []
    try:
        embedding = get_embedder().embed([q.semantic_text])[0]
        hits = vector_service.query(embedding=embedding, document_ids=allowed_ids, k=settings.search_candidates)
    except EmbeddingError as exc:
        logger.error("Search embedding failed: %s", exc)
        raise SearchUnavailable("embedding") from exc
    except Exception as exc:  # Chroma missing / corrupted index
        logger.exception("Vector search failed")
        raise SearchUnavailable("vector_store") from exc
    hits = [h for h in hits if h.similarity >= settings.retrieval_min_similarity]
    chunks = doc_repo.chunks_by_ids(db, [h.chunk_id for h in hits])
    allowed_set = set(allowed_ids)
    current = dict(db.execute(select(Document.id, Document.current_version_id).where(Document.id.in_(allowed_ids))).all())
    out: list[ChunkHit] = []
    for h in sorted(hits, key=lambda x: (-x.similarity, x.chunk_id)):
        c = chunks.get(h.chunk_id)
        # Re-verify against MySQL: the chunk must exist and still belong to a document the caller may search.
        # and belong to the document's current version (superseded versions never surface).
        if c is None or c.document_id != h.document_id or c.document_id not in allowed_set or c.version_id != current.get(c.document_id):
            continue
        out.append(ChunkHit(c.id, c.document_id, c.page_number, " ".join(c.extracted_text.split()), similarity=h.similarity, sem_rank=len(out) + 1))
    return out


def _metadata_matches(db: Session, allowed, q: Query, require_all: bool) -> dict[int, list[str]]:
    """Documents whose file name, category or tags contain the query words. Returns {document_id: [fields]}."""
    conds = []
    for unit in q.units:
        like = _like(unit)
        conds.append(
            or_(
                Document.original_filename.ilike(like, escape="\\"),
                Document.category_id.in_(select(Category.id).where(Category.name.ilike(like, escape="\\"))),
                Document.id.in_(select(DocumentTag.document_id).join(Tag, Tag.id == DocumentTag.tag_id).where(Tag.name.ilike(like, escape="\\"))),
            )
        )
    stmt = select(Document).where(Document.id.in_(allowed), and_(*conds) if require_all else or_(*conds)).order_by(Document.id).limit(settings.search_candidates)
    docs = list(db.scalars(stmt))
    if not docs:
        return {}
    labels = _labels(db, [d.id for d in docs], None)
    out: dict[int, list[str]] = {}
    for d in docs:
        fields: dict[str, str] = {"title": d.original_filename}
        lab = labels[d.id]
        if lab["category"]:
            fields["category"] = lab["category"]["name"]
        if lab["tags"]:
            fields["tag"] = " ".join(t["name"] for t in lab["tags"])
        per_unit = [{f for f, v in fields.items() if _unit_regex(u).search(v)} for u in q.units]
        ok = all(per_unit) if require_all else any(per_unit)
        if ok:
            out[d.id] = sorted(set().union(*per_unit), key=["title", "tag", "category"].index)
    return out


def _labels(db: Session, ids: list[int], viewer_id: int | None):
    return knowledge_service.document_labels(db, ids, viewer_id)


# ---------------------------------------------------------------- ranking
def rrf(ranks: list[tuple[float, int | None]]) -> float:
    """Reciprocal rank fusion: sum of weight / (k + rank) over the lists the item appears in."""
    return sum(w / (settings.search_rrf_k + r) for w, r in ranks if r is not None)


def _rank_chunks(mode: str, kw: list[ChunkHit], sem: list[ChunkHit]) -> dict[int, ChunkHit]:
    merged: dict[int, ChunkHit] = {}
    for h in kw:
        merged[h.chunk_id] = h
    for h in sem:
        cur = merged.get(h.chunk_id)
        if cur is None:
            merged[h.chunk_id] = h
        else:  # the same passage found by both methods: one entry carrying both signals
            cur.similarity, cur.sem_rank = h.similarity, h.sem_rank
    for h in merged.values():
        if mode == "keyword":
            h.score = h.kw_score or 0.0
        elif mode == "semantic":
            h.score = h.similarity or 0.0
        else:
            h.score = rrf([(settings.search_keyword_weight, h.kw_rank), (settings.search_semantic_weight, h.sem_rank)])
    return merged


# ------------------------------------------------------------ orchestration
def search(db: Session, user: User, req: SearchRequest) -> dict:
    q = parse_query(req.query)
    allowed = _allowed_ids_stmt(db, user, req)
    warnings: list[str] = []
    truncated = False

    kw: list[ChunkHit] = []
    meta: dict[int, list[str]] = {}
    if req.mode in ("keyword", "hybrid"):
        kw, truncated = _keyword_chunks(db, allowed, q, require_all=True)
        meta = _metadata_matches(db, allowed, q, require_all=True)
        if not kw and not meta and len(q.units) > 1:
            kw, truncated = _keyword_chunks(db, allowed, q, require_all=False)
            meta = _metadata_matches(db, allowed, q, require_all=False)
            if kw or meta:
                warnings.append("relaxed_to_any_term")  # nothing contained every term, so results contain at least one
    sem: list[ChunkHit] = []
    if req.mode in ("semantic", "hybrid"):
        try:
            sem = _semantic_chunks(db, allowed, q)
            truncated = truncated or len(sem) >= settings.search_candidates
        except SearchUnavailable as exc:
            if req.mode == "semantic":
                raise AppError(503, "SEMANTIC_SEARCH_UNAVAILABLE", "Semantic search is unavailable right now. Try keyword search or try again later.") from exc
            warnings.append("semantic_unavailable")

    chunks = _rank_chunks(req.mode, kw, sem)

    # Group passages by document; a document's score is its best passage's score.
    by_doc: dict[int, list[ChunkHit]] = {}
    for h in chunks.values():
        by_doc.setdefault(h.document_id, []).append(h)
    doc_score: dict[int, float] = {d: max(h.score for h in hs) for d, hs in by_doc.items()}
    n_kw = len(kw)
    for pos, doc_id in enumerate(sorted(meta), 1):  # title/tag/category matches rank after passage matches
        if req.mode == "keyword":
            s = 1.0
        else:
            s = rrf([(settings.search_keyword_weight, n_kw + pos)])
        doc_score[doc_id] = max(doc_score.get(doc_id, 0.0), s)

    docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(list(doc_score) or [0])))} if doc_score else {}
    ordered = [d for d in doc_score if d in docs]
    if req.sort_by == "newest":
        ordered.sort(key=lambda d: (docs[d].created_at, d), reverse=True)
    elif req.sort_by == "title":
        ordered.sort(key=lambda d: (docs[d].original_filename.lower(), d))
    else:
        ordered.sort(key=lambda d: (-doc_score[d], d))

    total = len(ordered)
    start = (req.page - 1) * req.page_size
    page_ids = ordered[start : start + req.page_size]
    items = _build_items(db, user, q, req, page_ids, docs, by_doc, doc_score, meta)

    ranking = {
        "hybrid": dict(method="rrf", rrf_k=settings.search_rrf_k, keyword_weight=settings.search_keyword_weight, semantic_weight=settings.search_semantic_weight, score_type="reciprocal_rank_fusion"),
        "keyword": dict(method="keyword", score_type="keyword_match_score"),
        "semantic": dict(method="semantic", score_type="embedding_cosine_similarity"),
    }[req.mode]
    if req.mode == "hybrid" and "semantic_unavailable" in warnings:
        ranking = dict(method="keyword", score_type="keyword_match_score")
    return {
        "query": req.query,
        "mode": req.mode,
        "terms": q.words,
        "phrases": q.phrases,
        "items": items,
        "total": total,
        "total_exact": not truncated,
        "page": req.page,
        "page_size": req.page_size,
        "pages": max(1, -(-total // req.page_size)),
        "sort_by": req.sort_by,
        "ranking": ranking,
        "warnings": warnings,
    }


def _build_items(db, user, q, req, page_ids, docs, by_doc, doc_score, meta) -> list[dict]:
    if not page_ids:
        return []
    labels = _labels(db, page_ids, user.id)
    roles = access_service.document_roles(db, user.id, page_ids)
    coll_ids = {c for i in page_ids for c in labels[i]["collection_ids"]}
    coll_names = dict(db.execute(select(Collection.id, Collection.name).where(Collection.id.in_(coll_ids or {0}))).all()) if coll_ids else {}
    items = []
    for doc_id in page_ids:
        role = roles.get(doc_id)
        if role is None:  # defence in depth: lost access between the steps of this request
            continue
        d, lab = docs[doc_id], labels[doc_id]
        passages, seen = [], set()
        for h in sorted(by_doc.get(doc_id, []), key=lambda x: (-x.score, x.chunk_id)):
            pos = h.first_pos
            if pos is None:
                m = _analyse(h.text, q, require_all=False)
                pos = m.first_pos if m else 0
            snip = _snippet(h.text, pos)
            if (h.page, snip) in seen:
                continue
            seen.add((h.page, snip))
            passages.append(
                dict(
                    chunk_id=vector_service.vector_id_for(h.chunk_id),
                    page_number=h.page,
                    snippet=snip,
                    keyword_match=h.kw_rank is not None,
                    keyword_rank=h.kw_rank,
                    semantic_rank=h.sem_rank,
                    semantic_similarity=round(h.similarity, 4) if h.similarity is not None else None,
                )
            )
            if len(passages) == MAX_PASSAGES_PER_DOCUMENT:
                break
        matched = list(meta.get(doc_id, []))
        if any(p["keyword_match"] for p in passages):
            matched.insert(0, "text")
        items.append(
            dict(
                document_id=doc_id,
                title=d.original_filename,
                score=round(doc_score[doc_id], 6),
                matched_on=matched,
                passages=passages,
                total_pages=d.total_pages,
                file_type="pdf",
                category=lab["category"],
                tags=lab["tags"],
                collections=[{"id": c, "name": coll_names[c]} for c in lab["collection_ids"] if c in coll_names],
                role=role,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )
    return items
