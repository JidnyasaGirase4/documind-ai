# DocuMind AI --- Complete Project Plan

**Project type:** Full-stack AI document intelligence and
knowledge-search platform\
**Stack:** React.js, JavaScript, Python, FastAPI, MySQL, Chroma,
embeddings, LLM API, RAG.

## 1. Project Overview

DocuMind AI lets authenticated users upload PDF documents, search their
content, ask questions in natural language, and receive AI-generated
answers grounded in uploaded documents with source-document and page
references.

**Problem solved:** Users spend time manually searching lengthy
handbooks, manuals, policies, notes, and reports. DocuMind AI combines
PDF processing, semantic retrieval, and grounded question answering.

**Target users:** Employees, students, developers, researchers, and
consultants.

**Core rule:** Answer from accessible uploaded documents, provide
traceable citations, and admit when evidence is insufficient. Do not
present mock responses as real AI answers.

## 2. Goals and Scope

### Goals

-   Build a polished, responsive React frontend.
-   Implement a Python/FastAPI REST backend.
-   Store application records in MySQL.
-   Extract text from supported PDFs while preserving page metadata.
-   Implement RAG: extraction → chunking → embeddings → retrieval →
    grounded answer.
-   Keep each user's documents and conversations private.
-   Include tests, environment examples, setup instructions, and
    deployment guidance.

### Initial limitations

-   OCR for scanned PDFs is out of scope for the first version; detect
    and explain unsupported extraction.
-   No billing, payment processing, enterprise SSO, or organization-wide
    multi-tenancy.
-   Do not claim deployment is complete until it has been verified.

## 3. Technology Stack

### Frontend

-   React.js, JavaScript ES6+, Vite
-   HTML5, CSS3, Tailwind CSS or a consistent CSS system
-   React Router, Axios, React Context where appropriate
-   Recharts, Lucide React
-   Vitest and React Testing Library

### Backend

-   Python, FastAPI, Pydantic
-   SQLAlchemy and Alembic
-   PyMuPDF for PDF extraction
-   JWT authentication and a maintained password-hashing library
-   Pytest

### Data and AI

-   MySQL for relational application data
-   Chroma for the initial vector index
-   Sentence Transformers or a compatible embedding API
-   An LLM API for answer generation
-   Retrieval-Augmented Generation (RAG)

### Tools

VS Code, Git, GitHub, Postman, MySQL Workbench or phpMyAdmin, Python
virtual environment, npm.

**Architecture note:** MySQL is the primary relational database; Chroma
stores and searches embeddings. Every vector should include owner,
document, chunk, and page metadata. Authorization filters must be
applied before retrieved text is sent to an LLM.

## 4. Main User Journey

1.  Visitor explores the landing page.
2.  User registers or logs in.
3.  User opens the dashboard and uploads a PDF.
4.  Backend validates and stores the file, extracts page-aware text,
    chunks it, generates embeddings, and indexes it.
5.  UI shows `uploaded`, `processing`, `ready`, or `failed`.
6.  User asks a question about one or more accessible documents.
7.  Backend retrieves relevant passages and asks the LLM to answer from
    the evidence.
8.  UI displays the answer with document and page citations.
9.  User asks follow-up questions or reopens chat history.
10. User can delete documents and conversations; related data is cleaned
    up according to the documented deletion policy.

## 5. Functional Modules

### Public website

-   Landing, Features, How It Works, About
-   Login and Registration
-   Footer with privacy and terms links/placeholders

### Authentication

-   Register, login, logout, current-user endpoint
-   Password hashing and JWT-protected endpoints
-   Input validation and clear error messages
-   Frontend route guards for usability; backend authorization for
    security

### Dashboard

-   Total, ready, processing, and failed documents
-   Recent uploads and conversations
-   Activity and storage summary
-   Upload and new-chat quick actions
-   Real API data, loading states, empty states, and errors

### Document management

-   Drag/drop and file-picker PDF upload
-   Frontend and backend file validation
-   Upload progress where supported
-   Filename, size, upload date, processing status
-   Search, filter, sort, pagination
-   Document details and authorized preview
-   Delete with confirmation and retry failed processing

Initial format: text-based PDFs. If extraction yields no text, explain
that scanned PDFs need OCR and are not supported in the first version.

### PDF processing and indexing

1.  Validate the file and generate a safe server-side filename.
2.  Store it in configured storage and create MySQL metadata.
3.  Extract text with page numbers using PyMuPDF.
4.  Split text into configurable overlapping chunks.
5.  Generate embeddings and index chunks in Chroma.
6.  Save chunk metadata and vector references where appropriate.
7.  Update processing status and log errors.
8.  Support safe retry and clean temporary files.
9.  Remove vector records and stored files when a document is deleted.

Use background processing so large files do not block requests. FastAPI
background tasks may be used for the initial local version, with the
processing service structured so a proper queue can be added later.

### AI assistant

-   New conversation, send question, follow-up questions
-   Select a document or search all accessible documents
-   Loading, timeout, provider-error, and retry states
-   Answers with document and page citations
-   Copy answer, rename/delete conversation, persist history

RAG flow: 1. Verify user and conversation ownership. 2. Validate
selected document IDs and permissions. 3. Embed the question. 4.
Retrieve relevant chunks and filter by authorized owner/document. 5.
Construct an LLM prompt with retrieved passages and source metadata. 6.
Generate an evidence-grounded answer. 7. Return answer and citations;
save messages and citation metadata.

The model must not invent source references or document facts. If
evidence is insufficient, say so. Treat uploaded document text as
untrusted data that cannot override system instructions.

### Conversation history

-   List, search, reopen, rename, and delete conversations
-   Persist messages across refreshes
-   Enforce ownership on every conversation and message API

### Analytics

-   Documents uploaded over time
-   Ready/failed/processing counts
-   Number of conversations and questions
-   Recent processing errors
-   User-scoped metrics based on real database records

### Settings

-   Profile details supported by the API
-   Account information, logout, supported file limits, data deletion
    explanation
-   Do not show controls that do not work

## 6. UI/UX Requirements

Use a clean enterprise SaaS style: white/light-gray surfaces, dark navy
text, blue/indigo accents, consistent spacing, restrained shadows,
moderate corner radii, responsive desktop/tablet/mobile layouts,
accessible labels, keyboard navigation, and clear focus states.

Application shell: - Collapsible sidebar - Top bar with page
title/breadcrumb and user menu - Responsive main content area

Pages: 1. Landing: hero, CTA, product preview, features, workflow, use
cases, FAQ, footer 2. Features 3. How It Works 4. About 5.
Login/Register 6. Dashboard 7. My Documents 8. AI Assistant 9. Chat
History 10. Analytics 11. Settings

Reusable components: - Buttons, inputs, modal, toast, sidebar, header -
Stat cards, document table/cards, upload dropzone, status badges -
Search/filter toolbar, chat bubbles, citation cards - Skeletons,
empty/error states, pagination, confirmation dialogs

Every visible control must work or be clearly marked unavailable.

## 7. Database Plan

Use SQLAlchemy models and Alembic migrations, with foreign keys,
indexes, timestamps, and deliberate deletion behavior.

### `users`

`id`, `name`, `email` (unique), `password_hash`, `is_active`,
`created_at`, `updated_at`

### `documents`

`id`, `user_id`, `original_filename`, `storage_path`, `file_size`,
`mime_type`, `processing_status`, `processing_error`, `total_pages`,
`created_at`, `updated_at`

### `document_chunks`

`id`, `document_id`, `chunk_index`, `page_number`, `extracted_text`,
`vector_reference`, `created_at`

### `conversations`

`id`, `user_id`, `title`, `created_at`, `updated_at`

### `messages`

`id`, `conversation_id`, `role`, `content`, `citation_metadata`,
`created_at`

### `processing_jobs`

`id`, `document_id`, `status`, `retry_count`, `error_message`,
`started_at`, `completed_at`, `created_at`

Optional future `document_permissions` table only if sharing is
implemented.

Rules: - Documents belong to one owner in the first version. -
Conversations belong to one user; messages belong to one conversation. -
Enforce ownership in backend queries, not only in React. - Clean up
vectors and stored files on document deletion. - Define how old
citations behave after their source document is deleted.

## 8. REST API Plan

Use `/api/v1`, consistent JSON schemas, validation, pagination, status
codes, and clear errors.

### Auth

-   `POST /api/v1/auth/register`
-   `POST /api/v1/auth/login`
-   `GET /api/v1/auth/me`

### Dashboard

-   `GET /api/v1/dashboard/stats`
-   `GET /api/v1/dashboard/activity`

### Documents

-   `POST /api/v1/documents/upload`
-   `GET /api/v1/documents`
-   `GET /api/v1/documents/{document_id}`
-   `GET /api/v1/documents/{document_id}/preview`
-   `DELETE /api/v1/documents/{document_id}`
-   `POST /api/v1/documents/{document_id}/retry`

### Conversations

-   `POST /api/v1/conversations`
-   `GET /api/v1/conversations`
-   `GET /api/v1/conversations/{conversation_id}`
-   `PATCH /api/v1/conversations/{conversation_id}`
-   `DELETE /api/v1/conversations/{conversation_id}`

### Messages

-   `POST /api/v1/conversations/{conversation_id}/messages`

### Analytics and settings

-   `GET /api/v1/analytics/overview`
-   `GET /api/v1/settings/profile`
-   `PATCH /api/v1/settings/profile`

Define request/response schemas before frontend integration. FastAPI
OpenAPI/Swagger documentation should be usable. Never expose stack
traces or secrets in public errors.

## 9. Repository Structure

``` text
documind-ai/
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── context/
│   │   ├── hooks/
│   │   └── utils/
│   ├── .env.example
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── db/
│   │   ├── rag/
│   │   ├── utils/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── docs/
│   ├── architecture.md
│   ├── api-contract.md
│   └── database-design.md
├── .gitignore
└── README.md
```

## 10. Security and Reliability

-   Hash passwords; keep JWT and AI API keys in environment variables.
-   Validate file type/size on both frontend and backend.
-   Generate safe storage filenames; never trust client filenames as
    paths.
-   Store uploads outside publicly served frontend directories.
-   Enforce ownership on documents, chunks, conversations, and messages.
-   Filter vector results before sending context to the LLM.
-   Treat document text as untrusted input.
-   Avoid logging passwords, tokens, API keys, or sensitive full
    document content.
-   Add timeouts and useful errors for embedding/LLM failures.
-   Handle partial indexing failures and retries safely.
-   Add rate limits or usage controls before public deployment.
-   Document file retention and deletion behavior.

## 11. Testing Plan

### Backend

-   Registration, login, duplicate email, invalid inputs
-   Unauthorized access and cross-user isolation
-   File validation and PDF extraction
-   Empty/scanned PDF handling
-   Chunking and page metadata
-   Retrieval relevance and citation metadata
-   LLM timeout/provider failure
-   Conversation and message persistence
-   Document deletion, vector cleanup, retry behavior

### Frontend

-   Form validation and protected routes
-   Upload progress and processing states
-   Document list/search/filter
-   Chat submission, loading, citations, and errors
-   Empty states and responsive navigation

### Manual acceptance test

Upload a known PDF, ask a question answered in it, verify the cited
page, ask an unsupported question, and confirm the system admits
insufficient evidence. Sign in as a second user and verify the first
user's content is inaccessible.

## 12. Development Phases

### Phase 1 --- Setup

Create repository, Vite/React app, FastAPI app, environment examples,
health endpoint, routing, design system. **Exit:** Both apps start and
frontend can call the backend.

### Phase 2 --- Database and authentication

Configure MySQL, SQLAlchemy models, Alembic, register/login/current-user
APIs, auth UI. **Exit:** Auth works and protected endpoints enforce
identity.

### Phase 3 --- Document management

Build upload UI, secure file upload, extraction, document list,
processing states, delete and retry. **Exit:** Uploaded text PDFs are
processed and visible.

### Phase 4 --- RAG indexing

Add chunking, embeddings, Chroma indexing, metadata filters, retrieval
tests. **Exit:** Queries retrieve relevant passages from only authorized
documents.

### Phase 5 --- AI assistant

Add LLM adapter, grounded prompting, citations, conversation APIs and
chat UI. **Exit:** Answers cite retrieved sources and unsupported
questions are handled honestly.

### Phase 6 --- Dashboard and analytics

Connect real dashboard statistics, history, analytics, and settings.
**Exit:** No fake metrics or inert controls remain in implemented areas.

### Phase 7 --- Quality and deployment

Automated tests, access-control review, responsive polish, README,
deployment configuration and verification. **Exit:** Tests and
documented manual scenarios pass; another developer can run the app
using the README.

## 13. Definition of Done

-   User registration and login work.
-   Authenticated users can upload supported PDFs.
-   Extraction and indexing work.
-   Questions return evidence-grounded answers with valid citations.
-   Insufficient evidence is acknowledged.
-   Conversation history persists.
-   Users cannot access other users' documents, vectors, or chats.
-   Frontend and backend are integrated and tested.
-   Database migrations work.
-   Environment examples contain no real secrets.
-   Setup instructions are complete.
-   Deployment status is stated accurately.

## 14. Implementation Rules

1.  Do not create only a static dashboard and call it a full-stack
    application.
2.  Do not use fake statistics or unlabelled mock AI answers.
3.  Do not mark features complete before API/database integration works.
4.  Never put private API keys in frontend code.
5.  Do not trust client-supplied ownership or document IDs without
    backend validation.
6.  Keep frontend and backend prompts separate, but make both follow
    this shared plan and API contract.
7.  Build and verify each phase before proceeding.
8.  Keep code understandable enough to explain in a Full Stack Developer
    interview.

## 15. Deliverables

-   React.js frontend source
-   Python/FastAPI backend source
-   MySQL schema and Alembic migrations
-   RAG indexing and retrieval pipeline
-   `.env.example` files
-   Automated tests
-   API, architecture, and database documentation
-   Complete setup README
-   GitHub repository
-   Deployment configuration and verified live demo, if deployed

**Success measure:** Another developer can clone the repository, follow
setup instructions, configure required services, run the application,
upload a PDF, ask a question, and verify the answer against its cited
source.
