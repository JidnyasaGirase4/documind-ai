import { AnimatedHeading } from '../../components/common/AnimatedHeading'
import { ArrowRight, BookOpenCheck, Database, FileText, Scissors, Search, Upload } from 'lucide-react'
import { PageBanner } from '../../components/marketing/PageBanner'
import { Button } from '../../components/common/Button'
import { PIPELINE } from '../../components/marketing/content'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'

const ICONS = [Upload, FileText, Scissors, Database, Search, BookOpenCheck]

// Items in order; phase markers sit between the steps.
const ITEMS = [
  { kind: 'phase', label: 'Phase 1', title: 'When you upload a document', highlight: 'a document', note: 'Done once per file' },
  ...PIPELINE.slice(0, 4).map((s, i) => ({ kind: 'step', n: i + 1, ...s })),
  { kind: 'phase', label: 'Phase 2', title: 'When you ask a question', highlight: 'a question', note: 'Starts from your own documents' },
  ...PIPELINE.slice(4).map((s, i) => ({ kind: 'step', n: i + 5, ...s })),
]

// Timeline where every step is shown in its normal, full-colour state.
export default function HowItWorks() {
  useDocumentTitle('How It Works')
  return (
    <div className="container-page py-10">
      <PageBanner
        eyebrow="How it works"
        title="From PDF to cited answer"
        text="This is the workflow your PDFs go through. Larger files take longer, and a document is only available for questions once its status shows Ready."
      />

      <div className="mx-auto mt-10 max-w-4xl">
        <ol className="relative" aria-label="Processing steps">
          {/* Full-length gradient line */}
          <span
            className="pointer-events-none absolute bottom-0 left-[22px] top-0 w-0.5 -translate-x-1/2 rounded-full bg-gradient-to-b from-brand-500 via-brand-400 to-gold-400 lg:left-1/2"
            aria-hidden="true"
          />

          {ITEMS.map((item) => {
            if (item.kind === 'phase') {
              return (
                <li key={item.label} className="relative z-10 flex justify-start py-5 lg:justify-center">
                  <div className="flex flex-col items-start gap-1 bg-canvas pb-1 pr-4 lg:items-center lg:px-6">
                    <span className="rounded-full bg-gradient-to-r from-plum-800 to-plum-950 px-4 py-1.5 text-[13px] font-bold uppercase tracking-[0.16em] text-white shadow-lift">
                      {item.label}
                    </span>
                    <AnimatedHeading text={item.title} highlight={item.highlight} className="mt-1 text-lg font-bold text-ink" />
                    <p className="text-xs text-muted">{item.note}</p>
                  </div>
                </li>
              )
            }

            const Icon = ICONS[item.n - 1]
            const last = item.n === PIPELINE.length
            const left = item.n % 2 === 1
            return (
              <li key={item.title} className="relative pb-10 last:pb-2">
                <span
                  className={`absolute left-0 top-0 z-10 flex h-11 w-11 items-center justify-center rounded-full border-2 border-white bg-gradient-to-br text-white shadow-glow lg:left-1/2 lg:-translate-x-1/2 ${
                    last ? 'from-gold-500 to-brand-700' : 'from-brand-500 to-brand-700'
                  }`}
                  aria-hidden="true"
                >
                  <Icon className="h-5 w-5" strokeWidth={1.8} />
                </span>

                <div className={`pl-16 pt-1 lg:w-1/2 lg:pl-0 ${left ? 'lg:pr-14 lg:text-right' : 'lg:ml-auto lg:pl-14'}`}>
                  <p className="font-display text-[13px] font-bold uppercase tracking-[0.16em] text-brand-600">Step {String(item.n).padStart(2, '0')}</p>
                  <h3 className="mt-1 text-lg font-bold text-ink">{item.title}</h3>
                  <p className="mt-1 text-[15px] leading-relaxed text-muted">{item.text}</p>
                  {last && <p className="mt-2 inline-block rounded-full bg-gold-100 px-3 py-1 text-[13px] font-semibold text-gold-600">The result you read</p>}
                </div>
              </li>
            )
          })}
        </ol>

        <p className="mt-6 border-l-2 border-brand-300 pl-4 text-[15px] text-muted">
          Answers are generated from the passages retrieved from your documents. Always open the cited page when accuracy matters.
        </p>
        <div className="mt-8 text-center">
          <Button to="/register" size="lg">
            Start for Free
            <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  )
}
