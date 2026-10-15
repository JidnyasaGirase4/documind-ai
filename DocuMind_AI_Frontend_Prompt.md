# DocuMind AI --- Frontend Implementation Prompt

You are a senior frontend engineer and product UI/UX designer. Build the
complete frontend for **DocuMind AI**, a professional AI-powered
document intelligence and knowledge-search platform.

This prompt covers FRONTEND ONLY. Build the React application,
responsive design, components, navigation, form validation, and API
integration layer. Do not implement the Python backend or database. Do
not present fake UI interactions as completed functionality. Use the API
contract below and make backend base URL configurable.

## 1. Product Goal

Users upload PDF documents, ask questions about their content, and
receive AI answers with document/page citations. The experience should
feel like a polished, trustworthy enterprise SaaS product---not a
generic admin template.

## 2. Required Stack

-   React.js with JavaScript ES6+
-   Vite
-   React Router
-   Tailwind CSS (or a consistent custom CSS system if Tailwind setup is
    incompatible)
-   Axios
-   React Context for authentication/shared state where appropriate
-   Recharts for analytics charts
-   Lucide React icons
-   React Hook Form optional for form handling
-   Vitest + React Testing Library for tests

Do not use TypeScript unless explicitly requested. Do not add
unnecessary UI libraries. Use reusable components and clean separation
of concerns.

## 3. Visual Design System

Create a professional, modern, calm AI/SaaS interface.

### Colors

-   Main background: `#F7F8FC`
-   Surface/card: `#FFFFFF`
-   Primary text: `#172033`
-   Secondary text: `#667085`
-   Primary indigo: `#4F46E5`
-   Primary hover: `#4338CA`
-   Soft indigo surface: `#EEF2FF`
-   Border: `#E5E7EB`
-   Success: `#15803D`
-   Warning: `#B45309`
-   Error: `#B42318`
-   Dark sidebar: `#111827` with subtle lighter hover states

Use the accent color sparingly. Use consistent spacing, 8px rhythm,
restrained shadows, 10--14px corner radii, clear typography, and good
contrast. Avoid neon gradients, excessive glassmorphism, oversaturated
backgrounds, and decorative elements that reduce usability.

### Typography

Use Inter or a clean system sans-serif. Use clear page titles, compact
labels, readable body text, and consistent line heights. Make dense
tables readable.

### Layout

-   Desktop application shell: 248px sidebar + flexible main area.
-   Top header: page title/breadcrumb, optional search, notifications
    only if implemented, and user menu.
-   Main content max width: around 1440px with responsive padding.
-   Mobile: collapsible drawer/sidebar, stacked cards, scrollable tables
    or mobile card layout.
-   Make the app usable at 1440px, 1024px, 768px, and 375px widths.

### Interaction details

-   Visible keyboard focus states
-   Accessible labels and button names
-   Loading skeletons
-   Empty states with useful next action
-   Error states with retry where possible
-   Confirmation dialogs for destructive actions
-   Toasts for success/error feedback
-   Tooltips for icon-only buttons
-   Disable buttons while actions are submitting
-   Prevent duplicate form submissions
-   No inert controls or fake links

## 4. Brand and Shared Components

Create a simple DocuMind AI wordmark with a document + sparkle/search
icon. Do not use copyrighted brand logos. Use Lucide icons.

Reusable components: - `AppSidebar` - `AppHeader` - `MobileNavigation` -
`PageHeader` - `Button` - `Input` - `Textarea` - `Select` - `Badge` -
`Card` - `StatCard` - `Modal` - `ConfirmDialog` - `ToastProvider` -
`LoadingSkeleton` - `EmptyState` - `ErrorState` - `Pagination` -
`SearchInput` - `DocumentStatusBadge` - `DocumentRow` / `DocumentCard` -
`UploadDropzone` - `ChatMessage` - `SourceCitationCard` -
`ChatComposer` - `ChartCard`

Use consistent component APIs and avoid duplicated markup.

## 5. Routes and Pages

### Public routes

-   `/` --- Landing page
-   `/features` --- Features page
-   `/how-it-works` --- How It Works
-   `/about` --- About
-   `/login` --- Login
-   `/register` --- Registration

### Protected routes

-   `/app/dashboard`
-   `/app/documents`
-   `/app/documents/:documentId`
-   `/app/assistant`
-   `/app/assistant/:conversationId`
-   `/app/history`
-   `/app/analytics`
-   `/app/settings`

Use a route guard for user experience, but remember that actual
authorization must be enforced by the backend. Preserve intended
destination when redirecting unauthenticated users to login.

## 6. Public Website Design

### Landing page

Create a polished product landing page with: 1. Responsive navbar with
logo, Features, How It Works, About, Log In, Get Started. 2. Hero
section: - Eyebrow: `AI-POWERED DOCUMENT INTELLIGENCE` - Heading:
`Your documents. Your knowledge. One AI assistant.` - Supporting copy:
`Find answers in your PDFs, policies, manuals, and reports—with source references you can verify.` -
Primary CTA: `Start for Free` - Secondary CTA: `See How It Works` -
Right-side product preview composed of actual frontend mock UI
components, not a static screenshot. 3. Trust/value strip with 3--4
benefits; do not invent customer logos or metrics. 4. Features grid: PDF
knowledge search, cited answers, document library, conversation history,
secure document access, usage insights. 5. How it works: Upload → Ask →
Verify. 6. Use cases: teams, students, developers, researchers. 7. FAQ
accordion with accessible keyboard behavior. 8. Final CTA. 9. Footer
with navigation, privacy/terms placeholders clearly marked if no legal
pages exist.

Use coherent spacing and responsive stacking. No fabricated user
testimonials, company logos, or unsupported security certifications.

### Features page

Explain each product capability with a concise description and
appropriate visual examples.

### How It Works page

Show the document pipeline visually: Upload PDF → Extract text → Split
into chunks → Index embeddings → Retrieve passages → Generate cited
answer. Make it clear this is a product workflow, not a claim that
processing is instantaneous.

### About page

Describe the product purpose and intended use cases. Do not invent
company history or claims.

### Login page

-   Email and password fields
-   Password visibility toggle
-   Inline validation
-   Submit loading state
-   Error summary
-   Link to registration
-   Show API error messages safely

### Registration page

-   Name, email, password, confirm password
-   Password requirements
-   Inline validation
-   Submit state
-   Link to login
-   Do not store plaintext passwords in frontend state longer than
    necessary.

## 7. Protected App Shell

Sidebar items: - Dashboard - My Documents - AI Assistant - Chat
History - Analytics - Settings

Include active route styling, icons, a collapse option on desktop, and a
mobile drawer. Footer/sidebar user area should show the authenticated
user's name/email only when returned by `/auth/me`.

Header: - Page title/breadcrumb - Optional document/global search only
if functional - User dropdown with profile/settings and logout - Do not
add nonfunctional notification icons.

## 8. Dashboard Page

Connect to: - `GET /api/v1/dashboard/stats` -
`GET /api/v1/dashboard/activity` - `GET /api/v1/documents` -
`GET /api/v1/conversations`

Display stat cards: - Total documents - Ready documents - Processing
documents - Failed documents

Also display: - Recent uploads table/list - Recent conversations -
Document processing overview - Quick actions: Upload PDF, Ask a Question

Requirements: - All statistics must come from the API. - Do not hardcode
demo numbers as live data. - Provide skeleton loading, empty states,
retryable errors, and mobile layouts. - If the backend is unavailable,
show a clear connection error and optionally offer a clearly labeled
demo mode only if a separate demo mode is deliberately implemented.

## 9. My Documents Page

Features: - Drag-and-drop upload area and file picker - Accept PDFs only
in the first version - Show supported file type and configured size
limit from configuration - Upload progress if supported - Search by
filename - Filter by status - Sort by name/date - Pagination - Document
row/card: filename, size, upload date, status, action menu - Actions:
view details/preview, retry failed processing, delete - Delete
confirmation dialog - Empty state with upload CTA - Processing state
with status label - Failed state with useful error and retry action

Use multipart form data for upload. Do not assume an upload succeeded
until the API confirms it. Poll document status with a controlled
interval while a document is processing, and stop polling when the page
unmounts or status becomes ready/failed. Avoid excessive requests.

## 10. Document Details Page

Show: - Filename and processing status - File metadata and page count if
returned - Preview/open action through authorized backend endpoint -
Processing error when failed - Retry processing if available - Delete
action - Return-to-library link

Do not expose direct server file paths. Use an authorized preview
endpoint or a short-lived URL if the backend supports one.

## 11. AI Assistant Page

Build a high-quality two-panel layout: - Optional left
conversation/document selector panel - Main chat panel - Responsive
collapse into a mobile layout

Chat interface: - Welcome/empty state with suggested example questions -
Document selector for one or more accessible documents or "All my
documents" - Message bubbles for user and assistant - Composer with
multiline input and send button - Enter to send and Shift+Enter for
newline, with accessible alternatives - Sending/answer loading state -
Error state and retry - Copy answer action - Citation list/cards under
assistant messages - Each citation shows document name, page number, and
a short supporting excerpt if returned - Clicking a citation opens the
corresponding authorized document/page where possible - Conversation
title and timestamp - Follow-up questions - Keep focus behavior sensible
after sending a message

Only render citation details actually returned by the API. Never
fabricate source pages or excerpts.

## 12. Chat History Page

Display conversations with: - Title - Last updated time - Optional
message count if returned - Search by title - Open conversation -
Rename - Delete with confirmation - Pagination or incremental loading

Ensure the UI refreshes after rename/delete and handles empty history.

## 13. Analytics Page

Use Recharts for: - Document uploads over time - Processing status
distribution - Conversation/question activity

Metrics must be sourced from `GET /api/v1/analytics/overview`. Include
date-range controls only if the backend supports them. Add accessible
chart labels and a tabular alternative or concise text summary.

## 14. Settings Page

Implement only supported settings: - View/update profile fields -
Account information - Logout - Supported file type/size information -
Data retention/deletion explanation

If password change or account deletion is not supported by the API, do
not show a functional-looking control for it.

## 15. Frontend API Contract

Use an environment variable such as:
`VITE_API_BASE_URL=http://127.0.0.1:8000`

All API calls must be centralized in `src/services/`. Use Axios with a
shared instance, consistent error normalization, and auth handling.

Expected endpoints: - `POST /api/v1/auth/register` -
`POST /api/v1/auth/login` - `GET /api/v1/auth/me` -
`GET /api/v1/dashboard/stats` - `GET /api/v1/dashboard/activity` -
`POST /api/v1/documents/upload` - `GET /api/v1/documents` -
`GET /api/v1/documents/{id}` - `GET /api/v1/documents/{id}/preview` -
`DELETE /api/v1/documents/{id}` - `POST /api/v1/documents/{id}/retry` -
`POST /api/v1/conversations` - `GET /api/v1/conversations` -
`GET /api/v1/conversations/{id}` - `PATCH /api/v1/conversations/{id}` -
`DELETE /api/v1/conversations/{id}` -
`POST /api/v1/conversations/{id}/messages` -
`GET /api/v1/analytics/overview` - `GET /api/v1/settings/profile` -
`PATCH /api/v1/settings/profile`

Document and follow the actual backend response schemas. If a response
contract is not finalized, define it explicitly in a shared API contract
document instead of guessing in multiple components.

Authentication: - Implement a shared auth provider. - Load current user
using `/auth/me`. - Handle token expiration and logout consistently. -
Never treat frontend route guards as backend security. - Prefer a secure
token strategy supported by the backend. If bearer tokens are stored in
browser storage, document the XSS tradeoff and protect the app
appropriately.

## 16. Suggested Frontend Structure

``` text
frontend/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── common/
│   │   ├── layout/
│   │   ├── documents/
│   │   └── chat/
│   ├── layouts/
│   ├── pages/
│   │   ├── public/
│   │   └── app/
│   ├── routes/
│   ├── services/
│   ├── context/
│   ├── hooks/
│   ├── utils/
│   ├── styles/
│   ├── App.jsx
│   └── main.jsx
├── .env.example
├── package.json
└── README.md
```

## 17. Quality Requirements

-   Keep components small and reusable.
-   Avoid giant components and duplicated API logic.
-   Use stable loading/error states.
-   Add frontend tests for authentication forms, protected routes,
    document upload states, chat submission, citation rendering, and
    error states.
-   Add ESLint or equivalent basic code-quality checks.
-   Do not use lorem ipsum in final pages.
-   Do not leave dead links, fake metrics, or inert buttons.
-   Make layout responsive and accessible.
-   Keep API base URL configurable.
-   Document frontend setup and environment configuration.

## 18. Required Delivery Process

Before coding: 1. Summarize the frontend architecture and route map. 2.
Confirm the shared API contract with the backend plan. 3. Create the
folder structure and design tokens.

Then implement: 1. Design system and public pages. 2. App shell and
navigation. 3. Authentication. 4. Document management. 5. AI assistant
and citations. 6. History, analytics, and settings. 7. Tests, responsive
review, and README.

At each phase, ensure the app runs. Do not implement all pages as
disconnected mockups.

## 19. Definition of Done

-   Every specified page exists and is responsive.
-   Navigation and forms work.
-   API integration uses the configured backend URL.
-   Dashboard and analytics show real API data.
-   Upload states reflect actual backend responses.
-   Chat messages and citations use API responses.
-   Errors, empty states, and loading states are handled.
-   No fake success messages or invented citations.
-   Frontend tests pass.
-   README explains install, configuration, and run commands.

Build a professional, portfolio-quality React frontend that can be
integrated with the separately implemented FastAPI backend using the
shared contract above.
