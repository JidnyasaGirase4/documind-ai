# Release verification: browser checklist

Run on 16 October 2026 against a disposable stack (new database `documind_ai_e2e`, temporary upload/Chroma folders, backend on port 8011, Vite dev server on port 5180)
driven by headless Chrome (DevTools protocol) with the real local model `qwen2.5:3b` (Ollama) and the real embedding model. The development database was not used.
Status values: **Passed**, **Failed** (with what happened), **Blocked**, **Not Tested**. Items that failed first and were fixed are listed with their history.

| Item | Status | Notes |
|---|---|---|
| A1 landing page loads | Passed |  |
| A2 protected URL redirects to /login when signed out | Passed |  |
| A3 register via UI and land in the app | Passed | /app/dashboard |
| A4 sign out | Passed |  |
| A5 wrong password shows an error and stays on /login | Passed | DocuMind AI / Answers you can trace back to the page. / Answers you can trace back to the page. / employee-handbook.pdf / Completed / How many days of parental leave does the policy allow? /  / The policy allows 16 |
| A6 sign in | Passed |  |
| A7 direct URL /app/dashboard (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/documents (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/search (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/knowledge (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/reviews (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/assistant (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/history (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/analytics (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| A7 direct URL /app/settings (refresh) renders | Passed | Skip to content / DocuMind AI /  / MENU /  / Dashboard / My Documents / Search / Knowledge Base /  |
| B0 documents page shows an empty state for a new account | Passed | Empty state shown for a new account (first run). |
| B2 four valid PDFs processed to Completed | Passed | {'scanned-like.pdf': 'failed', 'private-merger.pdf': 'ready', 'retention-legal.pdf': 'ready', 'retention-hr.pdf': 'ready', 'leave-policy-v1.pdf': 'ready'} |
| B3 a PDF without enough text fails with an explained error and offers retry | Passed | No extractable text was found. This PDF may contain only scanned images; OCR is not supported yet. |
| B4 AI answer arrives with a Sources section | Passed | How many weeks of paid parental leave do primary caregive... / just now / How many weeks of paid parental leave do primary caregive... /  / Updated Oct 16, 2026, 1:12 PM /  / Searching in: / All my documents / How many weeks of paid parental leave do primary caregiv |
| B5 answer mentions the right value | Passed |  |
| B6 citation card names the document and page | Passed |  |
| B7 citation opens the PDF page in the viewer | Passed | leave-policy-v1.pdf /  / Source 1 of 1 · cited page 1 /  / Version 1 (current). /  / “Leave Policy Primary caregivers are entitled to sixteen weeks of paid parental leave.  |
| B8 the cited passage is highlighted on the page | Passed | highlight rectangles=4; note: The supporting passage is highlighted.  Open full PDF Close |
| B9 Escape closes the viewer | Passed |  |
| B10 a question with no support gets an honest 'not enough evidence' answer | Passed | Mars? /  / Oct 16, 2026, 1:12 PM /  / I couldn't find enough evidence in your documents to answer that. Try rephrasing the question, or select the documents that should contain the answer. /  / Oct 16, 2026, 1:12 PM / Copy answer / Ask a question about your documents /  / Enter t |
| C1 hybrid search finds both retention policies | Passed |  |
| C2 results show snippet, page link and a highlighted match | Passed | marks=9 |
| C3 keyword search finds the 7-year policy only | Passed | Verified that the 7-year policy is found; that the other policy is excluded was not asserted (exact phrase exclusivity is C4). |
| C4 exact phrase search matches only the document containing the phrase | Passed |  |
| C5 semantic search finds retention documents without sharing exact words | Passed | similarity shown: True |
| C6 no-results state | Passed |  |
| C7 category filter narrows results | Passed |  |
| C8 collection filter and sort controls respond | Passed | ?q=retained&category=1&collection=1&sort=title |
| C9 Clear filters resets category and collection | Passed | ?q=retained&sort=title |
| C10 opening a result lands on the document page with the viewer on the right page and highlight | Passed | url=?page=1&chunk=chunk-1 highlights=4 |
| C11 pagination across pages | Not Tested | only 4 searchable documents in this run (covered by automated tests) |
| C12 embedding model unavailable behaviour | Not Tested | would require stopping the model; covered by automated tests |
| D1 owner shares the collection with a Viewer and an Editor from the UI | Passed |  |
| D2 inviting an unregistered email shows a clear error | Passed |  |
| D3 viewer's My Documents is empty (nothing of their own) | Passed |  |
| D4 viewer sees only the shared collection's documents | Passed | ['leave-policy-v1.pdf', 'retention-hr.pdf', 'retention-legal.pdf'] |
| D5 the owner's private document is not discoverable by id (404) | Passed | id=4 |
| D6 viewer sees the shared collection labelled as shared/viewer | Passed |  |
| D7 search for private content returns nothing | Passed |  |
| D8 viewer document page: no Delete/Organize/Upload-version/Restore/Schedule buttons | Passed |  |
| D9 backend refuses a viewer's direct upload-version request | Passed | The first attempt sent an empty body and got 422 (not a permission test). Re-tested with a real PDF as Viewer: upload version, restore, metadata edit, review PUT and conflict analyze all returned 403. |
| D10 backend refuses a viewer's attempt to invite someone | Passed | status=403 |
| D11 viewer can ask questions about shared documents and gets citations | Passed |  |
| D12 AI cannot reveal the owner's private document to the viewer | Passed |  |
| D13 editor can edit labels of a shared document | Passed | status=200 |
| D14 editor cannot delete the owner's document | Passed | status=403 |
| D15 editor cannot manage members | Passed | status=403 |
| D16 revoke asks for confirmation | Passed |  |
| D17 member disappears from the list after revoke | Passed |  |
| D18 revoked viewer: document page says not found | Passed |  |
| D19 revoked viewer: search returns nothing | Passed |  |
| D20 revoked viewer: PDF preview endpoint refuses | Passed | status=404 |
| E1 version history shows version 1 as Current | Passed |  |
| E2 new version is created as version 2 and is NOT current while processing | Passed | v2 status at first look: queued |
| E3 while v2 processes, search still returns the old text and not the new | Passed | Verified with a timed probe (single-word queries): while a restore job was queued, the old text was still found and the new text was not; after activation the results flipped in one step. (The first attempt used two-word queries, which correctly fell back to 'any word' matching, so it asserted the wrong thing.) |
| E4 version 2 becomes current when ready; version 1 is kept as history | Passed |  |
| E5 new text is searchable, old text is not (current-version retrieval) | Passed | Single-word probe: 'eighteen' found, 'sixteen' not found after version 2 became current. |
| E6 AI answer now reflects version 2 (and cites v2) | Passed |  |
| E7 the new citation names its version | Passed |  |
| E8 comparison highlights removed 'sixteen' and added 'eighteen' | Passed | del=['sixteen'] ins=['eighteen'] |
| E9 comparison states it is a text comparison | Passed |  |
| E10 restore asks for confirmation and explains no history is deleted | Passed |  |
| E11 restore created version 3 'Restored from v1' and made it current; v1 and v2 remain | Passed |  |
| E12 after restore the old text is searchable again and the v2 text is not | Passed | Single-word probe after restore: 'sixteen' found again, 'eighteen' not found. |
| E13 the old answer is unchanged and its citation is labelled with its version | Passed |  |
| E14 the historical citation opens the original version's page with the passage highlighted | Passed | Opened the citation of the earlier answer: the earlier version's file and page opened with a highlight and the 'viewing version N, an earlier version' notice (my first assertion looked for a capital-V string). |
| E15 viewer sees version history but no upload/restore controls | Passed |  |
| F1 a never-scheduled document shows 'Not scheduled' | Passed |  |
| F2 a past date is rejected with a message | Passed |  |
| F3 an invalid interval is rejected with a message | Passed |  |
| F4 valid schedule saved: status Due (inside the 14-day window), next date and interval shown | Passed |  |
| F5 start review sets 'In review' | Passed |  |
| F6 completion recorded in history with outcome, note, reviewer and version | Passed |  |
| F7 next review date was proposed from the interval (today + 90 days) | Passed |  |
| F8 a newer version after the review shows the 'newer version since last review' warning; schedule unchanged | Passed |  |
| F9 dashboard counts match the stored dates (scheduled 3, overdue 1, due 1) | Passed | Counts match the stored dates: scheduled 3, overdue 1, upcoming 2, due 0 (my first expectation of 'due 1' was wrong: that document's next date had been moved 90 days ahead by completing its review). |
| F10 the overdue document is listed as Overdue with 'days overdue' text | Passed |  |
| F11 the status filter shows only overdue documents | Passed | ['retention-hr.pdf'] |
| F12 viewer can read the review panel but has no schedule/complete buttons | Passed |  |
| G1 empty state before any analysis | Passed |  |
| G2 running state is shown while the model works | Passed |  |
| G3 analysis with the configured local model (qwen2.5:3b) finishes | Passed | 23s; findings=1; report text: Examined 1 passages and 1 candidate pairs.  Potential conflict Other Awaiting review  Passage A states that employee per |
| G4 finding shows evidence from BOTH documents with version labels | Passed | assessment=potential_conflict quotes_verified=True |
| G5 the page says findings are AI-assisted and need human verification | Passed |  |
| G6 decision recorded: status, reviewer and note shown | Passed |  |
| G7 decision history lists the decision with name and time | Passed |  |
| G8 the AI's own assessment label is unchanged by the human decision | Passed |  |
| G9 evidence links carry document, page, passage and version | Passed | ['/app/documents/2?page=1&chunk=chunk-3&version=2', '/app/documents/3?page=1&chunk=chunk-4&version=3'] |
| G10 an evidence link opens the PDF page with the passage highlighted | Passed |  |
| G11 viewer sees the finding (both sources readable) but no decision buttons or Analyze button | Passed |  |
| G12 after one source stops being shared, the viewer sees no trace of the finding or the other document | Passed |  |
| G13 after a source gets a new version the finding is marked 'Source changed' and still shows the old evidence/version | Passed |  |
| G14 semantic search with the embedding model unavailable shows a plain message (no internals) | Passed | Semantic search is unavailable right now. Try keyword search or try again later.  Try again |
| G15 hybrid search falls back to keyword results with a notice | Passed |  |
| G16b conflict analysis with ONLY the AI model unreachable ends in a clear error, not a crash | Passed | The AI provider could not be reached. |
| G17b (AI model unreachable) assistant shows a failed-message state with a retry option when the AI cannot answer | Passed | How long must records be retained? / The AI provider could not be reached. / Retry / Ask a question about your documents /  / Enter to send · Shift+Enter for a new line /  / Send |
| H1 desktop (1366px): no horizontal page scroll on 9 pages | Passed | [] |
| H1 tablet (820px): no horizontal page scroll on 9 pages | Passed | [] |
| H2 tablet: navigation menu button present | Passed |  |
| H1 phone (390px): no horizontal page scroll on 9 pages | Passed | [] |
| H2 phone: navigation menu button present | Passed |  |
| H3 accessible names on /document | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H3 accessible names on /search | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H3 accessible names on /reviews | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H3 accessible names on /collection | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H3 accessible names on /knowledge | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H3 accessible names on /documents | Passed | {'unlabeled': [], 'unlabeledCount': 0, 'imgsWithoutAlt': 0, 'h1': 1} |
| H4 keyboard: Tab reaches interactive controls in order on the document page | Passed | 40 stops, e.g. ['Skip to content', 'DocuMind AI home', 'Dashboard', 'My Documents', 'Search', 'Knowledge Base', 'Reviews', 'AI Assistant'] |
| H5 keyboard: every focused control shows a visible focus indicator (outline or ring) | Passed | without indicator: [] |
| H6 keyboard: Tab stays inside an open dialog (focus trap) | Passed | [True, True, True, True, True, True, True, True, True, True, True, True] |
| H7 keyboard: Escape closes the dialog and focus returns to the opener | Passed | Share |
| I1 create a collection (name, description, colour, icon) from the Knowledge Base page | Passed |  |
| I2 a duplicate collection name is refused with a message | Passed |  |
| I3 create a category | Passed |  |
| I4 organize a document: category, tag and collection saved and shown on its row | Passed |  |
| I5 documents list can be filtered by category | Passed | ['retention-legal.pdf'] |
| I6 Chat History lists earlier conversations | Passed |  |
| H1 phone (390px): no horizontal page scroll on 9 pages (first run) | Failed -> fixed -> Passed | The 'Complete review' button overflowed the card by 7 px on the document page. Fixed (card headers stack on small screens); re-run passed on all 9 pages. |
| H8 contrast (first run) | Failed -> fixed -> Passed | Red text (#d92d20) measured 4.35-4.44:1, just under the AA minimum of 4.5:1 (Delete button, Overdue badge). Darkened to #c8281c (about 5.1:1); re-run found no text pair under 4.5:1 on 7 pages. Text on the dark sidebar and on gradient buttons cannot be measured by my script: Not Tested. |
| H8 contrast re-run after the fix (document, reviews, search, dashboard, knowledge, documents, conflicts) | Passed | No text/background pair under 4.5:1 on solid backgrounds. Not measurable by the script (Not Tested): white text on the dark sidebar and on gradient buttons. |
| H7 focus returns to the opener (first run) | Test artifact -> Passed | A scripted click does not move focus; after focusing the button first, focus returned to 'Share' after Escape. |
| CORS preflight for PUT (found by code review, not by the browser run) | Failed -> fixed -> Passed | The API allowed GET/POST/PATCH/DELETE only, but the review schedule uses PUT, so a real browser would block it. Fixed; a new test checks every method the API uses. |
| Visual: 'Analyze for conflicts' button text wrapped and was clipped | Failed -> fixed -> Passed | Buttons no longer wrap their labels (seen in a screenshot, confirmed fixed in a later one). |
| Visual: '1 pages' / '1 passages' wording | Failed -> fixed | Singular forms are used now. |
| Pagination across several pages of search results in the browser | Not Tested | Only 4 documents were searchable in this run; pagination is covered by automated tests. |
| Download of a version file through the browser | Not Tested | Headless Chrome does not show a download; the endpoint is covered by automated tests. |
| Real-device phone testing | Not Tested | Only a phone-sized window (390 x 844) in desktop Chrome was used. |
| Browsers other than Chrome (Firefox, Safari, Edge) | Not Tested |  |
| Screen reader testing | Not Tested | Only automated checks (accessible names, focus order, focus visibility, focus trap, contrast) were run. |
