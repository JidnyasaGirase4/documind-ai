# DocuMind AI --- Backend Implementation Prompt

You are a senior Python backend engineer. Implement the complete backend
for **DocuMind AI**, an AI-powered document intelligence and
knowledge-search platform.

This prompt covers BACKEND ONLY. Implement Python, FastAPI, MySQL using
XAMPP, SQLAlchemy, Alembic, PDF processing, vector indexing, RAG,
authentication, APIs, tests, and backend documentation. Do not build the
React UI. The backend must follow the shared product plan and the API
contract in this prompt.

## 1. Product Requirements

Authenticated users upload text-based PDFs, the backend extracts and
indexes their contents, and users ask questions answered from relevant
document passages with source citations and page references.

Core requirements: - Secure user authentication and ownership checks -
PDF upload, extraction, chunking, embeddings, and vector indexing -
RAG-based question answering - Conversation and message persistence -
MySQL persistence through XAMPP - Accurate citations and honest
insufficient-evidence behavior - API documentation, migrations, tests,
and setup instructions

Do not create mock endpoints that pretend to perform real processing. If
AI credentials are missing, provide an explicit development-only mock
adapter with clearly labeled responses; never describe mock responses as
real AI.

## 2. Required Technology Stack

-   Python 3.11+ (choose a compatible supported version and document it)
-   FastAPI
-   Uvicorn
-   Pydantic settings
-   SQLAlchemy 2.x
-   Alembic
-   MySQL running through XAMPP
-   PyMySQL or a compatible MySQL driver
-   PyMuPDF for PDF text extraction
-   Chroma for vector storage
-   Sentence Transformers or a compatible embedding provider
-   Configurable LLM provider adapter
-   JWT authentication
-   A maintained password-hashing library
-   Pytest and HTTPX for API tests

Keep secrets in `.env`, never hardcode API keys or credentials.

## 3. XAMPP and MySQL Setup

Use XAMPP for the MySQL-compatible database service. XAMPP Control Panel
may label the service "MySQL"; start that service before running
migrations.

Default local assumptions must be configurable: - Host: `127.0.0.1` -
Port: `3306` (confirm in XAMPP) - Database: `documind_ai` - Username:
`root` for a local development-only installation if that is the user's
setup - Password: empty only if the local XAMPP installation is
configured that way

Do not assume root has no password on every machine. Document how to set
the correct credentials.

Create the database using phpMyAdmin or the SQL below:

``` sql
CREATE DATABASE documind_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Example `.env.example`:

``` env
APP_NAME=DocuMind AI API
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173

DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/documind_ai?charset=utf8mb4

JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

LLM_PROVIDER=your_provider
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

CHROMA_PERSIST_DIRECTORY=./data/chroma
UPLOAD_DIRECTORY=./data/uploads
MAX_UPLOAD_SIZE_MB=20
CHUNK_SIZE=800
CHUNK_OVERLAP=120
TOP_K_RESULTS=5
```

Use Pydantic settings to load environment variables. Provide a safe
validation error if required production settings are missing. Add
`.env`, upload data, Chroma files, and secrets to `.gitignore`.

## 4. Backend Architecture

Use a maintainable structure:

``` text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── dashboard.py
│   │       ├── documents.py
│   │       ├── conversations.py
│   │       ├── messages.py
│   │       ├── analytics.py
│   │       └── settings.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── errors.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── document_service.py
│   │   ├── pdf_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_service.py
│   │   ├── rag_service.py
│   │   └── llm_service.py
│   ├── rag/
│   └── utils/
├── migrations/
├── tests/
├── data/
├── .env.example
├── alembic.ini
└── requirements.txt
```

Keep routers thin. Put business logic in services, persistence in
repositories/SQLAlchemy, request/response validation in schemas, and RAG
responsibilities in focused modules.

## 5. SQLAlchemy Models and Database

Create Alembic migrations; do not rely on `create_all()` as the only
production schema-management method.

### users

-   `id` primary key
-   `name`
-   `email` unique and indexed
-   `password_hash`
-   `is_active`
-   `created_at`
-   `updated_at`

### documents

-   `id`
-   `user_id` foreign key
-   `original_filename`
-   `storage_path`
-   `file_size`
-   `mime_type`
-   `processing_status`: uploaded, processing, ready, failed
-   `processing_error` nullable
-   `total_pages` nullable
-   timestamps

### document_chunks

-   `id`
-   `document_id` foreign key
-   `chunk_index`
-   `page_number`
-   `extracted_text`
-   `vector_reference`
-   `created_at`

### conversations

-   `id`
-   `user_id` foreign key
-   `title`
-   `created_at`
-   `updated_at`

### messages

-   `id`
-   `conversation_id` foreign key
-   `role` (user/assistant)
-   `content`
-   `citation_metadata` (JSON where supported)
-   `created_at`

### processing_jobs

-   `id`
-   `document_id` foreign key
-   `status`
-   `retry_count`
-   `error_message`
-   `started_at`
-   `completed_at`
-   `created_at`

Add indexes to foreign keys and common filters. Use UTC timestamps
consistently. Define cascading behavior intentionally. A document
belongs to one user in the initial version; conversations belong to one
user; messages belong to one conversation.

Chroma stores embeddings. MySQL stores relational records and vector
references. Every indexed chunk must have owner/document/page metadata.
Do not put raw vectors in MySQL unless there is a deliberate design
reason.

## 6. Authentication and Security

Implement: - `POST /api/v1/auth/register` - `POST /api/v1/auth/login` -
`GET /api/v1/auth/me`

Requirements: - Validate email and password input. - Enforce unique
email. - Hash passwords using a maintained password-hashing algorithm. -
Return a JWT access token from login. - Verify token signature and
expiry. - Add a reusable current-user dependency. - Return consistent
401/403 errors. - Never return password hashes. - Enforce ownership for
every document, conversation, message, and citation request. - Configure
CORS only for configured frontend origins. - Validate uploaded MIME
type, extension, file size, and actual PDF parsing. - Use generated
storage names and prevent path traversal. - Keep uploads outside public
static directories. - Avoid logging tokens, passwords, secrets, or
sensitive document contents. - Treat document text as untrusted prompt
content. - Filter retrieval by owner/document before sending text to the
LLM. - Add reasonable rate limits or usage controls before public
deployment.

Do not rely on frontend route guards for security.

## 7. PDF Upload and Processing

Implement: - `POST /api/v1/documents/upload` - `GET /api/v1/documents` -
`GET /api/v1/documents/{document_id}` -
`GET /api/v1/documents/{document_id}/preview` -
`DELETE /api/v1/documents/{document_id}` -
`POST /api/v1/documents/{document_id}/retry`

Upload requirements: 1. Validate file size and PDF content. 2. Create a
safe storage filename. 3. Store the file in configured local storage. 4.
Create the document database record. 5. Mark status as processing. 6.
Process in a background task or replaceable job abstraction. 7. Extract
page-aware text using PyMuPDF. 8. Detect PDFs with no usable text and
return a useful explanation that OCR is not supported in the first
version. 9. Chunk text with configurable size and overlap while
preserving page numbers. 10. Generate embeddings and index chunks in
Chroma. 11. Save chunk metadata/vector references in MySQL as
appropriate. 12. Mark ready only after successful indexing. 13. On
failure, mark failed and record a safe, user-readable error. 14. Support
safe retry and avoid duplicate indexing where practical.

For document listing, support pagination, filename search, status
filtering, and sorting. Enforce `user_id` in every query.

For preview, return an authorized streaming response or use a
controlled, short-lived URL. Never expose internal file paths.

On deletion, remove the database records, Chroma vectors, and stored
file safely. Define behavior if one cleanup operation fails; log it and
provide a retryable cleanup strategy.

## 8. RAG and AI Services

Separate these concerns: - PDF text extraction - Chunking - Embedding
provider - Vector storage/retrieval - LLM provider - RAG orchestration

### RAG workflow

1.  Validate authenticated user and conversation ownership.
2.  Validate selected document IDs and their ownership.
3.  Embed the question.
4.  Query Chroma for top-k relevant chunks with owner/document filters.
5.  Verify each returned chunk is authorized and belongs to an
    accessible document.
6.  Build a prompt containing relevant text and citation metadata.
7.  Instruct the LLM to answer only from supplied evidence.
8.  Require the response to include citation references tied to
    retrieved chunk IDs.
9.  Validate citation IDs against the retrieved results.
10. Return answer and source metadata.
11. Save the user message, assistant response, and citations.

Citations must contain real document IDs, original filenames, page
numbers, and a supporting excerpt when available. Never invent a page
number or source. If retrieval is empty or insufficient, return an
honest insufficient-evidence response.

Treat document contents as untrusted text. They must not override system
instructions or cause cross-user data access.

Define configurable interfaces so embedding and LLM providers can be
swapped. Handle missing credentials, timeouts, rate limits, and provider
errors cleanly. Do not silently return fabricated answers.

## 9. Conversations and Messages

Implement: - `POST /api/v1/conversations` -
`GET /api/v1/conversations` -
`GET /api/v1/conversations/{conversation_id}` -
`PATCH /api/v1/conversations/{conversation_id}` -
`DELETE /api/v1/conversations/{conversation_id}` -
`POST /api/v1/conversations/{conversation_id}/messages`

Requirements: - Create a default title that can be renamed. - List
conversations by current user, sorted by updated time. - Paginate
lists. - Return messages in a stable chronological order. - Persist user
question and assistant response. - Validate conversation ownership
before reading/writing. - Update conversation timestamps after new
messages. - Preserve citation metadata with assistant messages. - Return
a consistent response schema for frontend use.

## 10. Dashboard, Analytics, and Settings APIs

Implement: - `GET /api/v1/dashboard/stats` -
`GET /api/v1/dashboard/activity` - `GET /api/v1/analytics/overview` -
`GET /api/v1/settings/profile` - `PATCH /api/v1/settings/profile`

Return real metrics scoped to the current user. Do not hardcode counts.
Validate profile updates and return only supported fields.

## 11. Response Schemas and Error Handling

Use Pydantic schemas for all request and response bodies. Define a
consistent error shape, for example:

``` json
{
  "error": {
    "code": "DOCUMENT_NOT_READY",
    "message": "This document is still being processed.",
    "details": null
  }
}
```

Use appropriate HTTP statuses: - 200 successful read/update - 201
created resource - 202 accepted asynchronous processing - 400 invalid
operation - 401 unauthenticated - 403 unauthorized resource access - 404
resource not found - 413 file too large - 415 unsupported file type -
422 validation error - 429 rate limited - 500 unexpected server error -
503 required AI provider unavailable

Do not reveal internal stack traces or secrets to clients. Enable
FastAPI OpenAPI/Swagger documentation in development.

## 12. Environment and Configuration

Create `.env.example`:

``` env
APP_NAME=DocuMind AI API
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173

DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/documind_ai?charset=utf8mb4

JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

LLM_PROVIDER=your_provider
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

CHROMA_PERSIST_DIRECTORY=./data/chroma
UPLOAD_DIRECTORY=./data/uploads
MAX_UPLOAD_SIZE_MB=20
CHUNK_SIZE=800
CHUNK_OVERLAP=120
TOP_K_RESULTS=5
```

The example uses `YOUR_PASSWORD` intentionally; configure the real
password for your local XAMPP setup. If local root has an empty
password, use the matching local connection string and document that
this is development-only. Never use an empty root password in
production.

Add `.env`, upload files, Chroma data, virtual environments, caches, and
secrets to `.gitignore`.

## 13. XAMPP Setup Instructions to Include in README

1.  Install and open XAMPP.
2.  Start the MySQL service from the XAMPP Control Panel.
3.  Open phpMyAdmin, usually at `http://localhost/phpmyadmin`.
4.  Create a database named `documind_ai` with `utf8mb4` character set
    and `utf8mb4_unicode_ci` collation, or execute:

``` sql
CREATE DATABASE documind_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

5.  Configure `DATABASE_URL` in `.env` with the actual local host, port,
    username, and password.
6.  Create and activate a Python virtual environment.
7.  Install backend dependencies.
8.  Run Alembic migrations.
9.  Start FastAPI using Uvicorn.
10. Open `/docs` to verify the API.

Do not assume XAMPP always uses port 3306 or that root has no password;
tell the developer to confirm their actual configuration.

## 14. Dependencies and Local Run Guide

Provide `requirements.txt` with compatible versions for FastAPI,
Uvicorn, SQLAlchemy, Alembic, PyMySQL, Pydantic settings, PyMuPDF,
Chroma, the selected embedding library, JWT/security packages, Pytest,
and HTTPX.

Document commands similar to:

``` bash
cd backend
python -m venv .venv
```

Windows:

``` bash
.venv\Scripts\activate
```

macOS/Linux:

``` bash
source .venv/bin/activate
```

Then:

``` bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The exact commands must match the generated repository structure and
configuration.

## 15. Testing Plan

Use Pytest and HTTPX.

Test: - Registration, login, invalid credentials, duplicate email - JWT
expiration and protected routes - Cross-user document/conversation
isolation - File type/size validation - PDF extraction and empty/scanned
PDF handling - Chunk page metadata - Vector indexing and retrieval -
Citation IDs/pages matching retrieved chunks - Insufficient-evidence
responses - LLM timeout, rate-limit, and missing-key handling - Message
persistence and chronological ordering - Document deletion and
vector/file cleanup - Retry after processing failure - Analytics scoped
to the authenticated user

Use temporary directories and test databases or isolated test schemas.
Mock external LLM calls in unit tests without pretending those mocks are
live AI functionality.

## 16. Development Phases

### Phase 1: Base backend

-   FastAPI application, settings, health endpoint, CORS, error handling
-   MySQL/XAMPP connection
-   SQLAlchemy base and Alembic migrations

### Phase 2: Authentication

-   User model, password hashing, JWT, auth routes, current-user
    dependency
-   Auth tests

### Phase 3: Documents

-   Upload, validation, storage, PDF extraction, processing status,
    list/detail/delete/retry
-   Document tests

### Phase 4: RAG

-   Chunking, embeddings, Chroma, retrieval filters, source metadata
-   Retrieval tests

### Phase 5: AI and conversations

-   LLM adapter, grounded prompting, citation validation,
    conversation/message APIs
-   Insufficient-evidence behavior and failure handling

### Phase 6: Dashboard and settings

-   Real statistics, activity, analytics, profile APIs

### Phase 7: Hardening and documentation

-   Authorization review, tests, README, environment examples,
    migrations, deployment configuration

At the end of each phase, run the tests and provide the changed files,
commands executed, and any unresolved limitations.

## 17. Acceptance Criteria

-   FastAPI starts and connects to MySQL through the configured XAMPP
    service.
-   Alembic migrations create the schema successfully.
-   User registration and login work.
-   Authenticated users can upload supported PDFs.
-   Text extraction and indexing complete with accurate page metadata.
-   RAG retrieves only authorized document chunks.
-   AI answers contain valid citations or state that evidence is
    insufficient.
-   Conversations and messages persist in MySQL.
-   Cross-user access is blocked.
-   Deletion cleans up database, vector, and file records safely.
-   Tests pass and API documentation is available.
-   README enables another developer to run the backend locally.
-   No credentials, fabricated citations, or false deployment claims are
    included.

## Final Instruction

First implement and document the database models, migrations, API
request/response schemas, and authentication. Then implement document
processing and RAG in separate services. Keep the API contract
consistent with the separate React frontend prompt. Build in phases and
test each phase. Do not generate one enormous file, do not use MySQL
`create_all()` as a replacement for migrations, and do not claim a
feature is complete until it is working and verified.
