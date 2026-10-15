import { AnimatedHeading } from '../common/AnimatedHeading'
// Dark rounded banner used at the top of the public pages (Features, How It Works, About).
export function PageBanner({ eyebrow, title, text }) {
  return (
    <section className="relative mx-auto overflow-hidden rounded-3xl bg-gradient-to-br from-plum-800 via-plum-900 to-plum-950 px-6 py-10 text-center text-white shadow-lift sm:py-12">
      <div className="pointer-events-none absolute -left-10 -top-16 h-56 w-56 animate-blob rounded-full bg-brand-600/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 right-0 h-56 w-56 animate-blob rounded-full bg-gold-400/15 blur-3xl [animation-delay:-6s]" />
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-20 invert" />
      <div className="relative mx-auto max-w-2xl">
        {eyebrow && <p className="text-[13px] font-bold uppercase tracking-[0.18em] text-gold-400">{eyebrow}</p>}
        <AnimatedHeading as="h1" text={title} tone="dark" underline align="center" className="mt-2 text-2xl font-bold sm:text-3xl" />
        {text && <p className="mt-2.5 text-sm text-plum-100">{text}</p>}
      </div>
    </section>
  )
}
