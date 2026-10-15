import { Link } from 'react-router-dom'
import { ArrowRight, FileText, History, MessageSquareText } from 'lucide-react'

const STEPS = [
  { icon: FileText, title: 'Upload a PDF', text: 'Add a text-based PDF in My Documents and wait for it to show Ready.', to: '/app/documents', cta: 'Go to My Documents' },
  { icon: MessageSquareText, title: 'Ask a question', text: 'Ask about it in the AI Assistant. Every answer shows the page it came from.', to: '/app/assistant', cta: 'Open the Assistant' },
  { icon: History, title: 'Come back anytime', text: 'Your conversations are saved here so you can reopen, rename or delete them.' },
]

// Short onboarding checklist used to fill empty pages with something useful.
export function GetStarted() {
  return (
    <section className="rounded-card border border-line bg-surface p-5 shadow-card" aria-label="Get started">
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-brand-600">Get started</p>
      <h2 className="mt-1 text-lg font-bold text-ink">Three steps to your first answer</h2>
      <ol className="mt-4 space-y-4">
        {STEPS.map(({ icon: Icon, title, text, to, cta }, i) => (
          <li key={title} className="flex gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-btn">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-bold text-ink">
                <span className="text-brand-600">{i + 1}.</span> {title}
              </p>
              <p className="mt-0.5 text-[13px] text-muted">{text}</p>
              {to && (
                <Link to={to} className="group mt-1 inline-flex items-center gap-1 text-[13px] font-semibold text-brand-700 hover:text-brand-800">
                  {cta}
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </Link>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
