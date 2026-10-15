import { Link } from 'react-router-dom'
import { useId } from 'react'
import { cx } from '../../utils/format'

// Wordmark: a document with a sparkle, drawn inline (no third-party brand assets).
export function LogoMark({ className = 'h-9 w-9' }) {
  const gid = useId()
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#c9506f" />
          <stop offset="1" stopColor="#741733" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill={`url(#${gid})`} />
      <path d="M10 7h8l5 5v13a1 1 0 0 1-1 1H10a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z" fill="#fff" />
      <path d="M18 7v4a1 1 0 0 0 1 1h4z" fill="#edbbc8" />
      <path d="M12 16h4M12 20h3" stroke="#dd8aa0" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M21 16l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9z" fill="#8f1d3f" />
    </svg>
  )
}

export function Logo({ to = '/', dark = false, className }) {
  return (
    <Link to={to} className={cx('group inline-flex items-center gap-2.5 rounded-lg', className)} aria-label="DocuMind AI home">
      <LogoMark className="h-9 w-9 shrink-0 transition-transform duration-300 group-hover:rotate-[-6deg] group-hover:scale-105" />
      <span className={cx('whitespace-nowrap font-display text-lg font-bold tracking-tight', dark ? 'text-white' : 'text-ink')}>
        DocuMind<span className={dark ? 'text-brand-300' : 'text-brand-600'}> AI</span>
      </span>
    </Link>
  )
}
