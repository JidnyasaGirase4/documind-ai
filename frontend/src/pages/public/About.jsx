import { AnimatedHeading } from '../../components/common/AnimatedHeading'
import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BookOpenCheck, Code2, FlaskConical, GraduationCap, Scale, ShieldCheck, Sparkles, Users } from 'lucide-react'
import { PageBanner } from '../../components/marketing/PageBanner'
import { Button } from '../../components/common/Button'
import { Reveal } from '../../components/common/Reveal'
import { USE_CASES } from '../../components/marketing/content'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'

const PRINCIPLES = [
  { icon: BookOpenCheck, title: 'Sources first', text: 'Answers should point back to the document and page they came from, so you can check them.' },
  { icon: ShieldCheck, title: 'Your documents only', text: 'Questions are answered from the PDFs in your own account, and the server checks ownership on every request.' },
  { icon: Scale, title: 'Honest about limits', text: 'If the documents do not contain enough evidence, the assistant should say so rather than guess.' },
]

const WHO = {
  Teams: { icon: Users, chip: 'from-brand-500 to-brand-700', tint: 'from-brand-50', bubble: 'from-brand-500 to-brand-700', example: 'What is our remote work policy?' },
  Students: { icon: GraduationCap, chip: 'from-amber-400 to-amber-600', tint: 'from-amber-50', bubble: 'from-amber-500 to-amber-700', example: 'Where does the reading define opportunity cost?' },
  Developers: { icon: Code2, chip: 'from-plum-700 to-plum-900', tint: 'from-stone-100', bubble: 'from-plum-700 to-plum-900', example: 'Which endpoint handles token refresh?' },
  Researchers: { icon: FlaskConical, chip: 'from-emerald-500 to-emerald-700', tint: 'from-emerald-50', bubble: 'from-emerald-500 to-emerald-700', example: 'How did each paper measure sample size?' },
}

const LIMITS = ['PDF files only.', 'PDFs must contain selectable text; scanned images are not processed.', 'AI answers can be wrong. Use the cited pages to verify anything important.']

function Eyebrow({ children }) {
  return <p className="text-[13px] font-bold uppercase tracking-[0.18em] text-brand-600">{children}</p>
}

// Illustration: a question, the document passage it is based on, and the cited answer.
// Sample content only; it is not live data.
function DocumentIllustration() {
  const bar = (w, dark) => <span className={`block h-2 rounded-full ${dark ? 'bg-stone-300' : 'bg-stone-200'}`} style={{ width: w }} />
  return (
    <figure className="relative mx-auto w-full max-w-md pb-14 pt-8" aria-hidden="true">
      <div className="absolute -inset-4 rounded-[2.5rem] bg-gradient-to-br from-brand-200/50 via-gold-100/50 to-transparent blur-2xl" />

      {/* Stacked pages behind */}
      <div className="absolute inset-x-8 top-12 bottom-14 rotate-[5deg] rounded-2xl border border-line bg-surface shadow-card" />
      <div className="absolute inset-x-6 top-10 bottom-12 -rotate-[3deg] rounded-2xl border border-line bg-stone-50 shadow-card" />

      {/* Main page */}
      <div className="relative rounded-2xl border border-line bg-surface p-5 shadow-pop">
        <div className="flex items-center gap-2 border-b border-line pb-3">
          <span className="rounded bg-danger px-1.5 py-0.5 text-[11px] font-extrabold tracking-wider text-white">PDF</span>
          <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ink">employee-handbook.pdf</span>
          <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[12px] font-bold text-brand-700">Page 14</span>
        </div>

        <div className="mt-4 space-y-2.5">
          {bar('46%', true)}
          {bar('94%')}
          {bar('82%')}
          <p className="relative rounded-lg bg-gradient-to-r from-brand-100 to-gold-100 px-3 py-2 text-[14px] font-medium leading-snug text-ink ring-1 ring-inset ring-brand-200">
            <span className="absolute -left-2.5 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-full bg-brand-600 text-[12px] font-bold text-white shadow-btn">1</span>
            Primary caregivers are entitled to sixteen weeks of paid leave.
          </p>
          {bar('90%')}
          {bar('58%')}
        </div>
      </div>

      {/* The question */}
      <div className="absolute -left-2 top-0 max-w-[13rem] -rotate-2 rounded-2xl rounded-bl-md bg-gradient-to-br from-brand-500 to-brand-700 px-3.5 py-2 text-[14px] font-semibold text-white shadow-lift sm:-left-6">
        How many weeks of parental leave?
      </div>

      {/* The cited answer */}
      <div className="absolute -right-1 bottom-0 w-60 animate-float-slow rounded-2xl border border-line bg-surface p-3 shadow-lift sm:-right-6">
        <div className="flex items-start gap-2">
          <span className="icon-tile mt-0.5 h-6 w-6 shrink-0 !rounded-full">
            <Sparkles className="h-3 w-3" />
          </span>
          <p className="text-[14px] font-medium leading-snug text-ink">Sixteen weeks of paid leave for primary caregivers.</p>
        </div>
        <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[12px] font-bold text-brand-700">employee-handbook.pdf · p. 14</p>
      </div>

      <figcaption className="sr-only">Illustrative example: a question, the passage it is based on, and the cited answer.</figcaption>
    </figure>
  )
}

export default function About() {
  useDocumentTitle('About')
  const [who, setWho] = useState(USE_CASES[0].title)
  const hoverTimer = useRef(0)
  const hoverTo = (t) => {
    window.clearTimeout(hoverTimer.current)
    hoverTimer.current = window.setTimeout(() => setWho(t), 90)
  }
  useEffect(() => () => window.clearTimeout(hoverTimer.current), [])

  const persona = USE_CASES.find((u) => u.title === who)
  const st = WHO[who]
  const PIcon = st.icon

  return (
    <div className="container-page py-10">
      <PageBanner
        eyebrow="About"
        title="About DocuMind AI"
        text="A document question-answering tool: upload PDFs, ask in plain language, and get answers that point back to the document and page they came from."
      />

      <div className="mx-auto max-w-5xl">
        {/* Purpose */}
        <section className="mt-12 grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.15fr_1fr]">
          <Reveal>
            <Eyebrow>Purpose</Eyebrow>
            <AnimatedHeading as="p" text="Long documents are slow to search by hand. We help you reach the relevant passage quickly and keep the original source one click away, so you can check the answer instead of taking it on trust." highlight="and keep the original source one click away," className="mt-3 font-display text-2xl font-bold leading-snug text-ink sm:text-[1.75rem]" />
          </Reveal>
          <Reveal delay={120} className="pb-6 lg:pb-0">
            <DocumentIllustration />
          </Reveal>
        </section>

        {/* Principles: medallions on a connecting line */}
        <section className="mt-20" aria-label="Principles">
          <Reveal className="mb-8 text-center">
            <Eyebrow>What we hold to</Eyebrow>
            <AnimatedHeading text="Three principles behind every answer" highlight="principles" underline align="center" className="mt-1 text-xl font-bold text-ink" />
          </Reveal>
          <ol className="relative grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-6">
            <span className="pointer-events-none absolute left-[16.6%] right-[16.6%] top-8 hidden border-t-2 border-dashed border-brand-200 md:block" aria-hidden="true" />
            {PRINCIPLES.map(({ icon: Icon, title, text }, i) => (
              <Reveal as="li" key={title} delay={i * 100} className="relative text-center">
                <span className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-glow ring-8 ring-canvas">
                  <Icon className="h-7 w-7" strokeWidth={1.7} aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-base font-bold text-ink">{title}</h3>
                <p className="mx-auto mt-1.5 max-w-[16rem] text-[15px] leading-relaxed text-muted">{text}</p>
              </Reveal>
            ))}
          </ol>
        </section>

        {/* Who it is for: choose a persona (hover or click) */}
        <section className="mt-20" aria-label="Who it is for">
          <Reveal className="mb-6">
            <Eyebrow>Who it is for</Eyebrow>
            <AnimatedHeading text="People who work with long documents" highlight="long documents" underline className="mt-1 text-xl font-bold text-ink" />
          </Reveal>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-[14rem_1fr]">
            <div role="tablist" aria-label="Who it is for" className="flex gap-2 overflow-x-auto md:flex-col md:overflow-visible">
              {USE_CASES.map((u) => {
                const s = WHO[u.title]
                const Icon = s.icon
                const on = who === u.title
                return (
                  <button
                    key={u.title}
                    role="tab"
                    id={`who-tab-${u.title}`}
                    aria-selected={on}
                    aria-controls="who-panel"
                    type="button"
                    onClick={() => setWho(u.title)}
                    onMouseEnter={() => hoverTo(u.title)}
                    onMouseLeave={() => window.clearTimeout(hoverTimer.current)}
                    className={`flex shrink-0 items-center gap-3 rounded-xl px-3.5 py-3 text-left text-sm font-semibold transition-all duration-200 ${
                      on ? 'bg-surface text-ink shadow-lift ring-1 ring-brand-200' : 'text-muted hover:bg-surface/70 hover:text-ink'
                    }`}
                  >
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
                        on ? `bg-gradient-to-br text-white shadow-btn ${s.chip}` : 'bg-stone-100 text-muted'
                      }`}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    {u.title}
                  </button>
                )
              })}
            </div>

            <div
              id="who-panel"
              role="tabpanel"
              aria-labelledby={`who-tab-${who}`}
              className={`relative min-h-[15rem] overflow-hidden rounded-3xl border border-line bg-gradient-to-br ${st.tint} to-white p-6 shadow-card sm:p-8`}
            >
              <div key={who} className="animate-fade-in-up">
                <span className={`flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-lift ring-4 ring-white/70 ${st.chip}`}>
                  <PIcon className="h-7 w-7" strokeWidth={1.7} aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-xl font-bold text-ink">{persona.title}</h3>
                <p className="mt-1.5 max-w-lg text-sm leading-relaxed text-muted">{persona.text}</p>
                <p className="mt-6 text-[12px] font-bold uppercase tracking-[0.14em] text-muted">Example question</p>
                <p className={`mt-2 w-fit max-w-full rounded-2xl rounded-bl-md bg-gradient-to-br px-4 py-2.5 text-sm font-medium text-white shadow-card ${st.bubble}`}>{st.example}</p>
              </div>
            </div>
          </div>
        </section>

        {/* Limits */}
        <Reveal as="section" className="mt-20" aria-label="Current limits">
          <div className="border-l-4 border-amber-400 bg-gradient-to-r from-amber-50 to-transparent py-4 pl-5 pr-4">
            <h2 className="text-base font-bold text-ink">Current limits</h2>
            <ul className="mt-2 space-y-1.5">
              {LIMITS.map((l) => (
                <li key={l} className="flex items-start gap-2 text-[15px] text-ink">
                  <span className="mt-2 h-1 w-3 shrink-0 rounded-full bg-amber-500" aria-hidden="true" />
                  {l}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>

        <div className="mt-10">
          <Button to="/register" size="lg">
            Create your account
            <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  )
}
