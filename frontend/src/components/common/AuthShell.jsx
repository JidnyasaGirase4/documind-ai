import { AnimatedHeading } from './AnimatedHeading'
import { Link } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { Logo } from './Logo'
import { ProductPreview } from '../marketing/ProductPreview'

const POINTS = ['Ask questions across all your PDFs', 'Every answer cites its document and page', 'Documents stay tied to your account']

// Split screen: a brand panel with the product preview, and an open (card-free) form side.
export function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* Brand panel (large screens) */}
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-brand-800 via-brand-700 to-plum-950 p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 animate-blob rounded-full bg-brand-400/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 right-0 h-96 w-96 animate-blob rounded-full bg-gold-400/20 blur-3xl [animation-delay:-6s]" />
        <div className="dot-grid pointer-events-none absolute inset-0 opacity-15 invert" />

        <Logo dark className="relative self-start" />

        <div className="relative">
          <AnimatedHeading text="Answers you can trace back to the page." highlight="trace" tone="dark" className="max-w-md font-display text-3xl font-bold leading-tight" />
          <div className="mt-8 max-w-md">
            <ProductPreview />
          </div>
        </div>

        <ul className="relative space-y-2">
          {POINTS.map((p) => (
            <li key={p} className="flex items-center gap-2.5 text-[15px] text-brand-100">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/15 text-gold-400 ring-1 ring-inset ring-white/20">
                <Check className="h-3 w-3" strokeWidth={3} aria-hidden="true" />
              </span>
              {p}
            </li>
          ))}
        </ul>
      </aside>

      {/* Form side */}
      <div className="relative flex flex-col px-5 py-6 sm:px-10">
        <div className="dot-grid pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(55%_45%_at_50%_40%,black,transparent)]" />

        <div className="relative flex items-center justify-between">
          <Logo className="lg:invisible" />
          <Link to="/" className="group inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[15px] font-semibold text-muted transition-colors hover:bg-stone-100 hover:text-ink">
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" aria-hidden="true" />
            <span className="min-[380px]:hidden">Home</span>
            <span className="hidden min-[380px]:inline">Back to home</span>
          </Link>
        </div>

        <div className="relative mx-auto flex w-full max-w-sm flex-1 animate-fade-in-up flex-col justify-center py-10">
          <span className="mb-4 h-1.5 w-10 rounded-full bg-gradient-to-r from-brand-600 to-gold-500" aria-hidden="true" />
          <AnimatedHeading as="h1" text={title} highlight={title.split(' ').slice(-1)[0]} className="font-display text-3xl font-extrabold leading-tight text-ink" />
          {subtitle && <p className="mt-2 text-sm text-muted">{subtitle}</p>}
          <div className="mt-7">{children}</div>
          <p className="mt-6 text-sm text-muted">{footer}</p>
        </div>
      </div>
    </div>
  )
}

// Summary shown above a form after a failed submit (role=alert so screen readers announce it).
export function FormErrorSummary({ errors, apiError }) {
  const items = [...Object.values(errors), ...(apiError ? [apiError] : [])]
  if (!items.length) return null
  return (
    <div role="alert" className="mb-5 animate-scale-in rounded-xl border border-danger/25 bg-danger-soft p-3.5 text-sm text-danger">
      <p className="font-semibold">{apiError && !Object.keys(errors).length ? apiError : 'Please fix the following:'}</p>
      {Object.keys(errors).length > 0 && (
        <ul className="mt-1 list-disc pl-5">
          {Object.values(errors).map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
