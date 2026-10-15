import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'

export function Pagination({ page, pages, total, pageSize, onChange, noun = 'items' }) {
  if (!total || pages <= 1) return total ? <p className="px-1 pt-3 text-sm text-muted">{total} {noun}</p> : null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  return (
    <nav aria-label="Pagination" className="flex flex-col items-center justify-between gap-3 pt-4 sm:flex-row">
      <p className="text-sm text-muted">
        Showing {from}–{to} of {total} {noun}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Previous
        </Button>
        <span className="text-sm text-muted" aria-current="page">
          Page {page} of {pages}
        </span>
        <Button variant="secondary" size="sm" onClick={() => onChange(page + 1)} disabled={page >= pages} aria-label="Next page">
          Next
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  )
}
