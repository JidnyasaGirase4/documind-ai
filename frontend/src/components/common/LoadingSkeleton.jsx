import { cx } from '../../utils/format'

export function Skeleton({ className }) {
  return <div className={cx('skeleton', className)} aria-hidden="true" />
}

// Stack of row-shaped placeholders for lists and tables.
export function ListSkeleton({ rows = 4, className }) {
  return (
    <div className={cx('space-y-3', className)} role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-card border border-line bg-surface p-4">
          <Skeleton className="h-10 w-10 shrink-0 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  )
}

export function ChartSkeleton({ className }) {
  return <Skeleton className={cx('h-64 w-full', className)} />
}
