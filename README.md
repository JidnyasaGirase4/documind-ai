# DocuMind AI

DocuMind AI is an AI-powered knowledge management platform for PDF documents. People upload PDFs, organize them, search them,
ask questions and get answers with **citations that open the exact page and highlight the passage**, share collections with
teammates, keep a **version history**, schedule **content reviews**, and run an **AI-assisted check for potential conflicts**
between documents. It runs entirely on your own machine (XAMPP MySQL, local files, local vector index; the AI model can be a
local Ollama model or a hosted API).

> Detailed technical notes per feature (design decisions, rules, endpoint tables, limitations) are in
> [backend/README.md](backend/README.md). The end-user manual is [DocuMind_AI_User_Guide.pdf](DocuMind_AI_User_Guide.pdf).

## Features

| Area | What it does |
| --- | --- |
| Documents | Upload PDFs (type, size, signature and page-count validated), background processing with progress, automatic retries, manual retry |
| AI assistant | Questions over all or selected documents; every answer carries validated citations; honest "not enough evidence" answers; thumbs up/down feedback |
| Citations | Click a citation to open the page in the built-in viewer with the supporting passage highlighted (only when it was located reliably) |
| Knowledge base | Collections (colour, icon), categories, tags, filters, move/organize documents |
| Search | Keyword (MySQL FULLTEXT), semantic (Chroma) and hybrid (reciprocal rank fusion) search with filters, sorting and highlighted snippets |
| Sharing | Share a collection with registered users as **Viewer** or **Editor**; the owner can change roles and revoke access, effective immediately |
| Versions | Upload new versions, compare text, restore an old version as a new one, open historical files; search and AI answers only use the current version |
| Reviews | Review intervals and dates, derived status (upcoming / due / overdue / in review / reviewed), review history with the reviewed version, dashboard |
| Potential conflicts | User-started analysis; evidence from both sources with versions and pages; human decisions recorded; findings follow document permissions |
| Analytics | Document and question statistics, answer-quality panel, RAG evaluation CLI |

## Screenshots

Real screenshots from the running application (sample data).

| | |
|---|---|
| ![Hybrid search](docs/user-guide/screenshots/search.png) **Hybrid search** with highlighted matches | ![Citation viewer](docs/user-guide/screenshots/citation_viewer.png) **Citations** open the exact page with the passage highlighted |
| ![Version history](docs/user-guide/screenshots/version_history.png) **Version history** with restore and compare | ![Version compare](docs/user-guide/screenshots/compare.png) **Text comparison** of two versions |
| ![Conflict finding](docs/user-guide/screenshots/conflict_finding.png) **Potential conflict** with evidence and a human decision | ![Reviews](docs/user-guide/screenshots/reviews_dashboard.png) **Review dashboard** (due, overdue, completed) |

## Architecture

```
Browser (React + Vite + Tailwind, Axios)            http://localhost:5173
        │  JSON over HTTP, Authorization: Bearer <JWT>
        ▼
FastAPI  /api/v1  (auth, documents, versions, collections, search, conversations, reviews, conflicts, ...)
  │  every protected request ──► access_service  (single source of truth: owner / editor / viewer)
  ├─► MySQL / MariaDB (XAMPP)   users, documents, versions, chunks, collections, members, reviews, conflicts, jobs ...
  ├─► Chroma (local folder)     one embedding per passage (metadata: document, version, page, chunk)
  ├─► Upload folder             one immutable PDF file per version
  ├─► Embedding model           sentence-transformers all-MiniLM-L6-v2 (local, downloaded once)
  └─► LLM provider              Ollama (local) | Anthropic | OpenAI-compatible | mock (development only)

Background worker (a thread inside the API by default, or `python -m app.worker`)
  claims jobs from the MySQL `processing_jobs` table → extract text (PyMuPDF) → chunk → embed → index
```

**Request flow for a question:** the API resolves the documents the signed-in user may read from MySQL → Chroma is queried only
for those documents → every hit is re-read from MySQL and kept only if it belongs to the *current version* of an authorized
document → only those passages go to the LLM → the answer's citations are validated against the passages that were sent.

**Why MySQL decides access:** vectors are only an index. Authorization is never inferred from the vector store, so revoking
access or replacing a version takes effect on the next request.

## Technology

Frontend: React 18, Vite 5, Tailwind CSS 3, React Router 6, Axios, Recharts, Lucide icons, Vitest + Testing Library.
Backend: Python 3.11+ (tested on 3.13), FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PyMySQL, PyMuPDF, ChromaDB,
sentence-transformers, Argon2 password hashing, PyJWT. Database: MySQL/MariaDB (XAMPP).

## Repository structure

```
backend/
  app/api/v1/        routes (one module per area)        app/schemas/    Pydantic request/response models
  app/services/      business logic (access, rag, search, versions, reviews, conflicts, jobs, ...)
  app/models/        SQLAlchemy models                    app/repositories/  shared queries
  app/core/          settings, security, error handling   app/rag/         chunking
  app/worker.py      background worker                    app/eval_cli.py   RAG evaluation
  migrations/        Alembic (0001 ... 0008)              tests/            pytest suite (293 tests)
  requirements.txt  .env.example  run.bat  README.md
frontend/
  src/pages/ components/ services/ context/ hooks/ utils/ test/      package.json  .env.example  README.md
docs/user-guide/     source and generator of the user guide PDF
DocuMind_AI_User_Guide.pdf
```

## Prerequisites

* Windows, macOS or Linux (developed on Windows 11), **Python 3.11+**, **Node.js 18+**
* **XAMPP** with the MySQL service (MariaDB 10.4+ works; InnoDB FULLTEXT is used for keyword search)
* About 2 GB of disk for Python packages and the embedding model; internet access once to download the embedding model
* For real AI answers: [Ollama](https://ollama.com) (free, local; CPU-only machines answer in roughly 10-60 s) **or** an API key for a hosted provider

## Install and run (development)

1. **Database.** Start MySQL in the XAMPP Control Panel, then create the database (phpMyAdmin or SQL) and, for tests, a second one:
   ```sql
   CREATE DATABASE documind_ai      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE DATABASE documind_ai_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. **Backend.**
   ```bash
   cd backend
   python -m venv .venv && .venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env                                   # then edit DATABASE_URL, JWT_SECRET_KEY, LLM_* (see below)
   python -m alembic upgrade head                         # creates / upgrades every table (0001 ... 0008)
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   On Windows, `backend\run.bat` starts the API with a virtual environment outside the repository (on the author's machine
   the repository drive is nearly full) on **port 8001**. Use whichever port you like, but set `VITE_API_BASE_URL` and
   `FRONTEND_ORIGIN` to match. `APP_PORT` in `.env` is informational: the port is chosen by the `uvicorn --port` argument.
3. **Frontend.**
   ```bash
   cd frontend
   npm install
   cp .env.example .env        # set VITE_API_BASE_URL to the API address, e.g. http://127.0.0.1:8000
   npm run dev                 # http://localhost:5173
   ```
4. Open http://localhost:5173, create an account, upload a PDF.
5. **API documentation** (development only; disabled when `APP_ENV=production`): `http://127.0.0.1:<port>/docs` (Swagger UI),
   `/redoc`, `/openapi.json`. `GET /health` reports whether the database is reachable.

### Sample data (development only)

`python backend/scripts/seed_demo_data.py` (API must be running; defaults to the demo account on port 8001) uploads six realistic engineering
policy and runbook PDFs and adds collections, categories, tags, review schedules, one completed review and a second version. It skips files that
already exist, so it can be run again. Options: `--api`, `--email`, `--password`.

### Updating an existing database

Always back up first. Then from `backend/`: `python -m alembic current` (shows the applied revision) and
`python -m alembic upgrade head`. Every migration through `0008` is additive: existing documents become *version 1* of
themselves (`0007`), nothing is dropped. To roll back one step: `python -m alembic downgrade -1`. **Downgrading
has data-loss consequences:** below `0008` it drops the review schedules, review history, conflict reports and decisions; below `0007`
it drops the version table (the current file of each document is kept; older versions' files stay on disk but are no longer listed, and the
passages of non-current versions are deleted); below `0005` it drops the sharing memberships; below `0004` it drops collections, categories and tags.
Never downgrade a database you care about without a backup.

## Configuration

All backend settings are read from `backend/.env` (never committed; `.env.example` lists every variable).

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development`, `test` or `production`. Production refuses placeholder secrets, `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=hashing` and a wildcard origin; it also disables `/docs` |
| `DATABASE_URL` | **required** | `mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/documind_ai?charset=utf8mb4` |
| `JWT_SECRET_KEY` | **required** | 32+ random characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Session lifetime |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS origin(s), comma separated |
| `LLM_PROVIDER` | `mock` | `ollama`, `anthropic`, `openai` (any OpenAI-compatible API) or `mock` (development only, answers are labelled) |
| `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL` | empty | Model id, key (hosted providers), base URL (OpenAI-compatible; Ollama defaults to `http://127.0.0.1:11434/v1`) |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS`, `LLM_FREQUENCY_PENALTY` | `60`, `1024`, `0` | Raise the timeout for CPU-only local models (e.g. 300, 350, 0.3) |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | `sentence_transformers`, `all-MiniLM-L6-v2` | `hashing` is a tiny test embedder with weak quality |
| `CHROMA_PERSIST_DIRECTORY`, `UPLOAD_DIRECTORY` | `./data/chroma`, `./data/uploads` | Vector index and PDF files (keep outside any web root; back them up with the database) |
| `MAX_UPLOAD_SIZE_MB`, `MAX_PDF_PAGES` | `20`, `1000` | Upload limits enforced by the backend |
| `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K_RESULTS`, `RETRIEVAL_MIN_SIMILARITY` | `800`, `120`, `5`, `0.05` | Chunking and retrieval tuning |
| `MULTI_DOC_MAX_SOURCES`, `MAX_DOCUMENTS_PER_QUESTION` | `8`, `20` | Multi-document question limits |
| `WORKER_EMBEDDED`, `WORKER_POLL_SECONDS` | `true`, `2` | Run one worker thread inside the API, or `false` + `python -m app.worker` |
| `JOB_MAX_ATTEMPTS`, `JOB_RETRY_BASE_SECONDS`, `JOB_STALE_AFTER_SECONDS` | `3`, `15`, `600` | Retry/backoff and lost-worker recovery |
| `SEARCH_RRF_K`, `SEARCH_KEYWORD_WEIGHT`, `SEARCH_SEMANTIC_WEIGHT`, `SEARCH_CANDIDATES` | `60`, `1.0`, `1.0`, `100` | Hybrid ranking |
| `REVIEW_DUE_SOON_DAYS` | `14` | A review is "due" this many days before its date |
| `CONFLICT_MIN_SIMILARITY`, `CONFLICT_MAX_PAIRS`, `CONFLICT_MAX_PASSAGES`, `CONFLICT_NEIGHBOURS` | `0.5`, `12`, `40`, `3` | Bounds for a conflict analysis (each pair is one LLM call) |
| `RATE_LIMIT_ENABLED` | `true` | In-memory rate limits (login, registration, upload, questions, search, invitations, analysis) |

Frontend (`frontend/.env`): `VITE_API_BASE_URL` (API origin, no trailing slash; code default `http://127.0.0.1:8000`) and
`VITE_MAX_UPLOAD_MB` (display hint only; the backend enforces the real limit).

**Embeddings and Chroma.** The first start downloads `all-MiniLM-L6-v2` (about 90 MB) into the Hugging Face cache; later starts are
offline. Chroma stores vectors in `CHROMA_PERSIST_DIRECTORY` (collection `documind_chunks`, cosine distance). Changing the embedding
model requires re-processing every document (retry or re-upload), because old vectors would no longer be comparable.

**LLM.** Ollama: `ollama pull qwen2.5:3b` (or another model), then `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:3b`,
`LLM_TIMEOUT_SECONDS=300`. Hosted: `LLM_PROVIDER=anthropic` or `openai` with `LLM_API_KEY` and `LLM_MODEL`. A missing key or model
returns a clear `503` instead of a fake answer.

## Tests, lint and build

```bash
# backend (from backend/; needs MySQL running and the documind_ai_test database)
python -m pytest                      # 293 tests; uses an isolated schema built with the real migrations
python -m pytest tests/test_search.py # one area

# frontend (from frontend/)
npm test                              # 100 tests (Vitest + Testing Library)
npm run lint
npm run build                         # production build into frontend/dist
```

Results of the browser verification run (what was tested in a real browser, what failed and was fixed, what was not tested) are in
[docs/RELEASE_VERIFICATION.md](docs/RELEASE_VERIFICATION.md).

The backend tests never touch your development database: they rebuild `documind_ai_test` from the migrations, use temporary
upload/Chroma folders, the hashing embedder and test doubles for the LLM. They do not exercise a real AI model.

## API overview (`/api/v1`)

Errors always look like `{ "error": { "code", "message", "details" } }`. Every route except register/login requires
`Authorization: Bearer <token>`. A resource the caller may not see answers `404` (so ids cannot be probed); a resource they may
see but not change answers `403`. The full, always-current list is the OpenAPI document at `/openapi.json`.

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Documents | `POST /documents/upload`, `GET /documents`, `GET/DELETE /documents/{id}`, `PATCH /documents/{id}/metadata`, `GET /documents/{id}/preview`, `/pages/{n}/image`, `/highlights`, `POST /documents/{id}/retry` |
| Versions | `GET/POST /documents/{id}/versions`, `GET .../versions/compare?from=&to=`, `GET .../versions/{vid}`, `/download`, `POST .../restore`, `.../retry` |
| Collections and labels | `/collections` (CRUD, `/documents`, `/members`), `/categories`, `/tags` |
| Search | `POST /search` (`mode`: hybrid, keyword, semantic; filters; sorting; pagination) |
| Assistant | `/conversations` (CRUD), `POST /conversations/{id}/messages`, feedback `PUT/DELETE .../messages/{mid}/feedback` |
| Reviews | `GET /reviews`, `/reviews/summary`, `/reviews/overdue`, `GET/PUT/DELETE /documents/{id}/review`, `POST .../review/start`, `.../review/complete`, `GET .../review/history` |
| Conflicts | `POST /conflicts/analyze`, `GET /conflicts`, `GET /conflicts/{id}`, `PATCH /conflicts/{id}/decision`, `GET /conflicts/{id}/decisions`, `GET /conflicts/reports[/{id}]` |
| Jobs, insights | `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/retry`, `GET /dashboard/stats`, `/dashboard/activity`, `/analytics/*`, `GET/PATCH /settings/profile` |

## Authentication and roles

Passwords use Argon2id; sessions are signed JWTs sent as a Bearer header. A document is readable by its uploader, or through a
collection that contains it (the collection's owner or members). Roles and what they may do are in the table below; the rules live
in `backend/app/services/access_service.py` and every route calls them (tests enumerate every route).

| | Owner | Editor | Viewer |
| --- | :-: | :-: | :-: |
| See documents, search, ask questions, open PDFs, versions, review history, findings | yes | yes | yes |
| Add own documents to / remove documents from the collection | yes | yes | no |
| Edit labels, upload or restore versions, schedule/complete reviews, restart failed processing, run conflict analysis, record decisions | yes | yes | no |
| Edit or delete the collection, invite, change roles, revoke members | yes | no | no |
| Delete the uploaded document itself | uploader only | no | no |

## Feature notes

* **Search.** `POST /search`: keyword uses MySQL FULLTEXT (all words, word-start matching, exact phrases in quotes, +2 when words appear together),
  semantic uses the existing embeddings, hybrid merges both lists with reciprocal rank fusion. Filters: collection, category (`0` = none), tag, file type;
  sorting: relevance, newest, title. Results come only from documents the caller can read and only from their current version.
* **Versions.** A new version becomes current only after it is fully processed; the old one stays active until then and if processing fails.
  Restoring copies an old file into a new latest version. Comparison is text-only (sentences within paragraphs); it cannot see layout or images.
* **Reviews.** Dates are UTC calendar dates. Status is derived from the date on every read (no scheduler). Completing a review records the signed-in
  user, the outcome, notes and the version reviewed.
* **Conflicts.** Findings are *potential* conflicts suggested by the AI model and always need a person's decision. Evidence is stored by exact
  document, version, passage and page; a finding is visible only while the viewer can read both documents.

## Regenerating the user guide

The guide is built from `docs/user-guide/guide_content.py` by `docs/user-guide/build_user_guide.py` (uses PyMuPDF, already a backend dependency):

```bash
cd backend && python ../docs/user-guide/build_user_guide.py      # writes ../DocuMind_AI_User_Guide.pdf
```

The screenshots in `docs/user-guide/screenshots/` were captured from the running application (see the guide's appendix).

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| API does not start: "DATABASE_URL" / "JWT_SECRET_KEY" field required | Create `backend/.env` from `.env.example` |
| `Can't connect to MySQL server` | Start MySQL in XAMPP; check host/port/password in `DATABASE_URL`; `GET /health` shows `database: unreachable` |
| Browser shows a network/CORS error | Add the frontend's exact origin to `FRONTEND_ORIGIN` and restart the API; check `VITE_API_BASE_URL` points to the running API port |
| First upload is slow | The embedding model is loading (first run downloads ~90 MB) |
| Document stays `queued` | The worker is not running: keep `WORKER_EMBEDDED=true` or start `python -m app.worker` |
| Document `failed`: "No extractable text" | Scanned PDF (no text layer). OCR is not supported |
| Answer fails with "AI provider could not be reached" | Start Ollama / check `LLM_PROVIDER`, `LLM_MODEL`, key and base URL |
| Answers take a minute | CPU-only local model; use a smaller model or a hosted provider |
| `alembic` says a table already exists | The database was created with an old `create_all`; restore a backup or start from an empty database |
| Search says "Semantic search is unavailable" | The embedding model could not load; keyword search keeps working |

## Production readiness (what is and is not done)

Done: fail-fast production settings validation, no stack traces or paths in errors, security headers and `no-store` on API responses, Argon2id,
parameterized SQL, upload validation, per-route authorization tests, additive migrations, restart-safe job queue.
**Not done / must be decided before a real deployment:** run behind HTTPS; the JWT lives in `localStorage` (XSS-readable; prefer an HttpOnly cookie);
rate limiting is per process and in memory (use a shared store behind several workers); one embedded worker thread by default (use `python -m app.worker`);
no automated backups of MySQL, `data/uploads` and `data/chroma` (they must be backed up together); no log shipping or monitoring; no OCR; no email notifications;
the Vite dev server is for development only (serve `frontend/dist` from a web server); production CORS must list the real origin.

## Known limitations

No OCR (scanned PDFs fail with a clear message). PDF only. Hybrid/keyword search matches whole-word starts, not typos or stems. Version comparison is text-only.
Conflict detection quality depends on the model; small local models miss contradictions and sometimes misjudge, so every finding needs a human decision.
Dashboard and analytics count only documents the user uploaded. Review dashboard lists documents that have a review record. Reports of a conflict analysis do
not resume after a server restart. See [backend/README.md](backend/README.md) for per-feature limitations.
