# DocuMind AI — Frontend

React + Vite + Tailwind CSS single-page app for the DocuMind AI document Q&A platform. It talks to the separate
FastAPI backend; see [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the original contract (documents, chat, analytics) and the backend's `/docs` (OpenAPI) for the
current, complete API including collections, sharing, search, versions, reviews and conflicts. The project overview is in the root [README](../README.md).

## Setup

```bash
npm install
cp .env.example .env     # then edit values
npm run dev              # http://localhost:5173
```

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend origin (the app appends `/api/v1`). Must match the port the API runs on (`backend/run.bat` uses 8001). |
| `VITE_MAX_UPLOAD_MB` | `25` | Size limit *displayed* and pre-checked on upload. The backend enforces the real limit. |

The backend must allow the frontend origin in its CORS settings (e.g. `http://localhost:5173`).

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` / `npm run preview` | Production build / preview |
| `npm run lint` | ESLint |
| `npm test` | Vitest + React Testing Library |

## Structure

```
src/
  components/{common,layout,documents,chat,knowledge,versions,reviews,viewer,analytics,marketing}   reusable UI
  layouts/        PublicLayout, AppLayout (sidebar + header)
  pages/{public,app}
  routes/         AppRoutes, ProtectedRoute
  services/       all API calls (Axios instance, error normalisation, payload mappers)
  context/        AuthContext, ToastContext
  hooks/          useAsync, usePolling, useDebounce, useDocumentTitle
  utils/          config, formatting, validation, preview helper
  test/           tests
```

## Behaviour notes

- **Data is never faked.** Dashboard, analytics, documents, chat and citations render what the API returns. If the
  backend is unreachable the page shows a connection error with a retry button. There is no demo mode.
- **Polling.** The document list and details page re-fetch every 5 s only while a document is `uploaded`/`processing`,
  pause while the tab is hidden, and stop on unmount.
- **Citations** show document name, page and excerpt only when returned. Clicking one fetches the PDF through the
  authorized preview endpoint and opens it at that page (`#page=N`).
- **Public pages** use illustrative sample content that is labelled as an example. Privacy/Terms are marked as
  placeholders in the footer because no legal pages exist.
- Not implemented because the API contract has no endpoint for them: password change, account deletion, notifications,
  analytics date ranges. (Search across documents, collections/sharing, version history, reviews and conflict findings were added later and use the
  endpoints listed in the backend's OpenAPI document.)

## Security notes

- The route guard is for UX only; the backend must authorize every request.
- The JWT is kept in `localStorage` so sessions survive reloads. That makes it readable by any script on the page
  (XSS). The app renders all server text as plain text (no `dangerouslySetInnerHTML`) and has no third-party scripts.
  For stronger protection, have the backend issue an `HttpOnly; Secure; SameSite` cookie and replace
  `tokenStore` / the request interceptor in `src/services/http.js`.
- Passwords are held in component state only while the form is open and are cleared after submit.
- Serve the production build behind HTTPS with a restrictive `Content-Security-Policy`.

## Trying the app without the backend

`npm run mock` starts a **development-only** fake API on http://127.0.0.1:8000. It accepts any email and password
and serves sample documents, conversations and analytics; chat answers are canned and labelled `[Mock]`. Run it in a
second terminal next to `npm run dev`. Never deploy it. The real backend replaces it with no frontend changes.
