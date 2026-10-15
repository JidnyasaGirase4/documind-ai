import { AnimatedHeading } from './AnimatedHeading'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

export function PageHeader({ title, description, actions, breadcrumbs }) {
  return (
    <div className="mb-5">
      {breadcrumbs && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex flex-wrap items-center gap-1 text-sm text-muted">
            {breadcrumbs.map((b, i) => (
              <li key={b.label} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />}
                {b.to ? (
                  <Link to={b.to} className="rounded hover:text-ink hover:underline">
                    {b.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="max-w-[16rem] truncate text-ink">
                    {b.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-1 h-7 w-1.5 shrink-0 rounded-full bg-gradient-to-b from-brand-500 to-gold-500" aria-hidden="true" />
          <div className="min-w-0">
            <AnimatedHeading as="h1" text={title} className="break-words text-xl font-bold text-ink sm:text-2xl" />
            {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
          </div>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
