import { Link } from 'react-router-dom'
import { ArrowRight, ArrowUp, ArrowUpRight } from 'lucide-react'
import { Logo } from '../common/Logo'

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { to: '/features', label: 'Features' },
      { to: '/how-it-works', label: 'How It Works' },
      { to: '/about', label: 'About' },
    ],
  },
  {
    title: 'Account',
    links: [
      { to: '/login', label: 'Log In' },
      { to: '/register', label: 'Create account' },
    ],
  },
]

const NOTES = ['PDF files only for now', 'Answers cite document and page', 'Scanned images are not processed']

// Bold brand-coloured footer with a rounded top edge.
export function PublicFooter() {
  return (
    <footer className="relative mt-6 overflow-hidden rounded-t-[2rem] bg-gradient-to-br from-brand-800 via-brand-700 to-plum-950 text-brand-100">
      <div className="pointer-events-none absolute -left-16 -top-24 h-72 w-72 rounded-full bg-brand-400/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 right-10 h-64 w-64 rounded-full bg-gold-400/15 blur-3xl" />
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-15 invert" aria-hidden="true" />

      <div className="container-page relative grid grid-cols-1 gap-10 pb-10 pt-12 lg:grid-cols-[1.3fr_1.7fr] lg:gap-16">
        <div>
          <Logo dark />
          <p className="mt-6 max-w-sm font-display text-2xl font-bold leading-snug text-white">
            Ask your documents.
            <br />
            <span className="text-gold-400">Verify the answer.</span>
          </p>
          <p className="mt-3 max-w-sm text-[15px] leading-relaxed text-brand-100/90">
            Get answers from your PDFs with source references you can check.
          </p>
          <Link
            to="/register"
            className="group mt-5 inline-flex h-10 items-center gap-2 rounded-control bg-white px-4 text-sm font-semibold text-ink shadow-card transition-all hover:-translate-y-0.5 hover:bg-brand-50"
          >
            Start for free
            <ArrowRight className="h-4 w-4 text-brand-600 transition-transform group-hover:translate-x-1" aria-hidden="true" />
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          {COLUMNS.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <h2 className="text-[13px] font-bold uppercase tracking-[0.16em] text-gold-400">{col.title}</h2>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.to}>
                    <Link to={l.to} className="group inline-flex items-center gap-1 text-sm font-medium text-white/90 transition-colors hover:text-white">
                      {l.label}
                      <ArrowUpRight className="h-3.5 w-3.5 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
          <div className="col-span-2 sm:col-span-1">
            <h2 className="text-[13px] font-bold uppercase tracking-[0.16em] text-gold-400">Good to know</h2>
            <ul className="mt-4 space-y-2.5">
              {NOTES.map((n) => (
                <li key={n} className="flex items-start gap-2 text-[15px] text-brand-100">
                  <span className="mt-2 h-1 w-3 shrink-0 rounded-full bg-gold-400" aria-hidden="true" />
                  {n}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="relative border-t border-white/15">
        <div className="container-page flex flex-col gap-3 py-4 text-xs text-brand-100/90 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} DocuMind AI</p>
          <p className="sm:flex-1 sm:px-6 sm:text-center">Privacy Policy and Terms of Service: placeholder — legal pages have not been published yet.</p>
          <button
            type="button"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="group inline-flex items-center gap-1.5 self-start rounded-full bg-white/10 px-3 py-1.5 font-semibold text-white ring-1 ring-inset ring-white/20 transition-colors hover:bg-white/20 sm:self-auto"
          >
            Back to top
            <ArrowUp className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </footer>
  )
}
