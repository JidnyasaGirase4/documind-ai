"""RAG evaluation harness.

Builds the synthetic corpus from eval/dataset.json as real PDFs under a dedicated (non-loginable) evaluation user, runs
every question through the same retrieval and answering code the app uses, scores it against the hand-labelled
relevant pages, stores the run, then removes the corpus again. User documents are never touched.

How each metric is obtained (stored with the run, so the UI can label it honestly):
  precision_at_k / recall_at_k / citation_correctness  measured against labelled pages (exact, no model involved)
  latency / failure rates                               measured wall-clock / counted
  faithfulness                                          automated estimate: share of the answer's content words found in
                                                        the cited passages (lexical, not a semantic judgement)
  keyword_recall                                        automated: expected keywords present in the answer
Answer-level metrics are only computed when a real LLM is configured; with the dev mock the run is retrieval_only."""

import hashlib
import json
import logging
import secrets
import time
from pathlib import Path

import pymupdf
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.errors import AppError
from app.models.conversation import Conversation
from app.models.document import STATUS_READY, Document, DocumentChunk, DocumentVersion
from app.models.quality import EvalResult, EvalRun
from app.models.user import User
from app.rag.chunker import chunk_pages
from app.services import rag_service, vector_service
from app.services.embedding_service import get_embedder
from app.services.pdf_service import PageText
from app.utils.time import utcnow

logger = logging.getLogger("documind.eval")
DATASET_PATH = BACKEND_DIR / "eval" / "dataset.json"
EVAL_EMAIL = "evaluation@documind.invalid"


def load_dataset(path: Path = DATASET_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def precision_recall(retrieved: list[tuple[str, int]], relevant: list[tuple[str, int]], k: int) -> tuple[float | None, float | None]:
    """Precision@K = relevant retrieved in top K / K retrieved; Recall@K = relevant found / relevant labelled.
    Duplicate pages in the ranking count once (a page is either found or not)."""
    if not relevant:
        return None, None
    top = retrieved[:k]
    unique_hits = {r for r in top if r in set(relevant)}
    precision = len(unique_hits) / len(top) if top else 0.0
    return round(precision, 4), round(len(unique_hits) / len(set(relevant)), 4)


def citation_correctness(cited: list[tuple[str, int]], relevant: list[tuple[str, int]]) -> float | None:
    """Share of the answer's citations that point at a labelled-relevant page. None when nothing was cited."""
    if not cited:
        return None
    rel = set(relevant)
    return round(sum(1 for c in cited if c in rel) / len(cited), 4)


def lexical_faithfulness(answer: str, passages: list[str]) -> float | None:
    words = rag_service._content_words(rag_service._MARKER.sub("", answer))
    if not words:
        return None
    support = set().union(*(rag_service._content_words(p) for p in passages)) if passages else set()
    return round(len(words & support) / len(words), 4)


def _make_pdf(path: Path, pages: list[str]) -> None:
    doc = pymupdf.open()
    for body in pages:
        doc.new_page().insert_textbox(pymupdf.Rect(50, 50, 545, 790), body, fontsize=11)
    path.write_bytes(doc.tobytes())
    doc.close()


def _eval_user(db: Session) -> User:
    from app.core.security import hash_password

    user = db.query(User).filter(User.email == EVAL_EMAIL).first()
    if user is None:
        user = User(name="Evaluation", email=EVAL_EMAIL, password_hash=hash_password(secrets.token_urlsafe(32)), is_active=False)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _build_corpus(db: Session, user: User, dataset: dict) -> dict[int, str]:
    """Indexes the synthetic documents synchronously. Returns {document_id: filename}."""
    folder = settings.upload_path / "_eval"
    folder.mkdir(parents=True, exist_ok=True)
    ids: dict[int, str] = {}
    embedder = get_embedder()
    for name, pages in dataset["documents"].items():
        path = folder / f"{secrets.token_hex(8)}.pdf"
        _make_pdf(path, pages)
        doc = Document(user_id=user.id, original_filename=name, storage_path=str(path), file_size=path.stat().st_size, mime_type="application/pdf", processing_status=STATUS_READY, total_pages=len(pages))
        db.add(doc)
        db.flush()
        version = DocumentVersion(document_id=doc.id, version_number=1, original_filename=name, storage_path=str(path), file_size=doc.file_size, mime_type="application/pdf", total_pages=len(pages), processing_status=STATUS_READY, created_by=user.id)
        db.add(version)
        db.flush()
        doc.current_version_id = version.id
        chunks = chunk_pages([PageText(i + 1, t) for i, t in enumerate(pages)], settings.chunk_size, settings.chunk_overlap)
        rows = [DocumentChunk(document_id=doc.id, version_id=version.id, chunk_index=c.index, page_number=c.page_number, extracted_text=c.text) for c in chunks]
        db.add_all(rows)
        db.flush()
        vids = vector_service.add_chunks(user_id=user.id, document_id=doc.id, chunk_ids=[r.id for r in rows], pages=[r.page_number for r in rows], texts=[r.extracted_text for r in rows], embeddings=embedder.embed([r.extracted_text for r in rows]), version_id=version.id)
        for r, v in zip(rows, vids):
            r.vector_reference = v
        ids[doc.id] = name
    db.commit()
    return ids


def _teardown(db: Session, user: User, doc_ids: list[int]) -> None:
    for doc_id in doc_ids:
        doc = db.get(Document, doc_id)
        if doc is None:
            continue
        try:
            vector_service.delete_document(doc_id)
        except Exception:
            logger.exception("eval cleanup: vectors of %s", doc_id)
        Path(doc.storage_path).unlink(missing_ok=True)
        doc.current_version_id = None
        db.flush()
        db.delete(doc)
    db.query(Conversation).filter(Conversation.user_id == user.id).delete()
    db.commit()


def _mean(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def _pctl(values: list[int], q: float) -> int | None:
    from app.services.quality_service import _percentile

    return _percentile(values, q)


def run_evaluation(db: Session, *, k: int | None = None, dataset_path: Path = DATASET_PATH, answers: bool | None = None) -> EvalRun:
    dataset, digest = load_dataset(dataset_path)
    k = k or settings.top_k_results
    with_answers = (settings.llm_provider.lower() != "mock") if answers is None else answers
    run = EvalRun(
        status="running", dataset_name=dataset["name"], dataset_version=dataset["version"], dataset_hash=digest,
        mode="full" if with_answers else "retrieval_only", judge="heuristic" if with_answers else "none", k=k,
        config={
            "llm_provider": settings.llm_provider if with_answers else None,
            "llm_model": settings.llm_model if with_answers else None,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model if settings.embedding_provider == "sentence_transformers" else settings.embedding_provider,
            "chunk_size": settings.chunk_size, "chunk_overlap": settings.chunk_overlap,
            "min_similarity": settings.retrieval_min_similarity,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    user = _eval_user(db)
    names: dict[int, str] = {}
    try:
        names = _build_corpus(db, user, dataset)
        all_ids = list(names)
        conv = Conversation(user_id=user.id, title="evaluation")
        db.add(conv)
        db.commit()
        for q in dataset["questions"]:
            run.results.append(_evaluate_question(db, user, conv, q, all_ids, names, k, with_answers))
            db.commit()
        run.metrics = _aggregate(run.results, with_answers)
        run.status = "completed"
    except Exception as exc:
        logger.exception("Evaluation run %s failed", run.id)
        db.rollback()
        run = db.get(EvalRun, run.id)
        run.status, run.error = "failed", f"{type(exc).__name__}: {exc}"[:2000]
    finally:
        try:
            _teardown(db, user, list(names))
        except Exception:
            logger.exception("Evaluation cleanup failed")
            db.rollback()
        run = db.get(EvalRun, run.id)
        run.finished_at = utcnow()
        db.commit()
    return run


def _evaluate_question(db, user, conv, q: dict, all_ids: list[int], names: dict[int, str], k: int, with_answers: bool) -> EvalResult:
    relevant = [(r["document"], r["page"]) for r in q.get("relevant", [])]
    res = EvalResult(run_id=0, question_id=q["id"], category=q["category"], question=q["question"], answerable=q["answerable"],
                     expected_answer=q.get("expected_answer"), relevant=q.get("relevant", []), outcome="skipped")
    try:
        t0 = time.perf_counter()
        sources = rag_service._retrieve(db, user, q["question"], all_ids)[:k]
        res.retrieval_ms = int((time.perf_counter() - t0) * 1000)
        retrieved = [(s.document_name, s.page_number) for s in sources]
        res.retrieved = [{"document": d, "page": p} for d, p in retrieved]
        res.precision_at_k, res.recall_at_k = precision_recall(retrieved, relevant, k)
        if not with_answers:
            res.outcome = "skipped"
            res.latency_ms = res.retrieval_ms
            return res

        t1 = time.perf_counter()
        ans = rag_service.answer_question(db, user, conv, q["question"], None)
        res.latency_ms = int((time.perf_counter() - t1) * 1000)
        res.answer = ans.content
        cited = [(c["document_name"], c["page_number"]) for c in ans.citations]
        res.cited = [{"document": d, "page": p, "correct": (d, p) in set(relevant)} for d, p in cited]
        res.outcome = "answered" if ans.citations else "insufficient_evidence"
        if q["answerable"]:
            res.citation_correctness = citation_correctness(cited, relevant)
            if ans.citations:
                res.faithfulness = lexical_faithfulness(ans.content, [c["excerpt"] for c in ans.citations])
                res.faithfulness_method = "lexical"
                kws = q.get("expected_keywords") or []
                if kws:
                    res.keyword_recall = round(sum(1 for w in kws if w.lower() in ans.content.lower()) / len(kws), 4)
        else:
            res.correct_abstention = not ans.citations
    except AppError as exc:
        res.outcome, res.error = "error", f"{exc.code}: {exc.message}"
    except Exception as exc:  # one broken question must not hide the rest
        res.outcome, res.error = "error", f"{type(exc).__name__}: {exc}"[:500]
    return res


def _aggregate(results: list[EvalResult], with_answers: bool) -> dict:
    def metric(value, kind, n, note=""):
        return {"value": value, "kind": kind, "n": n, "note": note}

    ans_q = [r for r in results if r.answerable]
    ret_q = [r for r in ans_q if r.precision_at_k is not None]
    out = {
        "questions": len(results),
        "answerable_questions": len(ans_q),
        "precision_at_k": metric(_mean([r.precision_at_k for r in ret_q]), "measured", len(ret_q), "Against hand-labelled relevant pages."),
        "recall_at_k": metric(_mean([r.recall_at_k for r in ret_q]), "measured", len(ret_q), "Against hand-labelled relevant pages."),
        "retrieval_latency_ms_p50": metric(_pctl([r.retrieval_ms for r in results if r.retrieval_ms is not None], 0.5), "measured", len(results)),
    }
    if with_answers:
        cc = [r.citation_correctness for r in ans_q if r.citation_correctness is not None]
        fa = [r.faithfulness for r in ans_q if r.faithfulness is not None]
        kr = [r.keyword_recall for r in ans_q if r.keyword_recall is not None]
        una = [r for r in results if not r.answerable and r.correct_abstention is not None]
        lat = [r.latency_ms for r in results if r.latency_ms is not None and r.outcome != "error"]
        errors = [r for r in results if r.outcome == "error"]
        out.update({
            "citation_correctness": metric(_mean(cc), "measured", len(cc), "Share of citations that point at a labelled-relevant page."),
            "faithfulness": metric(_mean(fa), "automated_estimate", len(fa), "Lexical: share of the answer's content words present in the cited passages. Not a semantic judgement."),
            "keyword_recall": metric(_mean(kr), "automated_estimate", len(kr), "Expected keywords found in the answer."),
            "correct_abstention_rate": metric(round(sum(1 for r in una if r.correct_abstention) / len(una), 4) if una else None, "measured", len(una), "Unanswerable questions answered with 'insufficient evidence'."),
            "latency_ms_p50": metric(_pctl(lat, 0.5), "measured", len(lat)),
            "latency_ms_p95": metric(_pctl(lat, 0.95), "measured", len(lat)),
            "failure_rate": metric(round(len(errors) / len(results), 4) if results else None, "measured", len(results), "Questions that errored."),
            "abstained_on_answerable": metric(sum(1 for r in ans_q if r.outcome == "insufficient_evidence"), "measured", len(ans_q)),
        })
    return out
