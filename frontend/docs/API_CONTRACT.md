# DocuMind AI — Frontend/Backend API Contract

Base URL: `${VITE_API_BASE_URL}/api/v1`. All endpoints except register/login require
`Authorization: Bearer <access_token>`. All calls live in `src/services/`; field mapping lives in
`src/services/normalize.js`. If the backend differs from this document, change the contract here and the
mapper there, not individual components.

## Errors

```json
{ "error": { "code": "DOCUMENT_NOT_READY", "message": "…", "details": null } }
```

FastAPI's default `{ "detail": "…" }` / `{ "detail": [{ "msg": "…" }] }` is also understood. `message` is shown to the
user as plain text. A response with no HTTP reply is shown as a connection error.

## Auth

| Endpoint | Request | Response |
|---|---|---|
| `POST /auth/register` | `{ name, email, password }` | `201` user. The client then logs in. |
| `POST /auth/login` | `{ email, password }` | `{ access_token, token_type }` |
| `GET /auth/me` | – | `{ id, name, email, created_at? }` (`full_name` is also accepted) |

A `401` on any other call clears the session and redirects to login.

## Documents

Document: `{ id, original_filename, file_size, processing_status, processing_error, total_pages, created_at, updated_at }`
where `processing_status ∈ uploaded | processing | ready | failed`.

| Endpoint | Notes |
|---|---|
| `GET /documents` | Query: `page`, `page_size`, `search`, `status`, `sort_by` (`name` \| `created_at`), `sort_order` (`asc` \| `desc`). Response: `{ items, total, page, page_size, pages? }` (a bare array also works). |
| `POST /documents/upload` | `multipart/form-data`, field `file`. Returns the created document (`201`/`202`). |
| `GET /documents/{id}` | Document |
| `GET /documents/{id}/preview` | Authorized PDF stream (`application/pdf`) **or** JSON `{ url }` with a short-lived link. |
| `DELETE /documents/{id}` | `204` |
| `POST /documents/{id}/retry` | `202`, optionally the updated document |

## Conversations

Conversation: `{ id, title, created_at, updated_at, message_count? }`; the detail response adds `messages`.

Message: `{ id, role: "user" | "assistant", content, created_at, citations?: Citation[], follow_up_questions?: string[] }`
(`citation_metadata` is accepted as an alias for `citations`).

Citation: `{ document_id, document_name, page_number, excerpt? }` — only fields actually returned are rendered.

| Endpoint | Notes |
|---|---|
| `GET /conversations` | Query: `page`, `page_size`, `search`. Paginated like documents. |
| `POST /conversations` | `{ title?, document_ids? }` → Conversation |
| `GET /conversations/{id}` | Conversation + `messages` (chronological) |
| `PATCH /conversations/{id}` | `{ title }` → Conversation |
| `DELETE /conversations/{id}` | `204` |
| `POST /conversations/{id}/messages` | `{ content, document_ids? }` → `{ user_message, assistant_message }` (a bare assistant message is accepted). Empty `document_ids` means "all my documents". |

`follow_up_questions` is optional; the UI only shows follow-up suggestions when the API returns them.

## Dashboard, analytics, settings

| Endpoint | Response |
|---|---|
| `GET /dashboard/stats` | `{ total_documents, ready_documents, processing_documents, failed_documents }` |
| `GET /dashboard/activity` | `[{ id?, type, title, timestamp }]` or `{ items: [...] }` |
| `GET /analytics/overview` | `{ uploads_over_time: [{ date, count }], status_distribution: [{ status, count }], question_activity: [{ date, count }] }` |
| `GET /settings/profile` | `{ id, name, email, created_at? }` |
| `PATCH /settings/profile` | `{ name }` → profile |

No date-range parameters are sent to analytics because the backend plan does not define them.

> Status: this contract is implemented by the FastAPI backend in `../../backend` and was verified end to end in a browser (register, upload, indexing, cited answers, history, analytics, settings).
