import { forwardRef } from 'react'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { cx } from '../../utils/format'

const VARIANTS = {
  primary:
    'bg-gradient-to-b from-brand-500 to-brand-600 text-white shadow-btn hover:from-brand-600 hover:to-brand-700 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:from-brand-300 disabled:to-brand-300 disabled:shadow-none disabled:translate-y-0',
  secondary:
    'border border-line bg-surface text-ink shadow-card hover:border-stone-300 hover:bg-stone-50 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:text-muted disabled:translate-y-0',
  ghost: 'text-ink hover:bg-stone-100 active:scale-[0.98] disabled:text-muted',
  danger: 'bg-danger text-white shadow-card hover:bg-rose-800 active:scale-[0.98] disabled:bg-danger/60',
  dangerGhost: 'text-danger hover:bg-danger-soft active:scale-[0.98]',
  dark: 'bg-plum-900 text-white shadow-card hover:bg-plum-700 hover:-translate-y-0.5 active:scale-[0.98]',
  glass: 'border border-white/20 bg-white/10 text-white backdrop-blur hover:-translate-y-0.5 hover:bg-white/20 active:scale-[0.98]',
  light: 'bg-white text-ink shadow-card hover:bg-brand-50 hover:-translate-y-0.5 active:scale-[0.98]',
}

const SIZES = {
  sm: 'h-8 px-3 text-[15px] gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-sm gap-2',
  icon: 'h-8 w-8 justify-center',
}

// Renders a <button>, or a router <Link> when `to` is provided.
export const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', loading = false, disabled, to, className, children, type = 'button', ...rest },
  ref,
) {
  const classes = cx(
    'group/btn inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-control font-semibold transition-all duration-200 disabled:cursor-not-allowed',
    VARIANTS[variant],
    SIZES[size],
    className,
  )
  if (to) {
    return (
      <Link ref={ref} to={to} className={classes} {...rest}>
        {children}
      </Link>
    )
  }
  return (
    <button ref={ref} type={type} disabled={disabled || loading} aria-busy={loading || undefined} className={classes} {...rest}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
})
