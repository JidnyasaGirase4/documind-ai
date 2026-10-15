# DocuMind AI — Backend

FastAPI + SQLAlchemy 2 + Alembic + MySQL (XAMPP) + PyMuPDF + Chroma + Sentence Transformers.
Authenticated users upload text-based PDFs; the backend extracts, chunks and indexes them, and answers
questions from the user's own documents with **validated citations** (document, page, excerpt) or an honest
"insufficient evidence" message.

The React frontend lives in `../frontend` and uses the API documented in `../frontend/docs/API_CONTRACT.md`.
This backend implements that contract (checked end to end in a real browser against this server).

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

8. Open http://127.0.0.1:8000/docs to see and try the API (docs are disabled when `APP_ENV=production`).
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
- Every document, conversation, message and vector query is filtered by the authenticated user. Another
  user's resources return `404` so ids cannot be probed.
- Uploaded files live outside any static directory under generated names; internal paths are never returned.
- CORS allows only `FRONTEND_ORIGIN`. Stack traces and secrets are never sent to clients.
- Basic in-memory rate limits protect login, registration, uploads and questions.

## Tests

```bash
pytest
```

The suite (56 tests) uses a separate `documind_ai_test` database, builds it with the real Alembic migrations,
and removes it afterwards. Create that empty database once in phpMyAdmin (same charset/collation as above).
Tests use temporary upload/Chroma folders, the tiny deterministic `hashing` embedder (no model download) and
test doubles for the LLM or mocked HTTP for the provider adapters. They cover registration/login/JWT expiry,
cross-user isolation, upload validation, PDF extraction (including scanned/corrupt files), chunk page
metadata, indexing and filtered retrieval, citation validation, insufficient-evidence behaviour, LLM
timeout/rate-limit/missing-key handling, message ordering, deletion cleanup, retry, and per-user analytics.

## Known limitations

- Background processing uses FastAPI background tasks inside the API process. If the server stops mid-run, a
  document can stay `processing`; a restart-safe job queue (Celery/RQ) is the next step for production.
- The rate limiter is per process and in memory; use a shared store behind several workers.
- If vector or file cleanup fails after a document is deleted, it is logged (`CLEANUP FAILED`) and the
  leftovers are inert (retrieval re-checks MySQL), but there is no automatic retry job yet.
- Follow-up questions send recent conversation turns to the LLM, but retrieval uses only the current question.
- No OCR: scanned PDFs without a text layer fail with a clear message.
- Only text-based PDFs up to `MAX_UPLOAD_SIZE_MB` are supported; password-protected PDFs are rejected.
