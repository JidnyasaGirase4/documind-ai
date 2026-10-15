import { AnimatedHeading } from '../../components/common/AnimatedHeading'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowRight, FileText, Search } from 'lucide-react'
import { PageBanner } from '../../components/marketing/PageBanner'
import { Button } from '../../components/common/Button'
import { ChatMessage } from '../../components/chat/ChatMessage'
import { DocumentStatusBadge } from '../../components/documents/DocumentStatusBadge'
import { FEATURES } from '../../components/marketing/content'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'

// Illustrative examples built from the real UI components (not live data).
const VISUALS = {
  'PDF knowledge search': (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-xl bg-surface px-3.5 py-3 text-sm text-ink shadow-card ring-1 ring-line">
        <Search className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
        What does the contract say about termination?
      </div>
      <p className="px-1 text-xs text-muted">Searches the text of every PDF in your library and finds the passages that match.</p>
    </div>
  ),
  'Cited answers': (
    <ChatMessage
      message={{
        role: 'assistant',
        content: 'Either party may terminate with 30 days written notice.',
        citations: [{ documentName: 'service-agreement.pdf', page: 6, excerpt: 'Either party may terminate this agreement by giving thirty (30) days written notice…' }],
      }}
    />
  ),
  'Document library': (
    <ul className="space-y-2">
      {[
        ['quarterly-report.pdf', 'ready'],
        ['onboarding-guide.pdf', 'processing'],
        ['scanned-contract.pdf', 'failed'],
      ].map(([name, status]) => (
        <li key={name} className="flex items-center gap-2.5 rounded-xl bg-surface p-3 text-sm shadow-card ring-1 ring-line">
          <FileText className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">{name}</span>
          <DocumentStatusBadge status={status} />
        </li>
      ))}
    </ul>
  ),
  'Conversation history': (
    <ul className="space-y-2 text-sm">
      {[
        ['Leave policy questions', 'Today'],
        ['Warranty terms', 'Yesterday'],
        ['API rate limits', 'Last week'],
      ].map(([t, when]) => (
        <li key={t} className="flex items-center justify-between rounded-xl bg-surface px-3.5 py-3 shadow-card ring-1 ring-line">
          <span>{t}</span>
          <span className="text-xs text-muted">{when}</span>
        </li>
      ))}
    </ul>
  ),
  'Secure document access': (
    <div className="rounded-xl bg-surface p-4 text-sm shadow-card ring-1 ring-line">
      <p className="font-semibold text-ink">Sign in required</p>
      <p className="mt-1 text-muted">Document and conversation requests are checked against your account on the server.</p>
    </div>
  ),
  'Usage insights': (
    <div className="rounded-xl bg-surface p-4 shadow-card ring-1 ring-line">
      <p className="text-xs font-semibold text-muted">Uploads over time</p>
      <div className="mt-3 flex h-28 items-end gap-2" role="img" aria-label="Example bar chart">
        {[30, 55, 40, 75, 60, 90, 70].map((h, i) => (
          <div key={i} className="flex-1 rounded-t bg-gradient-to-t from-brand-600 to-brand-300" style={{ height: `${h}%` }} />
        ))}
      </div>
    </div>
  ),
}

const STICKY_TOP = 80 // px below the viewport top where the showcase sticks
const N = FEATURES.length

export default function Features() {
  useDocumentTitle('Features')
  const [active, setActive] = useState(0)
  const wrapRef = useRef(null)
  const tabRefs = useRef([])
  const current = FEATURES[active]

  // Pixels of scrolling per feature (half a screen).
  const stepPx = () => Math.round(window.innerHeight * 0.5)

  // The showcase is sticky inside a tall wrapper; scroll position inside the wrapper picks the feature.
  useEffect(() => {
    let raf = 0
    const update = () => {
      raf = 0
      const el = wrapRef.current
      if (!el) return
      const scrolled = STICKY_TOP - el.getBoundingClientRect().top
      const idx = Math.min(N - 1, Math.max(0, Math.round(scrolled / stepPx())))
      setActive((prev) => (prev === idx ? prev : idx))
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

  // Keep the active tab visible inside the horizontally scrolling tab strip on small screens.
  useEffect(() => {
    tabRefs.current[active]?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
  }, [active])

  const goTo = useCallback((i) => {
    const el = wrapRef.current
    if (!el) return
    const absTop = el.getBoundingClientRect().top + window.scrollY
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: absTop - STICKY_TOP + i * stepPx(), behavior: reduce ? 'auto' : 'smooth' })
    setActive(i)
  }, [])

  // Hovering a tab previews that feature (no page scroll). A short delay avoids flicker
  // while the pointer moves across the list; scrolling takes over again afterwards.
  const hoverTimer = useRef(0)
  const hoverTo = (i) => {
    window.clearTimeout(hoverTimer.current)
    hoverTimer.current = window.setTimeout(() => setActive(i), 90)
  }
  const cancelHover = () => window.clearTimeout(hoverTimer.current)
  useEffect(() => () => window.clearTimeout(hoverTimer.current), [])

  const onKeyDown = (e) => {
    const horizontal = window.matchMedia?.('(min-width: 1024px)').matches === false
    const next = horizontal ? 'ArrowRight' : 'ArrowDown'
    const prev = horizontal ? 'ArrowLeft' : 'ArrowUp'
    let i = null
    if (e.key === next) i = (active + 1) % N
    if (e.key === prev) i = (active - 1 + N) % N
    if (e.key === 'Home') i = 0
    if (e.key === 'End') i = N - 1
    if (i !== null) {
      e.preventDefault()
      goTo(i)
      tabRefs.current[i]?.focus({ preventScroll: true })
    }
  }

  return (
    <div className="container-page py-10">
      <PageBanner eyebrow="Features" title="What DocuMind AI does" text="Scroll to explore each capability, or pick one to jump straight to it." />

      {/* Tall wrapper: the sticky showcase stays in view while you scroll through the spacer */}
      <div ref={wrapRef} className="relative mt-8">
        <div className="sticky z-10 grid grid-cols-1 gap-5 bg-canvas/0 lg:grid-cols-[19rem_1fr] lg:gap-8" style={{ top: STICKY_TOP }}>
          <div>
            <div
              role="tablist"
              aria-label="Features"
              onKeyDown={onKeyDown}
              className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 lg:mx-0 lg:flex-col lg:gap-1.5 lg:overflow-visible lg:px-0 lg:pb-0"
            >
              {FEATURES.map(({ icon: Icon, title }, i) => {
                const on = i === active
                return (
                  <button
                    key={title}
                    ref={(el) => (tabRefs.current[i] = el)}
                    role="tab"
                    id={`feature-tab-${i}`}
                    aria-selected={on}
                    aria-controls="feature-panel"
                    tabIndex={on ? 0 : -1}
                    type="button"
                    onClick={() => goTo(i)}
                    onMouseEnter={() => hoverTo(i)}
                    onMouseLeave={cancelHover}
                    className={`group relative flex shrink-0 items-center gap-3 rounded-xl px-3.5 py-3 text-left text-[15px] font-semibold transition-all duration-300 ${
                      on ? 'bg-surface text-ink shadow-lift ring-1 ring-brand-200' : 'text-muted hover:bg-surface/70 hover:text-ink'
                    }`}
                  >
                    {on && <span className="absolute inset-y-2 left-0 hidden w-1 rounded-r-full bg-brand-600 lg:block" aria-hidden="true" />}
                    <span
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors ${
                        on ? 'bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-btn' : 'bg-stone-100 text-muted group-hover:bg-brand-50 group-hover:text-brand-700'
                      }`}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <span className="whitespace-nowrap lg:whitespace-normal">{title}</span>
                    <span className="ml-auto hidden font-display text-[13px] font-bold text-muted/70 lg:block" aria-hidden="true">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                  </button>
                )
              })}
            </div>
            <p className="mt-3 hidden items-center gap-1.5 px-1 text-xs text-muted lg:flex">
              <ArrowDown className="h-3.5 w-3.5 animate-bounce" aria-hidden="true" />
              Keep scrolling to see the next feature
            </p>
          </div>

          <div
            id="feature-panel"
            role="tabpanel"
            aria-labelledby={`feature-tab-${active}`}
            aria-live="polite"
            className="relative min-h-[28rem] min-w-0 overflow-hidden rounded-3xl bg-gradient-to-br from-plum-800 via-plum-900 to-plum-950 p-5 text-white shadow-lift sm:p-8"
          >
            <div className="pointer-events-none absolute -left-12 -top-16 h-56 w-56 animate-blob rounded-full bg-brand-600/40 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 right-0 h-56 w-56 animate-blob rounded-full bg-gold-400/15 blur-3xl [animation-delay:-6s]" />
            <div className="dot-grid pointer-events-none absolute inset-0 opacity-15 invert" />

            <div key={active} className="relative animate-fade-in-up">
              <p className="text-[13px] font-bold uppercase tracking-[0.18em] text-gold-400">
                Feature {String(active + 1).padStart(2, '0')} / {String(N).padStart(2, '0')}
              </p>
              <AnimatedHeading key={active} text={current.title} highlight={current.title.split(' ').slice(-1)[0]} tone="dark" className="mt-2 text-2xl font-bold" />
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-plum-100">{current.text}</p>

              <div className="mt-6 overflow-hidden rounded-2xl bg-canvas shadow-pop ring-1 ring-white/10">
                <div className="flex items-center gap-1.5 border-b border-line bg-surface px-4 py-2.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-brand-300" aria-hidden="true" />
                  <span className="h-2.5 w-2.5 rounded-full bg-gold-400" aria-hidden="true" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" aria-hidden="true" />
                  <span className="ml-3 truncate text-[13px] font-medium text-muted">DocuMind AI · {current.title}</span>
                </div>
                <div className="min-w-0 p-5 text-ink">{VISUALS[current.title]}</div>
              </div>
              <p className="mt-3 text-[13px] text-plum-200/80">Illustrative example — not live data</p>
            </div>

            {/* Scroll progress */}
            <div className="absolute inset-x-0 bottom-0 h-1 bg-white/10" aria-hidden="true">
              <div className="h-full bg-gradient-to-r from-brand-400 to-gold-400 transition-all duration-500" style={{ width: `${((active + 1) / N) * 100}%` }} />
            </div>
          </div>
        </div>

        {/* Scroll distance that drives the switching */}
        <div aria-hidden="true" style={{ height: `${(N - 1) * 50}vh` }} />
      </div>

      <div className="mt-8 text-center">
        <Button to="/register" size="lg">
          Start for Free
          <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
