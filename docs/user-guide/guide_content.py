"""Source text of the DocuMind AI user guide. Edit this file, then run build_user_guide.py to regenerate the PDF.

Block types: ("p", text) ("h2", text) ("steps", [text]) ("bullets", [text]) ("note"|"tip"|"warn", text)
             ("table", [header], [[cell]], [width %]) ("img", file, caption, width px)
Only describe what the application really does. Every screenshot in screenshots/ was captured from the running application."""

VERSION = "1.0"
DATE = "16 October 2026"
TITLE = "DocuMind AI User Guide"

INTRO_HOW_TO_USE = [
    ("p", "This guide explains how to use DocuMind AI from the point of view of the person using it. It does not describe the code. "
          "Read the chapters in order the first time; afterwards use the contents page to jump to the task you need."),
    ("bullets", [
        "Boxes marked <b>Note</b> explain something worth knowing. Boxes marked <b>Important</b> warn you about something that can cost time or data.",
        "Names in <b>bold</b> are buttons, tabs or menu items exactly as they appear on screen.",
        "The screenshots were taken from the real application with sample documents and sample people (Olivia Owner, Eddie Editor, Vera Viewer). Your screen will show your own data.",
    ]),
]

CHAPTERS = [
    {
        "id": "intro", "title": "Introduction to DocuMind AI",
        "blocks": [
            ("p", "DocuMind AI helps you keep and use knowledge that lives in PDF documents. You upload your PDFs, and the application reads them, "
                  "lets you organize and search them, answers your questions with references to the exact page, and helps your team keep the content "
                  "correct over time."),
            ("h2", "What you can do"),
            ("table", ["Task", "Where"], [
                ["Upload PDFs and watch them being processed", "My Documents"],
                ["Group documents into collections, categories and tags", "Knowledge Base, document pages"],
                ["Find passages by words, phrases or meaning", "Search (and the search box at the top of every page)"],
                ["Ask questions and get answers with citations", "AI Assistant"],
                ["Share a collection with colleagues", "Knowledge Base - collection page"],
                ["Keep every version of a document, compare and restore", "Document page - Version history"],
                ["Schedule reviews and track what is overdue", "Document page - Content review, and the Reviews page"],
                ["Check documents for possible contradictions", "Document page - Potential conflicts, and Reviews - Potential conflicts"],
            ], [62, 38]),
            ("h2", "A few words used in this guide"),
            ("table", ["Word", "Meaning"], [
                ["Document", "One PDF that you uploaded. It keeps the same name and place while you upload newer versions of it."],
                ["Version", "One uploaded file of a document. The <b>current version</b> is the one used for search and AI answers."],
                ["Collection", "A folder-like group of documents that can be shared with other people."],
                ["Citation", "A reference in an AI answer to a document, a page and the passage that supports the answer."],
                ["Owner, Editor, Viewer", "The three roles a person can have in a shared collection (chapter 12)."],
            ], [28, 72]),
            ("note", "DocuMind AI works with <b>text-based PDFs</b>. Scanned pages that are only pictures cannot be read, because the application has no text recognition (OCR)."),
            ("img", "dashboard.png", "The Dashboard shows your documents and recent activity. The menu on the left leads to every area of the application.", 640),
        ],
    },
    {
        "id": "signin", "title": "Sign-in and navigation",
        "blocks": [
            ("h2", "Create an account"),
            ("steps", [
                "Open the address of your DocuMind AI installation in a web browser and choose the button to create an account on the home page (or open the Register page).",
                "Enter your name, your email address, a password and the same password again. The password needs at least 8 characters, one letter and one number.",
                "Choose <b>Create account</b>. You are signed in and taken to the Dashboard.",
            ]),
            ("h2", "Sign in and sign out"),
            ("steps", [
                "On the sign-in page enter your email and password and choose <b>Log in</b>.",
                "To leave, open the account menu at the top right (your name) and choose <b>Log out</b>.",
            ]),
            ("p", "A sign-in stays valid for 30 minutes unless your administrator has set another time. If it expires you are taken back to the sign-in page and can continue after signing in again. "
                  "If you type a wrong password the application shows an error and you can try again; the message never says whether the email exists."),
            ("h2", "Finding your way around"),
            ("table", ["Menu item", "What it is for"], [
                ["Dashboard", "Numbers and recent activity for your own documents and questions"],
                ["My Documents", "Upload PDFs, see their status, open or delete them"],
                ["Search", "Find passages in every document you may read"],
                ["Knowledge Base", "Collections, categories and tags; sharing"],
                ["Reviews", "Content reviews that are due or overdue, and potential conflicts"],
                ["AI Assistant", "Ask questions about your documents"],
                ["Chat History", "Earlier conversations"],
                ["Analytics", "Statistics and answer-quality feedback"],
                ["Settings", "Your profile (name)"],
            ], [30, 70]),
            ("tip", "The search box at the top of every page starts a search across all documents. Press <b>Enter</b> to see the results on the Search page."),
            ("p", "On a phone or a narrow window the menu is hidden behind the menu button at the top left. All pages adapt to small screens."),
            ("img", "phone.png", "On a phone the same page is shown in one column. The buttons wrap and nothing needs sideways scrolling.", 220),
        ],
    },
    {
        "id": "upload", "title": "Uploading and processing PDF documents",
        "blocks": [
            ("h2", "Upload a document"),
            ("steps", [
                "Open <b>My Documents</b>.",
                "Drag one or more PDF files onto the upload area, or choose <b>Choose files</b> and select them.",
                "A progress bar shows the upload. The new document appears in the list with the status <b>Queued</b>.",
            ]),
            ("p", "Only PDF files are accepted. The default size limit is 20 MB per file and 1000 pages; your administrator can change it. "
                  "The application checks that the file really is a PDF (not just that its name ends in .pdf) and refuses password-protected files."),
            ("h2", "What happens next: status of a document"),
            ("table", ["Status", "Meaning", "What you do"], [
                ["Queued", "Waiting for its turn in the background queue", "Nothing; the page updates by itself"],
                ["Processing", "Text is being read, split into passages and indexed. A stage and percentage are shown", "Wait; large files take longer"],
                ["Completed", "Ready for search and questions", "Use it"],
                ["Failed", "Processing stopped. The reason is shown, for example that no text was found", "Read the message; use <b>Retry</b> if the cause was temporary"],
            ], [18, 52, 30]),
            ("p", "If a temporary problem occurs (for example the embedding model is busy) the application retries automatically up to three times with increasing pauses "
                  "and says so. Problems that retrying cannot fix, such as a corrupt file or a PDF without text, fail immediately with an explanation."),
            ("h2", "Actions on a document"),
            ("p", "Open the <b>...</b> menu at the right of a row, or click the document name to open its page. You can view details, organize it (chapter 4), "
                  "retry processing if it failed, or delete it. Deleting removes the document, all its versions, its files and its search index. Only the person who "
                  "uploaded a document can delete it."),
            ("img", "documents.png", "My Documents with search, status, sort and filter controls. Each row shows the status, category and tags.", 640),
            ("warn", "Deleting a document cannot be undone. A confirmation dialog appears first."),
        ],
    },
    {
        "id": "organize", "title": "Organizing documents with collections, categories and tags",
        "blocks": [
            ("p", "Three tools help you structure your library. They can be combined."),
            ("table", ["Tool", "Use it for", "Rules"], [
                ["Collection", "A group of documents, for example a project or a department. Can be shared (chapter 11)", "A document can be in many collections. Each collection has a name, optional description, colour and icon"],
                ["Category", "One label that says what kind of document it is, for example HR Policies", "At most one per document"],
                ["Tag", "Free keywords, for example 2026 or contract", "Any number per document"],
            ], [16, 44, 40]),
            ("h2", "Create a collection"),
            ("steps", [
                "Open <b>Knowledge Base</b> and stay on the <b>Collections</b> tab.",
                "Choose <b>New collection</b>, type a name, optionally a description, and pick a colour and an icon.",
                "Choose <b>Create collection</b>. The new collection appears as a card marked <b>Private</b> (only you can see it).",
            ]),
            ("p", "Names must be unique among your own collections, categories and tags, ignoring upper and lower case. The application tells you if a name is taken."),
            ("h2", "Put documents into a collection, assign a category and tags"),
            ("steps", [
                "On <b>My Documents</b> open the <b>...</b> menu of a document and choose <b>Organize</b> (or open the document and choose <b>Organize</b> there).",
                "Pick a category. Type a tag and press <b>Enter</b> to add it; the small x removes it. Tick the collections the document belongs to.",
                "Choose <b>Save</b>. Nothing is re-uploaded or re-processed.",
            ]),
            ("p", "Inside a collection you can also use <b>Add documents</b>, move a document to another collection, or remove it from the collection. "
                  "Removing a document from a collection never deletes the document."),
            ("h2", "Find documents again"),
            ("p", "On <b>My Documents</b> use the filters for collection, category (including Uncategorised) and tag, together with the status filter and the sort order. "
                  "<b>Clear filters</b> returns to the full list."),
            ("img", "organize.png", "The Organize dialog: category, tags and collections for one document.", 560),
            ("img", "collections.png", "The Knowledge Base lists collections as cards. Edit and delete are available to the owner.", 560),
            ("important", "Deleting a collection, a category or a tag never deletes documents. Documents simply lose that grouping or label. The confirmation dialog says so."),
        ],
    },
    {
        "id": "search", "title": "Searching with keyword, semantic and hybrid modes",
        "blocks": [
            ("p", "Search finds passages in all documents you are allowed to read, without starting a conversation. Open <b>Search</b> in the menu or use the search box "
                  "at the top of any page."),
            ("h2", "Choose a mode"),
            ("table", ["Mode", "How it works", "Good for"], [
                ["Hybrid (default)", "Combines keyword and meaning-based results into one ranking", "Most searches"],
                ["Keyword", "Finds the words you type. Words must start the same way (\"retent\" finds \"retention\"). Put an exact phrase in quotes. If no document contains all your words, you are told that results contain at least one of them", "Names, numbers, exact wording"],
                ["Semantic", "Finds passages whose meaning is close to your question even if the words differ", "Questions such as \"how long do we keep staff files\""],
            ], [20, 52, 28]),
            ("h2", "Search step by step"),
            ("steps", [
                "Type your words in the search box. Use quotes for an exact phrase, for example \"retention policy\".",
                "Choose a mode and press <b>Enter</b> or choose <b>Search</b>.",
                "Optionally narrow the results with the collection, category and tag filters and change the sort order (Most relevant, Newest first, Title A-Z). <b>Clear filters</b> removes them.",
                "Read the result cards. Matching words are highlighted. Choose <b>Open page N</b> to open that page with the passage highlighted.",
            ]),
            ("p", "Each result is one document and shows up to three matching passages with page numbers, the category, tags and collections. "
                  "A document can also be found by its file name, category or tag. When a passage was found by meaning, the card shows a \"semantic similarity\" number. "
                  "It is only a measure of how close two texts are for the computer; it is <b>not</b> a percentage of correctness."),
            ("h2", "When nothing is found, or something is unavailable"),
            ("bullets", [
                "<b>No results</b>: try fewer or different words, remove filters, or switch to Semantic.",
                "<b>Semantic search is unavailable right now</b>: the meaning-based part could not run. Keyword search still works, and Hybrid then shows keyword results with a notice.",
                "Search only covers documents that are <b>Completed</b>.",
            ]),
            ("note", "Search only returns documents you may read and only their <b>current version</b>. Text that exists only in an older version is not found."),
            ("img", "search.png", "Hybrid search for \"personnel records retained\": highlighted words, category, tags, collection and the page link.", 600),
        ],
    },
    {
        "id": "ask", "title": "Asking questions with the AI Assistant and understanding citations",
        "blocks": [
            ("h2", "Ask a question"),
            ("steps", [
                "Open <b>AI Assistant</b>. The selector at the top right says <b>All my documents</b>; click it to choose specific documents instead.",
                "Type your question in the box at the bottom and press <b>Enter</b> (<b>Shift+Enter</b> adds a new line).",
                "Wait for the answer. With a locally installed model this can take up to a minute.",
            ]),
            ("p", "The answer is written only from passages found in your documents. Under it you see <b>Sources</b>: one card per citation with the document name, the version, "
                  "the page and a short quote. The small numbers inside the answer match the numbered cards."),
            ("h2", "Understanding the answer"),
            ("bullets", [
                "<b>Every statement should have a citation.</b> If the assistant cannot support an answer with your documents it says that it could not find enough evidence instead of guessing.",
                "<b>Shared documents count.</b> Questions use your own documents and documents in collections shared with you. Nothing else is ever sent to the AI model.",
                "<b>Older versions are not used.</b> Answers come from the current version of each document.",
                "The assistant can be wrong. Open the citation and read the passage before you rely on an answer.",
            ]),
            ("h2", "Other things you can do"),
            ("bullets", [
                "Use the thumbs up or thumbs down under an answer to rate it; for a thumbs down you can say what was wrong. This feeds the quality figures on the Analytics page.",
                "Choose a suggested follow-up question, copy the answer, or start a <b>New chat</b>.",
                "Open <b>Chat History</b> to find, rename or delete earlier conversations.",
                "If asking fails (for example the AI service cannot be reached) the message shows the reason and a <b>Retry</b> button.",
            ]),
            ("img", "assistant.png", "An answer with its source card: document, version, page and quote. The thumbs below rate the answer.", 600),
        ],
    },
    {
        "id": "citations", "title": "Opening cited passages and PDF pages",
        "blocks": [
            ("steps", [
                "Click a source card under an answer (or <b>Open page N</b> on a search result).",
                "The built-in viewer opens on the cited page. The supporting passage is highlighted in yellow.",
                "Use the arrow buttons or type a page number to read other pages. If an answer has several sources, use the tabs at the top to switch between them.",
                "Choose <b>Open full PDF</b> to open the whole file in a new browser tab, or <b>Close</b> (or press <b>Esc</b>) to return.",
            ]),
            ("p", "The viewer shows a short sentence under the page controls. \"The supporting passage is highlighted\" means the application found the passage on the page with confidence. "
                  "If it could not locate the exact position reliably, it opens the right page <b>without</b> a highlight and tells you so; it never guesses."),
            ("note", "Older answers created before highlighting existed open the page but cannot be highlighted."),
            ("img", "citation_viewer.png", "The citation viewer: the quoted passage, page controls and the highlighted text on the real PDF page.", 600),
        ],
    },
    {
        "id": "versions", "title": "Understanding document versions and version history",
        "blocks": [
            ("p", "Documents change. Instead of replacing a file, DocuMind AI keeps every upload as a numbered <b>version</b> of the same document: Version 1, Version 2 and so on. "
                  "Your collections, tags, shares, conversations and reviews stay attached to the document."),
            ("h2", "The current version"),
            ("bullets", [
                "Exactly one version is <b>Current</b>. Search, AI answers, conflict checks and the PDF preview use it.",
                "A new version becomes current only after it has been fully processed. Until then, and if processing fails, the previous version stays current and keeps working.",
                "Older versions are never deleted by newer uploads. You can still view, download, compare and restore them.",
            ]),
            ("h2", "Reading the version history"),
            ("p", "Open a document and scroll to <b>Version history</b>. Each row shows the version number, a <b>Current</b> or <b>Earlier version</b> badge, its status "
                  "(Queued, Processing, Ready or Failed), who uploaded it and when, its size and pages, and the note about what changed. A <b>Restored from vN</b> badge "
                  "tells you that the version is a copy of an older one."),
            ("table", ["Button", "What it does"], [
                ["Eye (View version N)", "Opens that version's own PDF in the viewer, even if it is not current"],
                ["Download (Download version N)", "Downloads that version's file"],
                ["Restore", "Makes a copy of that version the new latest version (chapter 10). Editors and owners only"],
                ["Retry", "Starts processing again for a version that failed. Editors and owners only"],
            ], [34, 66]),
            ("img", "version_history.png", "Version history of one document. Version 6 is current; earlier versions can be viewed, downloaded or restored.", 600),
        ],
    },
    {
        "id": "newversion", "title": "Uploading a new version",
        "blocks": [
            ("steps", [
                "Open the document and, in <b>Version history</b>, choose <b>Upload new version</b>. (This button is shown to owners and editors only.)",
                "Choose the new PDF. Optionally describe what changed, for example \"Parental leave raised to eighteen weeks\".",
                "Choose <b>Upload version</b>. The new version appears as <b>Queued</b>, then <b>Processing</b> with a percentage.",
                "When it shows <b>Ready</b> and <b>Current</b>, search and answers use the new text.",
            ]),
            ("h2", "Things to know"),
            ("bullets", [
                "If the new file is <b>identical</b> to the current version, nothing is created and a message tells you so.",
                "Only one new version of a document can be processed at a time. If you try to add another meanwhile you are asked to wait.",
                "The same rules as for normal uploads apply: PDF only, size and page limits, no password protection.",
                "If processing fails, the version is marked <b>Failed</b> with the reason, the old version stays current, and you can use <b>Retry</b> or upload a corrected file.",
                "Review schedules do not change when you upload a version, but the document page tells you when a version is newer than the last review (chapter 13).",
            ]),
        ],
    },
    {
        "id": "compare", "title": "Comparing and restoring versions",
        "blocks": [
            ("h2", "Compare two versions"),
            ("steps", [
                "In <b>Version history</b> tick the boxes of two versions, then choose <b>Compare selected</b>.",
                "The older version is always shown as the left side (\"from\") and the newer as the right side (\"to\"). Counters summarize <b>added</b>, <b>removed</b>, <b>changed</b> and <b>unchanged</b> passages.",
                "Removed text is red with a minus sign; added text is green with a plus sign. In a changed passage the exact words that differ are marked. Long unchanged stretches are collapsed.",
                "Choose <b>Back to version history</b> to return.",
            ]),
            ("important", "The comparison looks at the <b>extracted text only</b>. It cannot see changes in images, fonts, tables drawn as pictures or page design. If a version has no readable text or failed processing, "
                         "the page says that these versions cannot be compared reliably and why."),
            ("img", "compare.png", "Comparing version 1 with version 2: \"sixteen\" was replaced by \"eighteen\" and a new sentence was added.", 600),
            ("h2", "Restore an older version"),
            ("steps", [
                "Choose <b>Restore</b> on the version you want back and confirm. The dialog explains that no version is deleted.",
                "The application creates a <b>new latest version</b> with the contents of the old one (for example restoring Version 1 when Version 3 exists creates Version 4, marked \"Restored from v1\").",
                "When it is processed it becomes current. Nothing is removed from the history, so you can restore any other version later.",
            ]),
            ("p", "You cannot restore the version that is already current, a version that failed, or while another version is still being processed."),
            ("h2", "Old answers keep their original source"),
            ("p", "An AI answer is never rewritten when a document changes. Its citation shows the version it came from (for example <b>v1 (earlier version)</b>). "
                  "Opening that citation shows the <b>original file and page</b> with a notice that you are viewing an earlier version."),
            ("img", "historical_citation.png", "A citation from an earlier answer opens the earlier version of the file and says so.", 600),
        ],
    },
    {
        "id": "sharing", "title": "Sharing collections and managing team roles",
        "blocks": [
            ("p", "You share a <b>collection</b>, not your whole account. The people you add can use the documents in that collection and nothing else of yours. "
                  "Your other documents stay private."),
            ("h2", "Share a collection"),
            ("steps", [
                "Open <b>Knowledge Base</b> and click the collection (you must be its owner).",
                "In <b>Members and sharing</b> choose <b>Share</b>.",
                "Enter the email address the person used to register. They must already have a DocuMind AI account.",
                "Choose <b>Viewer</b> or <b>Editor</b> and select <b>Share</b>. Access starts immediately; there is nothing for the other person to accept.",
            ]),
            ("h2", "Change a role, revoke access or leave"),
            ("bullets", [
                "Owner: change someone's permission with the drop-down next to their name.",
                "Owner: choose the revoke icon (a person with a minus sign) next to a member and confirm. The person loses access to everything in the collection <b>at once</b>: documents, versions, search results, AI answers, files and findings.",
                "Members can leave a collection themselves with the leave icon next to their own name.",
            ]),
            ("p", "Collection cards show <b>Private</b> or <b>Shared with N people</b> for the owner, and your role (Viewer or Editor) with the owner's name for collections shared with you. "
                  "On <b>My Documents</b> the <b>Show</b> filter switches between <b>My uploads</b>, <b>Shared with me</b> and <b>Everything I can access</b>."),
            ("img", "sharing.png", "Members and sharing on a collection page: the owner, an Editor and a Viewer, with role selectors.", 600),
        ],
    },
    {
        "id": "roles", "title": "Understanding Owner, Editor and Viewer permissions",
        "blocks": [
            ("p", "Permissions are enforced by the server on every request. Hiding a button is only a convenience; a person without permission cannot do the action even by other means."),
            ("table", ["Action", "Owner", "Editor", "Viewer"], [
                ["See the collection, its members and documents", "Yes", "Yes", "Yes"],
                ["Search, ask questions, open PDFs, citations and version history, download any version, compare", "Yes", "Yes", "Yes"],
                ["Read review schedules, review history and conflict findings", "Yes", "Yes", "Yes"],
                ["Add own documents to, or remove documents from, the collection", "Yes", "Yes", "No"],
                ["Change a shared document's category and tags", "Yes", "Yes", "No"],
                ["Upload a new version, restore a version, retry failed processing", "Yes", "Yes", "No"],
                ["Schedule, start and complete reviews", "Yes", "Yes", "No"],
                ["Run a conflict analysis and record decisions", "Yes", "Yes", "No"],
                ["Edit or delete the collection; invite, change roles, revoke members", "Yes", "No", "No"],
                ["Delete a document", "Only the person who uploaded it", "No", "No"],
            ], [52, 16, 16, 16]),
            ("h2", "Good to know"),
            ("bullets", [
                "An Editor can add only documents that they uploaded themselves to a shared collection. They cannot pull in anyone else's private documents.",
                "The owner of a collection can read and manage the documents in it even if an Editor uploaded them, but only the uploader can delete the file.",
                "Category and tag names belong to the person who uploaded the document, so an Editor who labels a shared document uses the owner's labels.",
                "If you are not allowed to see something, the application behaves as if it does not exist (\"not found\"). It does not reveal names or other details.",
            ]),
        ],
    },
    {
        "id": "reviews", "title": "Scheduling and completing content reviews",
        "blocks": [
            ("p", "A review is a check that a document is still correct and up to date. Owners and Editors can schedule reviews and record the result; everyone who can read the document can see them."),
            ("h2", "Schedule a review"),
            ("steps", [
                "Open the document and find the <b>Content review</b> section.",
                "Choose <b>Schedule review</b> (or <b>Edit schedule</b>).",
                "Pick the <b>Next review date</b> and/or how often to repeat (in days; the buttons 30, 90 and 180 days are shortcuts). Add notes if you like and choose <b>Save schedule</b>.",
            ]),
            ("p", "The date must be today or later and not more than ten years ahead; the repeat interval must be a whole number of days from 1 to 3650. The application explains any mistake before saving."),
            ("h2", "Complete a review"),
            ("steps", [
                "Optionally choose <b>Start review</b> so colleagues can see that a review is in progress.",
                "Read the document, then choose <b>Complete review</b>.",
                "Select the <b>Outcome</b>: Approved as current, Changes required, Outdated content, or Needs clarification. Add notes.",
                "Optionally set the next review date. If you leave it empty the next date is today plus the repeat interval, or nothing is scheduled when there is no interval. Choose <b>Record review</b>.",
            ]),
            ("p", "Every completed review is added to the <b>Review history</b> under the document with the date, <b>your name</b>, the outcome, your notes and the <b>version you reviewed</b>. "
                  "You cannot record a review in someone else's name, and history entries are never changed later. If a newer version is uploaded after a review, "
                  "the page shows \"A newer version has been uploaded since the last review\"; the schedule itself stays as it was."),
            ("p", "<b>Remove schedule</b> clears the dates and interval but keeps the history."),
            ("img", "review_panel.png", "The Content review section: status, next date, last review, a warning about a newer version, and the history.", 600),
        ],
    },
    {
        "id": "overdue", "title": "Understanding due and overdue reviews",
        "blocks": [
            ("p", "The status of a review is worked out from its dates every time you look at it. Nobody has to update it, and it changes by itself as days pass. "
                  "Dates are calendar dates in UTC, so a date changes over at midnight UTC for everybody."),
            ("table", ["Status", "When"], [
                ["Upcoming", "The next review date is more than 14 days away"],
                ["Due", "The next review date is today or within the next 14 days"],
                ["Overdue", "The next review date has passed and no review was completed since"],
                ["In review", "Someone started a review and has not completed it yet"],
                ["Reviewed", "A review was completed and no further date is scheduled"],
                ["Not scheduled", "There is no review date and no review has ever been recorded"],
            ], [22, 78]),
            ("p", "The 14-day window is the default; an administrator can change it. A document is never marked outdated just because nobody opened it."),
            ("h2", "The Reviews page"),
            ("steps", [
                "Open <b>Reviews</b> in the menu. The cards show how many documents are scheduled, due within the window, overdue, and how many reviews were completed in the last 30 days. Click a card to filter the list.",
                "Use the search box, the status and collection filters, and <b>Assigned to me</b> to narrow the list.",
                "Each row shows the document, its current version, the next review date (\"3 days overdue\", \"due in 40 days\"), the reviewer and a note when a new version exists since the last review. Click the name to open the document.",
                "<b>Recently completed reviews</b> at the bottom lists the latest results.",
            ]),
            ("p", "The page lists only documents that have a review record and that you may read. The numbers are counted from the stored dates; nothing is estimated."),
            ("img", "reviews_dashboard.png", "The Reviews page: summary cards, one overdue document and a recently completed review.", 600),
        ],
    },
    {
        "id": "conflicts", "title": "Running potential-conflict detection",
        "blocks": [
            ("p", "Different documents sometimes say different things, for example two policies with different retention periods. DocuMind AI can look for such <b>potential conflicts</b>. "
                  "It uses an AI model to compare short passages, so the result is a <b>suggestion for a person to check</b>, never a verdict."),
            ("h2", "Analyze one document"),
            ("steps", [
                "Open the document and find <b>Potential conflicts</b>. You must be an owner or editor of it, and it must be Completed.",
                "Choose <b>Analyze for conflicts</b>. The button shows that it is working. With a local model this can take from seconds to several minutes; you may leave the page open.",
                "When it finishes you are told how many potential conflicts were found and how many passages and pairs were examined.",
            ]),
            ("h2", "Analyze a whole collection"),
            ("steps", [
                "Open <b>Reviews</b> and the <b>Potential conflicts</b> tab.",
                "Under <b>Analyze a collection</b> choose a collection you can edit and select <b>Analyze collection</b>.",
            ]),
            ("h2", "How it works, in plain words"),
            ("bullets", [
                "The application picks passages that state rules, numbers, deadlines or limits and looks for similar passages in other documents you can read (and, for one document, in its previous version).",
                "Only the most promising pairs are sent to the AI model, <b>two passages at a time</b>. Whole documents and documents you may not read are never sent.",
                "The model's answer is checked: if it claims a conflict, the words it quotes must appear word for word in both passages. Otherwise the finding is shown as <b>Needs human review</b>.",
                "Pairs that the model judges compatible are not shown. Answers that cannot be read are counted and ignored.",
            ]),
            ("note", "A run looks at a limited number of passages and pairs to keep cost and time down, so it can miss conflicts. A small local model finds fewer conflicts than a large hosted one. No conflict is ever resolved or changed automatically, and no document is edited."),
        ],
    },
    {
        "id": "evidence", "title": "Reviewing evidence and recording conflict decisions",
        "blocks": [
            ("h2", "Read a finding"),
            ("p", "Each finding is a card with: a label (<b>Potential conflict</b> or <b>Needs human review</b>), a type (for example different values), a short explanation, "
                  "and two evidence boxes <b>Source A</b> and <b>Source B</b>. Each box names the document, its <b>version</b>, the page and quotes the exact passage. "
                  "The line under the explanation reminds you that this is an AI-assisted suggestion and tells you whether the quoted evidence matched both passages."),
            ("bullets", [
                "Click a document name in an evidence box to open <b>that version and page</b> with the passage highlighted.",
                "<b>Source changed - re-analyze</b> means that one of the documents has a newer version since the finding was made. The finding still shows the old text it was based on. Run the analysis again to check the current text.",
                "<b>Between versions</b> marks a finding that compares a document with its own earlier version.",
            ]),
            ("h2", "Record your decision"),
            ("steps", [
                "Read both passages carefully, in context if needed.",
                "Choose <b>Confirm conflict</b>, <b>Not a conflict</b> or <b>Needs further review</b>. (These buttons appear only for editors of both documents.)",
                "Add a note if useful and choose <b>Record decision</b>.",
            ]),
            ("p", "The card now shows your decision, your name and the time. <b>Decision history</b> lists every decision ever recorded for the finding. The AI's own label does not change when you decide, and "
                  "neither document is modified. Deciding which document is right is your organisation's job; the application does not do it for you."),
            ("img", "conflict_finding.png", "A finding with evidence from two documents, a recorded decision and its history.", 600),
            ("h2", "Who can see findings"),
            ("p", "A finding is shown to you only while you can read <b>both</b> documents. If one of them stops being shared with you, the finding disappears for you completely, including names and quotes. "
                  "Viewers can read findings but cannot analyze or decide."),
        ],
    },
    {
        "id": "trouble", "title": "Troubleshooting common errors",
        "blocks": [
            ("table", ["What you see", "What it means and what to do"], [
                ["Only PDF files are supported. / This file is not a valid PDF.", "The file is not a real PDF. Export or print the document to PDF and upload that"],
                ["The file is larger than the 20 MB limit.", "Compress the PDF or split it. Your administrator can raise the limit"],
                ["Password-protected PDFs are not supported.", "Remove the password in a PDF tool and upload again"],
                ["No extractable text was found ... OCR is not supported yet.", "The PDF is made of scanned pictures. Use a PDF that contains selectable text"],
                ["Document stays Queued for a long time", "The background worker is not running. Tell your administrator (it must be started with the application)"],
                ["The embedding model is unavailable ...", "The search/AI preparation component could not run. Wait and use Retry; if it continues, tell your administrator"],
                ["The AI provider could not be reached. / took too long to respond.", "The AI model is not running or is too slow. Try again; tell your administrator if it persists"],
                ["I couldn't find enough evidence in your documents to answer that.", "Your documents do not contain a supported answer. Rephrase, select the right documents, or check that they are Completed"],
                ["Semantic search is unavailable right now.", "Use Keyword mode, or try again later"],
                ["No document contained every word, so these results contain at least one of them.", "A normal notice in keyword search. Add or remove words to be more specific"],
                ["This file is identical to the current version.", "You uploaded the same file again. Nothing was changed"],
                ["Another version of this document is still being processed.", "Wait until the Queued or Processing version finishes"],
                ["No registered user has that email address.", "The person must create an account first; check the spelling"],
                ["You need editor access to do that. / Only the collection owner can do that.", "Your role does not allow this action (chapter 12). Ask the owner"],
                ["Document not found / Collection not found", "It does not exist, or you no longer have access (for example after being removed from a shared collection)"],
                ["The review date must be today or later.", "Choose a date from today onwards"],
                ["The analysis did not finish (interrupted)", "The server restarted while it was running. Start the analysis again"],
                ["Your session has expired. Please sign in again.", "Sign in again; your work is kept"],
            ], [44, 56]),
            ("tip", "If something looks wrong after a change by a colleague, reload the page. Pages update by themselves only while a document is being processed."),
        ],
    },
    {
        "id": "privacy", "title": "Privacy, permissions and important limitations",
        "blocks": [
            ("h2", "Who can see what"),
            ("bullets", [
                "Your documents are private to you until you put them into a collection and share that collection. Sharing a collection shares only the documents in it.",
                "Everything is checked on the server for every request: documents, files, pages, citations, search results, versions, review data and findings. Other people's private documents do not appear in your search, answers, counts or error messages.",
                "When you remove a member or take a document out of a shared collection, the effect is immediate. Old conversations keep their text, but citations to documents the person can no longer read show no name or quote.",
                "Passwords are stored only as secure hashes. Uploaded files are stored on the server under generated names.",
            ]),
            ("h2", "What is sent to the AI model"),
            ("p", "Only short passages from documents you are allowed to read are sent to the AI model that your administrator configured, together with your question. "
                  "If the model is hosted by a third party, those passages leave your organisation's computer; if it runs locally (for example with Ollama) they stay on your own machine. "
                  "Ask your administrator which applies."),
            ("h2", "Limitations you should know"),
            ("bullets", [
                "PDF only. Pictures of text (scans) cannot be read because there is no OCR.",
                "AI answers and conflict findings can be wrong or incomplete. Always check the cited passage; conflicts always need a person's decision.",
                "Version comparison looks at text only, not at layout or images.",
                "Search matches words by their beginning; it does not correct typing mistakes or match different word forms.",
                "Conflict analysis examines a limited number of passages per run and does not run by itself. Review reminders, emails and chat notifications do not exist; check the Reviews page.",
                "The dashboard and analytics count your own uploads. The Reviews page lists documents that have a review record.",
                "The application does not automatically delete old versions.",
            ]),
        ],
    },
]

APPENDIX = [
    ("p", "<b>Version of this guide:</b> %s, %s." % (VERSION, DATE)),
    ("p", "<b>How the screenshots were made:</b> they are real screenshots of the application taken during a test run on %s with sample documents and three sample people, "
          "in a desktop browser (1366 x 900) and one in a phone-sized window (390 x 844). No screenshot is a mock-up." % DATE),
    ("p", "<b>Regenerating this guide:</b> the text lives in docs/user-guide/guide_content.py and the generator is docs/user-guide/build_user_guide.py (see the project README)."),
    ("p", "<b>Not covered here:</b> installing and configuring DocuMind AI (administrators: see the project README)."),
]
