# DocuMind AI — Backend

FastAPI + SQLAlchemy 2 + Alembic + MySQL (XAMPP) + PyMuPDF + Chroma + Sentence Transformers.
Authenticated users upload text-based PDFs; the backend extracts, chunks and indexes them, and answers
questions from the user's own documents with **validated citations** (document, page, excerpt) or an honest
"insufficient evidence" message.

Project overview, installation, configuration reference and production notes are in the root [README](../README.md); this file holds the
backend details and the per-feature design notes (sections below, oldest first). The React frontend lives in `../frontend`;
`../frontend/docs/API_CONTRACT.md` is the original contract for the first features, and `/openapi.json` is the current, complete one.

## Requirements

- Python 3.11+ (developed and tested on **3.13**, Windows)
- XAMPP with the **MySQL** service (XAMPP ships MariaDB; the schema works on both)
- Internet access once, to download the embedding model (~90 MB). Later runs use the local cache.

## Setup (XAMPP)

1. Install and open XAMPP, then **start the MySQL service** in the XAMPP Control Panel.
2. Open phpMyAdmin (usually http://localhost/phpmyadmin) and create the database, or run this SQL:

   ```sql
   CREATE DATABASE documind_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. Confirm your **actual** MySQL host, port (3306 by default, but check the XAMPP panel) and the `root`
   password. A fresh XAMPP install has an *empty* root password, which is fine for local development only.
   Never use an empty root password in production.
4. Create the virtual environment and install dependencies:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. Configure `.env` (copy `.env.example`) — at minimum `DATABASE_URL` and `JWT_SECRET_KEY`:

   ```bash
   copy .env.example .env          # macOS/Linux: cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as JWT_SECRET_KEY
   ```

   Example `DATABASE_URL` values:

   ```text
   mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/documind_ai?charset=utf8mb4
   mysql+pymysql://root:@127.0.0.1:3306/documind_ai?charset=utf8mb4        (empty password, dev only)
   ```

6. Create the tables with the Alembic migrations (the schema is **not** created with `create_all()`):

   ```bash
   alembic upgrade head
   ```

7. Start the API:

   ```bash
   uvicorn app.main:app --reload
   ```

8. Open http://127.0.0.1:8000/docs (use the port you started uvicorn on; `run.bat` uses 8001) to see and try the API (docs are disabled when `APP_ENV=production`).
   `GET /health` reports whether the database is reachable.

Then start the frontend (`cd ../frontend && npm run dev`). Its `VITE_API_BASE_URL` defaults to
`http://127.0.0.1:8000`, and `FRONTEND_ORIGIN` here must include the frontend's origin
(comma-separate several). Do not run the frontend's `npm run mock` at the same time: it uses port 8000 too.

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL for MySQL/MariaDB (required) |
| `JWT_SECRET_KEY` | Secret used to sign access tokens (required; 32+ random chars in production) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default 30) |
| `FRONTEND_ORIGIN` | Allowed CORS origin(s), comma-separated |
| `LLM_PROVIDER` | `anthropic`, `openai` (any OpenAI-compatible API), `ollama` (free local) or `mock` |
| `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Provider credentials/model (never commit them) |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | `sentence_transformers` (default) or `hashing` (dev/test only) |
| `CHROMA_PERSIST_DIRECTORY`, `UPLOAD_DIRECTORY` | Where vectors and PDFs are stored (outside any static directory) |
| `MAX_UPLOAD_SIZE_MB`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K_RESULTS` | Upload limit and retrieval tuning |
| `RETRIEVAL_MIN_SIMILARITY` | Floor that drops completely unrelated passages (default 0.05). Relevance is judged by the LLM, which answers `INSUFFICIENT_EVIDENCE` when the passages do not answer the question |

Missing/unsafe settings fail fast with a clear message (for example a placeholder secret or
`LLM_PROVIDER=mock` when `APP_ENV=production`).

### Real AI answers vs the development mock

`LLM_PROVIDER=mock` is **development-only**. It needs no key, and every answer starts with
`[DEVELOPMENT MOCK - not a real AI answer]` and simply quotes the retrieved passage that shares the most words with your question (or reports insufficient evidence when none does; it does not understand meaning). Retrieval,
citations and the whole pipeline are real; only the language model is replaced. For real answers set, for example:

```env
LLM_PROVIDER=anthropic
LLM_API_KEY=<your key>
LLM_MODEL=<a model id from your provider>
```

If the key or model is missing, asking a question returns `503 LLM_NOT_CONFIGURED` (never a fake answer).

**Free local option (no API key): Ollama.** Install Ollama from https://ollama.com, run `ollama pull llama3.2:3b`,
then set `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.2:3b` and `LLM_TIMEOUT_SECONDS=240` and restart the API. It runs
on your own computer (CPU-only machines answer slowly, often 20-60 seconds, and small models are less accurate than
hosted ones). `LLM_BASE_URL` defaults to `http://127.0.0.1:11434/v1`.

## API summary (`/api/v1`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Documents | `POST /documents/upload` (202), `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/preview`, `DELETE /documents/{id}`, `POST /documents/{id}/retry` |
| Conversations | `POST/GET /conversations`, `GET/PATCH/DELETE /conversations/{id}`, `POST /conversations/{id}/messages` |
| Insights | `GET /dashboard/stats`, `GET /dashboard/activity`, `GET /analytics/overview` |
| Later features | see the sections below: collections/categories/tags, sharing, search, versions, reviews, conflicts (full list in the root README and `/openapi.json`) |
| Settings | `GET/PATCH /settings/profile` (only `name` can be changed) |

Errors always look like `{ "error": { "code", "message", "details" } }`. Statuses used: 200, 201, 202, 204,
400, 401, 404, 409, 413, 415, 422, 429, 503.

## How it works

1. **Upload** — extension, MIME type, size (streamed, capped) and `%PDF-` header are checked, the file is
   parsed to confirm it is a real PDF, and it is stored under a generated name in `UPLOAD_DIRECTORY/<user id>/`.
   The document is created as `processing` and a background task takes over.
2. **Processing** — PyMuPDF extracts text per page; pages are chunked **without crossing page boundaries** so
   each chunk keeps its page number; chunks are embedded and stored in Chroma with `user_id`,
   `document_id` and `page_number` metadata, and in MySQL (`document_chunks`). A document is `ready` only
   after indexing fully succeeds; failures set `failed` with a readable reason (for example scanned PDFs
   with no text: OCR is not supported). `POST /documents/{id}/retry` re-runs a failed document without
   duplicating vectors.
3. **Asking** — the question is embedded; Chroma is queried with an **owner and document filter**; every hit is
   re-verified against MySQL; a grounded prompt (numbered sources, "answer only from the sources", document
   text treated as untrusted data) goes to the LLM. Citation markers (`[S1]`) are validated against the
   retrieved sources, invented ones are dropped, and the rest are renumbered. If nothing relevant was
   retrieved, or the model cites nothing valid, the answer is the standard insufficient-evidence message.
4. **Persistence** — the question and answer are saved together only when answering succeeded, so a failed
   LLM call never leaves a dangling question.

## Security notes

- Passwords: Argon2id. Tokens: signed JWT with expiry. Login errors never reveal whether the email exists.
- Every document, conversation, message and vector query is authorized for the authenticated user (documents through
  `access_service`: own documents plus collections shared with the user; conversations are private). Resources the caller may not see
  return `404` so ids cannot be probed.
- Uploaded files live outside any static directory under generated names; internal paths are never returned.
- CORS allows only `FRONTEND_ORIGIN`. Stack traces and secrets are never sent to clients.
- Basic in-memory rate limits protect login, registration, uploads and questions.

## Tests

```bash
pytest
```

The suite (293 tests) uses a separate `documind_ai_test` database, builds it with the real Alembic migrations,
and removes it afterwards. Create that empty database once in phpMyAdmin (same charset/collation as above).
Tests use temporary upload/Chroma folders, the tiny deterministic `hashing` embedder (no model download) and
test doubles for the LLM or mocked HTTP for the provider adapters. They cover registration/login/JWT expiry,
cross-user isolation, upload validation, PDF extraction (including scanned/corrupt files), chunk page
metadata, indexing and filtered retrieval, citation validation, insufficient-evidence behaviour, LLM
timeout/rate-limit/missing-key handling, message ordering, deletion cleanup, retry, and per-user analytics.

## Known limitations

- Document processing uses the MySQL-backed job queue (see "Advanced features"); conflict analyses run as FastAPI background
  tasks and are not resumed after a restart (a report older than 30 minutes is shown as interrupted).
- The rate limiter is per process and in memory; use a shared store behind several workers.
- If vector or file cleanup fails after a document is deleted, it is logged (`CLEANUP FAILED`) and the
  leftovers are inert (retrieval re-checks MySQL), but there is no automatic retry job yet.
- Follow-up questions send recent conversation turns to the LLM, but retrieval uses only the current question.
- No OCR: scanned PDFs without a text layer fail with a clear message.
- Only text-based PDFs up to `MAX_UPLOAD_SIZE_MB` are supported; password-protected PDFs are rejected.

---

# Advanced features (v2)

## What was added

| Feature | Backend | Frontend |
|---|---|---|
| Clickable citations + highlights | `GET /documents/{id}/pages/{n}/image`, `GET /documents/{id}/highlights?chunk_id=` (`highlight_service.py`) | `CitationViewer` modal: page navigation, highlight overlay, "Open full PDF" |
| Multi-document Q&A | `rag_service`: per-document balanced retrieval, conflict/insufficient-evidence prompt rules, cap of 20 documents | Document selector with "Select all", "Comparing N documents" banner |
| Background jobs + retries | `job_service.py`, `worker.py`, `/jobs` endpoints, migration `0002` | Queued / Processing (stage + %) / Completed / Failed, Retry buttons |
| Security | Security headers, `no-store` on API responses, page-count limit, route-inventory + isolation tests | - |
| Feedback + evaluation | `/conversations/{c}/messages/{m}/feedback`, `/analytics/{feedback,queries,evaluations}`, `eval_service.py`, migration `0003` | Thumbs + reason/note form, "Answer quality" section on Analytics |

## Design decisions

* **Queue = MySQL, not Celery/Redis.** The `processing_jobs` table is the persistent queue. Workers claim jobs with one
  conditional `UPDATE` (only one can win), a unique `active_key` prevents two active jobs per document, heartbeats let a
  lost job be recovered, and failures retry with exponential backoff (3 attempts). This keeps the stack to XAMPP only.
  Corrupt, empty or password-protected PDFs fail immediately (retrying cannot help); embedding/unexpected errors retry.
  If you later need more throughput, the claim/run functions map directly onto a Celery task.
* **Highlights are never guessed.** The cited chunk's words are aligned with the page's word boxes (PyMuPDF). Rectangles
  are returned only if >= 60% of the passage was located; otherwise `reliable: false` and the viewer just opens the page.
  Citations are the validated ones from the RAG pipeline (retrieved chunks only). Older answers without a chunk id open
  the page without a highlight. Scanned PDFs have no text layer, so they cannot be highlighted (OCR is unsupported).
* **Permissions.** Documents, conversations, messages, feedback, jobs and page images are owner-only and answered with
  404 for other users. Retrieval is limited to the document ids authorized in MySQL and re-checks every hit there. (Sharing with Viewer/Editor roles
  was added later: see "Team sharing and permissions" below, which supersedes the owner-only statements in this section.)
* **Evaluation honesty.** Each metric is tagged `measured` or `automated_estimate`. Precision@K, Recall@K, citation
  correctness, latency and failure rates are measured against hand-labelled pages in `eval/dataset.json`. Faithfulness is
  a lexical word-overlap estimate, not a semantic judgement. With `LLM_PROVIDER=mock` runs are `retrieval_only`.
  The dataset is small (12 questions, 3 synthetic PDFs): treat results as a regression signal, not a benchmark.

## Setup / commands

```
# from backend/ (use the venv python, see run.bat)
python -m alembic upgrade head          # applies every migration through 0008; keeps existing rows
python -m uvicorn app.main:app --reload # API (+ one embedded worker thread)
python -m app.worker                     # optional separate worker; set WORKER_EMBEDDED=false for the API then
python -m app.eval_cli                   # run the RAG evaluation (uses configured embeddings + LLM)
python -m pytest                         # backend tests

# from frontend/
npm run dev | npm run lint | npm test
```

New environment variables (all optional, see `.env.example`): `WORKER_EMBEDDED`, `WORKER_POLL_SECONDS`,
`JOB_MAX_ATTEMPTS`, `JOB_RETRY_BASE_SECONDS`, `JOB_STALE_AFTER_SECONDS`, `MAX_PDF_PAGES`, `MULTI_DOC_MAX_SOURCES`,
`MAX_DOCUMENTS_PER_QUESTION`. Secrets (`JWT_SECRET_KEY`, `LLM_API_KEY`, `DATABASE_URL`) stay in the git-ignored `.env`.

## Known limitations

* No OCR; highlights depend on a PDF text layer.
* Failed-job error text is shown to the owner; internal detail (`error_detail`) is stored but never returned.
* Rate limiting is in-memory (single process). Statistics cover the last 30 days.
* Evaluation faithfulness is lexical; the LLM-as-judge option is not implemented.

## Knowledge organization (collections, categories, tags)

Migration `0004` is additive: it creates `collections`, `collection_documents`, `categories`, `tags`, `document_tags` and
adds a nullable `documents.category_id`. No existing table or row is dropped or rewritten. Apply it to the XAMPP database
with `python -m alembic upgrade head` (reverse with `alembic downgrade 0003`). No new environment variables or dependencies.

Rules: collections, categories and tags belong to one user; names are unique per user (case-insensitive). A document can be in
many collections, has at most one category and any number of tags. Deleting a collection, category or tag never deletes
documents. Another user's ids behave like missing ids (404).

| Endpoint | Purpose |
| --- | --- |
| `GET/POST /collections`, `GET/PATCH/DELETE /collections/{id}` | list (search, sort, pagination) / create / view / edit / delete |
| `POST /collections/{id}/documents` | add documents; `move_from_collection_id` moves them atomically |
| `DELETE /collections/{id}/documents/{document_id}` | remove a document from the collection |
| `GET/POST /categories`, `PATCH/DELETE /categories/{id}` | category CRUD with document counts |
| `GET/POST /tags`, `PATCH/DELETE /tags/{id}` | tag CRUD with document counts |
| `PATCH /documents/{id}/metadata` | set category, tags (by name) and collections without re-uploading |
| `GET /documents?collection_id=&category_id=&tag_id=` | filters (`category_id=0` = uncategorised) |

## Team sharing and permissions (Phase 4)

Migration `0005` is additive: it creates `collection_members` (collection, user, role `viewer`|`editor`, inviter, timestamps;
unique per collection+user). Apply with `python -m alembic upgrade head`; `alembic downgrade 0004` reverses it. No new
dependencies or environment variables. Start the API, worker and frontend exactly as before.

**Permission rules** (all enforced in the backend, in `app/services/access_service.py`, re-read from MySQL on every request):

| | Owner | Editor | Viewer |
| --- | --- | --- | --- |
| See the collection, members, documents; search; ask questions; open PDFs, pages and citations | yes | yes | yes |
| Add *their own* documents to / remove documents from the collection | yes | yes | no |
| Edit category/tags of a shared document, restart its failed processing | yes | yes | no |
| Edit/delete the collection, invite, change roles, revoke members | yes | no | no |
| Leave the collection | n/a | yes | yes |

* A document is readable by its uploader, or through a collection that contains it. Sharing a collection exposes only the
  documents inside it; the owner's other documents stay private and being in one collection grants nothing elsewhere.
* The collection owner can read and manage the collection's documents but only the uploader can delete the file.
* Categories and tags belong to the document's uploader; an editor labelling a shared document uses the uploader's labels.
  Only the uploader can change which collections a document is in.
* "Invitations" are immediate: the owner enters the email of an existing active account and the share is effective at once.
  Unknown email -> 404 `USER_NOT_FOUND` (so owners learn whether an address is registered; the endpoint is rate limited).
* No access -> 404 (existence is not revealed); readable but not allowed -> 403.
* RAG: the authorised document ids are resolved from MySQL before Chroma is queried (the Chroma `user_id` filter was removed
  from retrieval; chunks are still re-verified against MySQL). Unauthorised chunks never reach the model.
* Old answers keep their text, but citations to documents the user can no longer read show no name or excerpt.

| Endpoint | Notes |
| --- | --- |
| `GET /collections?scope=all\|owned\|shared` | now includes shared collections with `role`, `owner_name`, `is_shared`, `member_count` |
| `GET /collections/{id}/members` | any member |
| `POST /collections/{id}/members` `{email, role}` | owner; 409 duplicate, 404 unknown email |
| `PATCH /collections/{id}/members/{user_id}` `{role}` | owner |
| `DELETE /collections/{id}/members/{user_id}` | owner revokes; a member may remove themselves |
| `GET /documents?scope=owned\|shared\|all` | default `owned` (unchanged); documents now carry `role` and `is_owner` |
| `GET /documents/{id}` and `/preview`, `/pages/{n}/image`, `/highlights`, `GET /jobs`, `GET /jobs/{id}` | any role |
| `PATCH /documents/{id}/metadata`, `POST /documents/{id}/retry`, `POST /jobs/{id}/retry` | owner or editor |
| `DELETE /documents/{id}` | uploader only |
| `POST /conversations/{id}/messages` | without `document_ids`, searches every ready document the user may read |

## Advanced search (Phase 3)

`POST /api/v1/search` searches the passages (chunks) of every document the caller may read: their own plus documents in
collections shared with them. It is independent of the AI chat and never calls the LLM.

**Migration `0006`** only adds a `FULLTEXT` index (`ft_chunks_text`) on `document_chunks.extracted_text`; no data changes.
Apply with `python -m alembic upgrade head` (`alembic downgrade 0005` drops it). On XAMPP's MariaDB the index is InnoDB
FULLTEXT; very large existing tables are indexed once during the migration. New optional variables (see `.env.example`):
`SEARCH_RRF_K`, `SEARCH_KEYWORD_WEIGHT`, `SEARCH_SEMANTIC_WEIGHT`, `SEARCH_CANDIDATES`. No new dependencies.

**Architecture** (`app/services/search_service.py`, thin route in `app/api/v1/search.py`):
1. The searchable document set is resolved in MySQL from `access_service` plus the filters (ready documents only).
2. *Keyword*: the query is parsed into "quoted phrases" and loose words (punctuation is discarded, never executed).
   Candidates come from `MATCH ... AGAINST (... IN BOOLEAN MODE)` with all words required (`+word*`, parameterized), restricted to
   the allowed documents and bounded by `SEARCH_CANDIDATES`. Words shorter than 3 letters or in the stop list cannot use the
   index, so a bounded `LIKE` scan inside the allowed documents is used instead. Each candidate is then verified in Python
   (word-start matching, exact phrases) and scored from its own text: 3 per phrase hit, 1 + ln(1 + occurrences) per word,
   +2 when unquoted words appear together in order, plus up to 0.5 from the index relevance. If no document contains every
   word, the search is retried with *any* word and the response carries the warning `relaxed_to_any_term`. File name,
   category and tag matches are returned as metadata matches (`matched_on`: `title`, `tag`, `category`) and rank after passage matches.
3. *Semantic*: the query is embedded with the existing embedder and Chroma is queried with the pre-resolved allowed
   document ids (no user-only filter). Hits below `RETRIEVAL_MIN_SIMILARITY` are dropped; every hit is re-read from MySQL and
   discarded unless its chunk still exists and its document is still allowed. `semantic_similarity` is the raw cosine similarity,
   **not** a probability or confidence.
4. *Hybrid* (default): passage lists from both methods are merged with reciprocal rank fusion,
   `score = w_kw/(k+rank_kw) + w_sem/(k+rank_sem)` (`k` = `SEARCH_RRF_K`, default 60). A passage found by both methods is one entry.
   Passages are grouped per document (one card per document, best 3 passages; document score = best passage).
   Ties break on id, so results are deterministic. If the embedding model or Chroma fails, hybrid falls back to keyword results with
   the warning `semantic_unavailable`; semantic mode returns `503 SEMANTIC_SEARCH_UNAVAILABLE` (no internal details).
5. Filters (`collection_id` - 404 unless the caller can access it, `category_id` - `0` = uncategorised, `tag_id`, `file_type` - `pdf`)
   apply identically in all modes. Sorting: `relevance`, `newest`, `title`. Pagination is over documents found within the candidate
   pool; `total_exact` is `false` when the pool was full (more matches may exist). Nothing is cached.

```
POST /api/v1/search
{"query": "\"retention policy\" records", "mode": "hybrid", "collection_id": null, "category_id": 0,
 "tag_id": null, "file_type": "pdf", "sort_by": "relevance", "page": 1, "page_size": 10}
->
{"query": "...", "mode": "hybrid", "terms": ["retention", "policy", "records"], "phrases": ["retention policy"],
 "items": [{"document_id": 5, "title": "records.pdf", "score": 0.032787, "matched_on": ["text"],
            "passages": [{"chunk_id": "chunk-7", "page_number": 2, "snippet": "...", "keyword_match": true,
                          "keyword_rank": 1, "semantic_rank": 1, "semantic_similarity": 0.42}],
            "total_pages": 4, "category": {"id": 1, "name": "HR"}, "tags": [], "collections": [], "role": "owner", ...}],
 "total": 1, "total_exact": true, "page": 1, "page_size": 10, "pages": 1, "sort_by": "relevance",
 "ranking": {"method": "rrf", "rrf_k": 60, "keyword_weight": 1.0, "semantic_weight": 1.0, "score_type": "reciprocal_rank_fusion"},
 "warnings": []}
```

`score` is only meaningful for ordering within one response (its type is in `ranking.score_type`). A result links to
`/app/documents/{id}?page={n}&chunk={chunk_id}`, which opens the in-app viewer on that page with the passage highlighted.

Security: results, snippets, tags/collections, totals and page counts are computed only from documents the caller may read, so a
revoked member sees nothing from the next request. Run the search tests with `python -m pytest tests/test_search.py`.

Limitations: PDF only; matching is word-start (not arbitrary substrings or typo tolerance); InnoDB FULLTEXT ignores words under
3 letters and common stop words (handled by the `LIKE` fallback, which is slower on very large libraries); at most
`SEARCH_CANDIDATES` passages per method are ranked; at most 5000 allowed documents are passed to Chroma per query; no search
history; no stemming ("retain" does not find "retention").

## Document version history (Phase 5)

**Migration `0007`** (additive) creates `document_versions` and adds nullable pointers `documents.current_version_id`,
`document_chunks.version_id` and `processing_jobs.version_id`. Every existing document becomes **version 1 of itself**: the
document id, its collections, tags, category, memberships, conversations, messages and citations are untouched; the version row
copies the file path/size/pages/status, takes the SHA-256 of the file (NULL if the file is missing) and the existing chunks and
jobs are linked to it. Files are only read, never moved. Apply with `python -m alembic upgrade head`.
Roll back with `python -m alembic downgrade 0006`: the pre-versioning columns of `documents` always mirror the current version,
so the old schema keeps working; rows of older versions are dropped with the table (their files stay on disk) and passages of
non-current versions are deleted so they cannot be mistaken for current ones. No new dependencies or environment variables.

**Model.** `document_versions(id, document_id, version_number, original_filename, storage_path, file_size, mime_type,
checksum_sha256, total_pages, processing_status, processing_error, created_by, change_note, restored_from_version_id, created_at)`,
unique on `(document_id, version_number)`. Each version has its own immutable file (`uploads/<uploader>/<uuid>.pdf`), its own
chunks (`document_chunks.version_id`) and its own jobs. The logical document keeps its id and name; `documents.storage_path`,
`file_size`, `total_pages` and `processing_status` mirror the current version, so "current" preview/page images keep working.
Extracted text is stored as that version's chunks; comparison re-extracts text from the immutable file.

**Lifecycle.** `POST /documents/{id}/versions` (owner/editor) validates the PDF with the normal upload rules, stores it under a new
name, computes SHA-256 and, while holding a row lock on the document, allocates the next number and queues a job. At most one
version per document is processed at a time (409 `VERSION_IN_PROGRESS`), so numbers cannot collide; a file identical to the current
version is refused (409 `DUPLICATE_VERSION`, nothing stored). The worker chunks, embeds and indexes the version; **only then**, in one
transaction, `current_version_id` moves to it. Until that moment, and if it fails, the previous version stays current, searchable and
downloadable. Failed versions can be retried (`POST .../versions/{vid}/retry`, or `/jobs/{id}/retry`), always for that version.
Re-indexing is idempotent (a retry first removes that version's chunks/vectors; vectors use `upsert`).

**Restore.** `POST .../versions/{vid}/restore` never rewrites history: the old file is copied into a new version N+1 (note
"Restored from version k"), processed like any upload and made current only when ready. Restoring the current or a non-ready version
is refused; repeated or concurrent submissions get 409.

**Compare.** `GET .../versions/compare?from={vid}&to={vid}` extracts reading-order text units (sentences within paragraph blocks,
`pdf_service.extract_units`) and aligns them with `difflib.SequenceMatcher` (`version_diff_service`, no LLM). Response blocks:
`equal` (context), `skipped`, `added`, `removed`, `changed` (with a word-level `inline` diff). Pages are reported but not compared, so
moved text is not a change. Failed/missing/empty/too large (> 4000 units) versions return `comparable: false` with a reason. The
notice states that this is a text comparison, not a visual or layout comparison.

**Vectors and retrieval.** New vectors carry `document_id`, `version_id`, `page_number`, `chunk_id` (and the uploader id, no longer
used for filtering). Retrieval is constrained to each document's current version in three independent ways: keyword search joins
`document_chunks.version_id = documents.current_version_id`; every semantic/RAG hit is re-read from MySQL and dropped unless its chunk
belongs to the current version of an authorized document; and when a version is activated the superseded version's vectors are
removed from Chroma by chunk id (their MySQL passages and files stay for history). Legacy vectors without `version_id` are handled
because the check is on MySQL, not on the Chroma metadata, and no re-embedding is required.

**Citations.** New citations include `version_id` and `version_number`; reading a conversation adds `version_is_current`. Old
answers are never rewritten (old citations without a version resolve through their chunk, which was backfilled to version 1).
Highlights are located in the file of the version the passage came from; `GET /documents/{id}/pages/{n}/image?version_id=` and
`GET /documents/{id}/preview?version_id=` serve a specific version. If access is lost, citations lose name, excerpt, chunk and version.

| Endpoint | Who |
| --- | --- |
| `GET /documents/{id}/versions`, `GET .../versions/{vid}`, `GET .../versions/{vid}/download[?inline=true]`, `GET .../versions/compare?from=&to=` | any role that can read the document |
| `POST /documents/{id}/versions` (multipart `file`, optional `change_note`) | owner / editor |
| `POST .../versions/{vid}/restore`, `POST .../versions/{vid}/retry` | owner / editor |

Documents now expose `version_number` (the current one). Deleting a document by its uploader removes every version file and vector.
Run the tests with `python -m pytest tests/test_versions.py tests/test_version_migration.py`.

Limitations: comparison is text-only and cannot see images/layout; scanned PDFs (no text) cannot be compared; the logical document
name does not change when a version has a different file name (each version keeps its own file name); one version is processed at a
time per document; old versions are never purged automatically; an uploaded version is stored under the uploader's folder.

## Content review and potential-conflict detection (Phase 6)

**Migration `0008`** (additive, new tables only): `document_reviews`, `document_review_history`, `conflict_reports`,
`document_conflicts`, `conflict_decisions`. Apply with `python -m alembic upgrade head`; `alembic downgrade 0007` drops those five
tables (documents, versions and all earlier data are untouched; review schedules, review history, conflict reports and reviewer
decisions recorded since the upgrade are lost). New optional variables (see `.env.example`): `REVIEW_DUE_SOON_DAYS` (14),
`CONFLICT_MIN_SIMILARITY` (0.5), `CONFLICT_MAX_PAIRS` (12), `CONFLICT_MAX_PASSAGES` (40), `CONFLICT_NEIGHBOURS` (3). No new dependencies.

### Review scheduling
*Design:* a schedule belongs to the **logical document**, not to a version (a review asks "is this content still right?", and uploading
a version must not reset or move the schedule). The version that was reviewed is stored in the append-only history, and the API
reports `version_changed_since_review` when a newer version is current. Reviews never change the current version.

*Date policy:* the server works in **UTC**. "Today" is the UTC calendar date; review dates are plain dates; timestamps are stored as
naive UTC and sent with a trailing `Z`. A date rolls over at 00:00 UTC for everyone.

*Status is derived on every read (nothing is stored, no scheduler runs):*

| Status | Rule |
| --- | --- |
| `in_review` | someone started a review that is not completed (explicit flag) |
| `not_scheduled` | no next date and never reviewed |
| `reviewed` | no next date, but a review was completed |
| `overdue` | next date is before today |
| `due` | next date is today, or within `REVIEW_DUE_SOON_DAYS` days |
| `upcoming` | next date is further away |

*Transitions:* `PUT` sets interval/date/notes/assigned reviewer (past dates, > 10 years ahead and intervals outside 1-3650 are rejected;
an interval without a date starts counting today); `start` sets `in_review`; `complete` appends a history row (reviewer = the
signed-in user, never a request field; version = the current version; outcome `approved | changes_required | outdated |
needs_clarification`; previous and next date), clears `in_review` and sets the next date to the given date, else today + interval, else none
(`reviewed`); `DELETE` clears the schedule (history is kept). Assigned reviewers must be active users with editor access to the document.

| Endpoint | Who |
| --- | --- |
| `GET /documents/{id}/review`, `GET /documents/{id}/review/history` | any role that can read the document |
| `PUT` / `DELETE /documents/{id}/review`, `POST .../review/start`, `POST .../review/complete` | owner / editor |
| `GET /reviews` (filters `status`, `collection_id`, `due_before`, `due_after`, `reviewer_id`, `assigned_to_me`, `search`, `sort`, pagination), `GET /reviews/overdue`, `GET /reviews/summary` | only documents the caller can read |

The summary's numbers are computed with SQL over the review dates of readable documents; nothing else is shown.

### Potential conflicts
User-initiated and bounded; nothing runs automatically. `POST /conflicts/analyze {document_id | collection_id}` (owner/editor of the
scope; 202) creates a report and runs it as a background task; poll `GET /conflicts/reports/{id}` (reports are private to their author;
a `running` report older than 30 minutes is shown as failed/interrupted).

1. *Scope and authorization:* the allowed document ids are resolved in MySQL (`access_service`) before any text is read, and re-checked
   when the background task starts. A document analysis compares against other documents the user can read; a collection analysis
   compares the collection's documents with each other.
2. *Passages:* claim-like passages (numbers, deadlines, must/shall/limits) of the **current** versions, at most `CONFLICT_MAX_PASSAGES`.
3. *Matching (no LLM):* nearest passages through the existing embeddings and Chroma, restricted to the allowed documents and re-verified in
   MySQL (current version only); plus, for one document, the closest passage of its previous processed version. Pairs are deduplicated,
   identical wording is dropped, pairs whose numbers differ go first, and at most `CONFLICT_MAX_PAIRS` pairs are judged.
4. *Judging:* one LLM call per pair containing only the two passages (never whole documents, never unauthorized text), asking for
   `conflict | compatible | unclear` as JSON. The reply is validated with Pydantic; unreadable replies are counted and ignored. A
   `conflict` verdict is kept as `potential_conflict` only if both quoted evidence strings appear verbatim in their passages; otherwise
   it is stored as `needs_review`. `compatible` verdicts are not stored. Provider failures stop the run and are reported without
   internal details.
5. *Storage:* `document_conflicts` keeps document, **version**, chunk, page and a copy of each passage, the model's explanation and type,
   and `assessment` (what the AI said: `potential_conflict | needs_review`). `review_status` (`pending | confirmed | not_conflict |
   needs_review`) is what a person decided; every decision is appended to `conflict_decisions`. The same evidence pair is never stored twice.

*Version safety:* evidence is pinned to the exact versions that produced it and is never rewritten. `stale` is derived: a source version is
no longer current (for a between-versions finding only the newer side counts), so the UI recommends re-analysis. Opening evidence uses
`?page=&chunk=&version=` so the historical file and page open. *Permissions are checked on every read:* a finding is returned only while the
caller can read **both** source documents (otherwise it is absent, with no title, excerpt or version, and its id is 404); viewers can
inspect but only editors of both documents can decide; nothing is cached.

| Endpoint | Who |
| --- | --- |
| `POST /conflicts/analyze` | owner / editor of the document or collection |
| `GET /conflicts/reports`, `GET /conflicts/reports/{id}` | the author |
| `GET /conflicts` (filters `review_status`, `assessment`, `document_id`, `collection_id`, `report_id`, `stale`), `GET /conflicts/{id}`, `GET /conflicts/{id}/decisions` | readers of both documents |
| `PATCH /conflicts/{id}/decision` `{decision, note}` | editors of both documents |

Tests: `python -m pytest tests/test_reviews.py tests/test_conflicts.py`. The LLM is replaced by a test double there, so those tests check this
pipeline (scope, validation, evidence, versions, permissions), not model quality.

Limitations: detection quality depends on the model (a small local model will miss contradictions and sometimes misjudge); only
claim-like passages are examined and at most `CONFLICT_MAX_PAIRS` pairs per run; the previous-version comparison uses word overlap because
superseded versions have no vectors; reports are not resumed after a server restart (shown as interrupted); there are no reminders or
e-mails; the review dashboard shows only documents that have a review record.
