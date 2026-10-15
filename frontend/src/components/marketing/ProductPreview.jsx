import { FileText, Quote, Sparkles } from 'lucide-react'
import { ChatMessage } from '../chat/ChatMessage'
import { DocumentStatusBadge } from '../documents/DocumentStatusBadge'

// Illustrative sample content rendered with the real UI components.
// It is labelled as an example and is not live data.
const SAMPLE_USER = { role: 'user', content: 'How many days of parental leave does the policy allow?' }
const SAMPLE_ASSISTANT = {
  role: 'assistant',
  content: 'The policy allows 16 weeks of paid parental leave for each primary caregiver.',
  citations: [{ documentId: null, documentName: 'employee-handbook.pdf', page: 14, excerpt: 'Primary caregivers are entitled to sixteen weeks of paid leave…' }],
}

export function ProductPreview() {
  return (
    <div className="relative mx-auto w-full max-w-xl" aria-label="Example of the DocuMind AI interface">
      <div className="pointer-events-none absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-brand-200/60 via-gold-100/50 to-transparent blur-2xl" />

      <div className="relative animate-float rounded-3xl border border-line bg-surface p-4 shadow-pop sm:p-5">
        <div className="mb-4 flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
            <span className="icon-tile h-8 w-8">
              <FileText className="h-4 w-4" aria-hidden="true" />
            </span>
            employee-handbook.pdf
          </div>
          <DocumentStatusBadge status="ready" />
        </div>
        <div className="space-y-4">
          <ChatMessage message={SAMPLE_USER} />
          <ChatMessage message={SAMPLE_ASSISTANT} />
        </div>
        <p className="mt-4 text-center text-[13px] text-muted">Illustrative example — not live data</p>
      </div>

      <div
        className="absolute -left-2 -top-4 hidden animate-float-slow items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-xs font-semibold text-ink shadow-lift sm:flex lg:-left-6"
        aria-hidden="true"
      >
        <Sparkles className="h-4 w-4 text-gold-500" />
        Source-backed answers
      </div>
      <div
        className="absolute -right-2 bottom-16 hidden animate-float items-center gap-2 rounded-xl bg-plum-900 px-3 py-2 text-xs font-semibold text-white shadow-lift [animation-delay:-3s] sm:flex lg:-right-6"
        aria-hidden="true"
      >
        <Quote className="h-4 w-4 text-brand-300" />
        Cited: page 14
      </div>
    </div>
  )
}
