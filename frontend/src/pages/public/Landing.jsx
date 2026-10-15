import { AnimatedHeading } from '../../components/common/AnimatedHeading'
import { ArrowRight, BarChart3, BookOpenCheck, Check, Code2, FileSearch, FileText, FlaskConical, GraduationCap, History, Library, Lock, Search, ShieldCheck, Users } from 'lucide-react'
import { Button } from '../../components/common/Button'
import { Reveal } from '../../components/common/Reveal'
import { ProductPreview } from '../../components/marketing/ProductPreview'
import { FAQ } from '../../components/marketing/FAQ'
import { FAQS, STEPS, USE_CASES } from '../../components/marketing/content'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'

const TRUST = ['Answers cite document and page', 'Built around your own PDFs', 'Open the source to verify', 'PDF files only for now']

const USE_CASE_STYLE = {
  Teams: { icon: Users, tint: 'from-brand-50', chip: 'from-brand-500 to-brand-700', glow: 'bg-brand-200/60', bubble: 'from-brand-500 to-brand-700', example: 'What is our remote work policy?' },
  Students: { icon: GraduationCap, tint: 'from-amber-50', chip: 'from-amber-400 to-amber-600', glow: 'bg-amber-200/70', bubble: 'from-amber-500 to-amber-700', example: 'Where does the reading define opportunity cost?' },
  Developers: { icon: Code2, tint: 'from-stone-100', chip: 'from-plum-700 to-plum-900', glow: 'bg-stone-300/60', bubble: 'from-plum-700 to-plum-900', example: 'Which endpoint handles token refresh?' },
  Researchers: { icon: FlaskConical, tint: 'from-emerald-50', chip: 'from-emerald-500 to-emerald-700', glow: 'bg-emerald-200/60', bubble: 'from-emerald-500 to-emerald-700', example: 'How did each paper measure sample size?' },
}

function SectionHeading({ eyebrow, title, highlight, text }) {
  return (
    <Reveal className="mx-auto mb-10 max-w-2xl text-center">
      <p className="text-[13px] font-bold uppercase tracking-[0.18em] text-brand-600">{eyebrow}</p>
      <AnimatedHeading text={title} highlight={highlight} underline align="center" className="mt-2 text-2xl font-bold text-ink sm:text-3xl" />
      {text && <p className="mt-2.5 text-sm text-muted">{text}</p>}
    </Reveal>
  )
}

function FeatureCard({ icon: Icon, title, text, delay = 0, children }) {
  return (
    <Reveal delay={delay} className="h-full">
      <article className="group relative flex h-full flex-col overflow-hidden rounded-card border border-line bg-surface p-5 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-lift">
        <span
          className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-brand-100/70 transition-transform duration-500 group-hover:scale-[1.8]"
          aria-hidden="true"
        />
        <div className="relative flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-btn transition-transform duration-300 group-hover:-rotate-3 group-hover:scale-105">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <h3 className="text-base font-bold text-ink">{title}</h3>
        </div>
        <p className="relative mt-3 text-[15px] leading-relaxed text-muted">{text}</p>
        <div className="relative mt-auto pt-4">
          <div className="flex min-h-[4.5rem] flex-col justify-center gap-2 rounded-xl border border-line bg-canvas p-3 text-xs" aria-hidden="true">
            {children}
          </div>
        </div>
      </article>
    </Reveal>
  )
}

function Row({ icon: Icon = FileText, children, tag }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-surface px-2.5 py-1.5 shadow-card">
      <Icon className="h-3.5 w-3.5 shrink-0 text-brand-600" />
      <span className="min-w-0 flex-1 truncate font-medium text-ink">{children}</span>
      {tag}
    </div>
  )
}

export default function Landing() {
  useDocumentTitle()
  return (
    <>
      {/* Hero */}
      <section className="container-page pt-3">
        <div className="relative overflow-hidden rounded-[1.75rem] bg-gradient-to-br from-plum-800 via-plum-900 to-plum-950 px-5 py-10 text-white sm:px-10 lg:px-14 lg:py-16">
          <div className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 animate-blob rounded-full bg-brand-600/45 blur-3xl" />
          <div className="pointer-events-none absolute -right-20 bottom-0 h-72 w-72 animate-blob rounded-full bg-gold-400/20 blur-3xl [animation-delay:-5s]" />
          <div className="dot-grid pointer-events-none absolute inset-0 opacity-20 invert" />

          <div className="relative grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
            <div>
              <p className="inline-flex animate-fade-in-up items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[13px] font-bold uppercase tracking-[0.12em] text-plum-100">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold-400" aria-hidden="true" />
                AI-POWERED DOCUMENT INTELLIGENCE
              </p>
              <AnimatedHeading as="h1" text="Your documents. Your knowledge. One AI assistant." highlight="One AI assistant." tone="dark" delay={100} className="mt-5 text-3xl font-bold leading-[1.12] sm:text-4xl lg:text-[2.6rem]" />
              <p className="mt-4 max-w-lg animate-fade-in-up text-base text-plum-100 [animation-delay:200ms]">
                Find answers in your PDFs, policies, manuals, and reports—with source references you can verify.
              </p>
              <div className="mt-7 flex animate-fade-in-up flex-col gap-3 [animation-delay:300ms] sm:flex-row">
                <Button to="/register" size="lg">
                  Start for Free
                  <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
                </Button>
                <Button to="/how-it-works" size="lg" variant="glass">
                  See How It Works
                </Button>
              </div>
            </div>

            <div className="animate-fade-in-up px-1 [animation-delay:250ms] sm:px-4 lg:px-2">
              <ProductPreview />
            </div>
          </div>
        </div>
      </section>

      {/* Highlights: an open ruled strip, no boxes */}
      <section aria-label="Highlights" className="container-page mt-8">
        <ul className="grid grid-cols-1 gap-x-6 gap-y-3 border-y border-line py-4 sm:grid-cols-2 lg:grid-cols-4">
          {TRUST.map((t) => (
            <li key={t} className="flex items-center gap-2.5 text-[15px] font-semibold text-ink">
              <Check className="h-4 w-4 shrink-0 text-brand-600" strokeWidth={2.5} aria-hidden="true" />
              {t}
            </li>
          ))}
        </ul>
      </section>

      {/* Features */}
      <section className="container-page py-14 lg:py-20">
        <SectionHeading eyebrow="Features" title="Everything you need to work with your PDFs" highlight="PDFs" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FeatureCard icon={FileSearch} title="PDF knowledge search" text="Ask in plain language. DocuMind AI looks through the text of your PDFs for the passages that matter.">
            <Row icon={Search}>What does the contract say about termination?</Row>
          </FeatureCard>
          <FeatureCard icon={BookOpenCheck} title="Cited answers" text="Every answer lists the document and page it is based on, so you can check the source yourself." delay={80}>
            <Row tag={<span className="shrink-0 rounded bg-brand-50 px-1.5 py-0.5 font-semibold text-brand-700">Page 14</span>}>employee-handbook.pdf</Row>
            <p className="truncate px-1 italic text-muted">“Primary caregivers are entitled to sixteen weeks…”</p>
          </FeatureCard>
          <FeatureCard icon={Library} title="Document library" text="Upload, search, filter and manage PDFs, and watch each file's processing status." delay={160}>
            <Row tag={<span className="shrink-0 rounded-full bg-success-soft px-2 py-0.5 font-semibold text-success">Ready</span>}>quarterly-report.pdf</Row>
            <Row tag={<span className="shrink-0 rounded-full bg-warning-soft px-2 py-0.5 font-semibold text-warning">Processing</span>}>onboarding-guide.pdf</Row>
          </FeatureCard>
          <FeatureCard icon={History} title="Conversation history" text="Pick up where you left off. Conversations are saved, searchable, renamable and deletable.">
            <Row icon={History}>Leave policy questions</Row>
            <Row icon={History}>Warranty terms</Row>
          </FeatureCard>
          <FeatureCard icon={ShieldCheck} title="Secure document access" text="You sign in to your own account, and the server checks ownership on every request." delay={80}>
            <Row icon={Lock}>Visible only to your account</Row>
          </FeatureCard>
          <FeatureCard icon={BarChart3} title="Usage insights" text="See how many documents you have uploaded, how they were processed, and how often you ask questions." delay={160}>
            <div className="flex h-12 items-end gap-1.5" role="img">
              {[30, 55, 40, 75, 60, 90, 70].map((h, i) => (
                <div key={i} className="flex-1 rounded-t bg-gradient-to-t from-brand-600 to-brand-300" style={{ height: `${h}%` }} />
              ))}
            </div>
          </FeatureCard>
        </div>
      </section>

      {/* Steps */}
      <section className="border-y border-line bg-surface py-14 lg:py-20">
        <div className="container-page">
          <SectionHeading eyebrow="How it works" title="Upload, ask, verify" highlight="verify" />
          <ol className="relative grid grid-cols-1 gap-8 md:grid-cols-3">
            <div className="pointer-events-none absolute left-[16%] right-[16%] top-5 hidden border-t-2 border-dashed border-brand-200 md:block" aria-hidden="true" />
            {STEPS.map((s, i) => (
              <Reveal as="li" key={s.title} delay={i * 110} className="relative text-center">
                <span className="relative mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 font-display text-sm font-bold text-white shadow-btn ring-4 ring-surface">
                  {i + 1}
                </span>
                <h3 className="mt-3 text-base font-bold text-ink">{s.title}</h3>
                <p className="mx-auto mt-1 max-w-[16rem] text-[15px] text-muted">{s.text}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* Use cases */}
      <section className="container-page py-14 lg:py-20">
        <SectionHeading eyebrow="Use cases" title="Made for people who work with documents" highlight="documents" />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {USE_CASES.map((u, i) => {
            const st = USE_CASE_STYLE[u.title]
            const Icon = st.icon
            return (
              <Reveal key={u.title} delay={i * 90} className="h-full">
                <article
                  className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-gradient-to-b ${st.tint} to-white p-6 shadow-card transition-all duration-300 hover:-translate-y-1.5 hover:shadow-pop`}
                >
                  <span
                    className={`pointer-events-none absolute -right-12 -top-12 h-36 w-36 rounded-full ${st.glow} blur-2xl transition-transform duration-500 group-hover:scale-125`}
                    aria-hidden="true"
                  />
                  <span
                    className="pointer-events-none absolute right-5 top-4 font-display text-4xl font-extrabold leading-none text-ink/[0.06]"
                    aria-hidden="true"
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>

                  <span
                    className={`relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-lift ring-4 ring-white/70 transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-105 ${st.chip}`}
                  >
                    <Icon className="h-7 w-7" strokeWidth={1.7} aria-hidden="true" />
                  </span>
                  <h3 className="relative mt-5 text-lg font-bold text-ink">{u.title}</h3>
                  <p className="relative mt-1.5 text-[15px] leading-relaxed text-muted">{u.text}</p>

                  <div className="relative mt-auto pt-6">
                    <p className="mb-2 text-[12px] font-bold uppercase tracking-[0.14em] text-muted">Example question</p>
                    <p
                      className={`ml-auto w-fit max-w-full rounded-2xl rounded-br-md bg-gradient-to-br px-3.5 py-2.5 text-[15px] font-medium text-white shadow-card ${st.bubble}`}
                    >
                      {st.example}
                    </p>
                  </div>
                </article>
              </Reveal>
            )
          })}
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-line bg-surface py-14 lg:py-20">
        <div className="container-page grid grid-cols-1 gap-8 lg:grid-cols-[1fr_1.7fr] lg:gap-14">
          <Reveal className="lg:sticky lg:top-24 lg:self-start">
            <p className="text-[13px] font-bold uppercase tracking-[0.18em] text-brand-600">FAQ</p>
            <AnimatedHeading text="Frequently asked questions" highlight="questions" underline className="mt-2 text-2xl font-bold text-ink sm:text-3xl" />
            <p className="mt-2.5 max-w-sm text-sm text-muted">Short answers about uploads, processing, and how answers are sourced from your documents.</p>
            <Button to="/how-it-works" variant="secondary" className="mt-5">
              See how it works
              <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
            </Button>
          </Reveal>
          <Reveal delay={80}>
            <FAQ items={FAQS} />
          </Reveal>
        </div>
      </section>

      {/* Final CTA */}
      <section className="container-page py-14 lg:py-20">
        <Reveal className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-800 to-plum-950 px-6 py-12 text-center shadow-lift sm:px-10">
          <div className="pointer-events-none absolute -left-10 -top-10 h-56 w-56 animate-blob rounded-full bg-gold-400/20 blur-3xl" />
          <div className="dot-grid pointer-events-none absolute inset-0 opacity-20 invert" />
          <div className="relative">
            <AnimatedHeading text="Ready to ask your documents a question?" highlight="a question?" tone="dark" underline align="center" className="text-2xl font-bold text-white sm:text-3xl" />
            <p className="mx-auto mt-3 max-w-lg text-sm text-brand-100">Create an account, upload a PDF, and see the answer with its source.</p>
            <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
              <Button to="/register" size="lg" variant="light">
                Start for Free
                <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
              </Button>
              <Button to="/features" size="lg" variant="glass">
                Explore features
              </Button>
            </div>
          </div>
        </Reveal>
      </section>
    </>
  )
}
