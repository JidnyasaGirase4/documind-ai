import { BarChart3, BookOpenCheck, FileSearch, History, Library, ShieldCheck } from 'lucide-react'

export const FEATURES = [
  {
    icon: FileSearch,
    title: 'PDF knowledge search',
    text: 'Ask questions in plain language. DocuMind AI searches the text of your uploaded PDFs for the passages that matter.',
  },
  {
    icon: BookOpenCheck,
    title: 'Cited answers',
    text: 'Answers come with the document name and page number of the passages they are based on, so you can check the source yourself.',
  },
  {
    icon: Library,
    title: 'Document library',
    text: 'Upload, search, filter and manage your PDFs in one place, and see the processing status of each file.',
  },
  {
    icon: History,
    title: 'Conversation history',
    text: 'Pick up where you left off. Conversations are saved, searchable, and can be renamed or deleted.',
  },
  {
    icon: ShieldCheck,
    title: 'Secure document access',
    text: 'You sign in to your own account, and the server checks ownership on every request so your documents stay yours.',
  },
  {
    icon: BarChart3,
    title: 'Usage insights',
    text: 'See how many documents you have uploaded, how they were processed, and how often you ask questions.',
  },
]

export const STEPS = [
  { title: 'Upload', text: 'Add one or more PDF files to your library.' },
  { title: 'Ask', text: 'Ask a question about one document or all of them.' },
  { title: 'Verify', text: 'Open the cited page to confirm the answer against the source.' },
]

export const USE_CASES = [
  { title: 'Teams', text: 'Look up policies, procedures and handbooks without paging through long PDFs.' },
  { title: 'Students', text: 'Find key passages in readings and lecture notes and trace them back to the page.' },
  { title: 'Developers', text: 'Search technical manuals and specifications for the section you need.' },
  { title: 'Researchers', text: 'Compare what several papers or reports say and keep the page references.' },
]

export const FAQS = [
  {
    q: 'What file types can I upload?',
    a: 'PDF files only for now. The upload screen shows the maximum file size that is currently configured.',
  },
  {
    q: 'Can DocuMind AI read scanned PDFs?',
    a: 'Not yet. PDFs need selectable text. Scanned pages without a text layer cannot be processed, and the document will be marked as failed with an explanation.',
  },
  {
    q: 'How do I know an answer is reliable?',
    a: 'Each answer lists the document and page it draws on. Open the citation to read the original passage. If the documents do not contain enough evidence, the assistant should say so rather than guess.',
  },
  {
    q: 'How long does processing take?',
    a: 'It depends on the size of the PDF and the load on the server. The status of each document is shown in your library and updates automatically.',
  },
  {
    q: 'Can other people see my documents?',
    a: 'Documents belong to your account and the server checks ownership on every request.',
  },
]

export const PIPELINE = [
  { title: 'Upload PDF', text: 'Your file is sent to the server over an authenticated request and stored for your account.' },
  { title: 'Extract text', text: 'Text is read from each page. Pages without extractable text, such as scans, cannot be used.' },
  { title: 'Split into chunks', text: 'The text is divided into overlapping passages while keeping track of the page each came from.' },
  { title: 'Index embeddings', text: 'Each passage is converted to a numeric representation so it can be searched by meaning.' },
  { title: 'Retrieve passages', text: 'When you ask a question, the most relevant passages from your own documents are selected.' },
  { title: 'Generate cited answer', text: 'An AI model writes an answer from those passages, with references back to the document and page.' },
]
