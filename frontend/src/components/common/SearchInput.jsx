import { useId } from 'react'
import { Search, X } from 'lucide-react'
import { cx } from '../../utils/format'

export function SearchInput({ value, onChange, placeholder = 'Search', label = 'Search', className }) {
  const id = useId()
  return (
    <div className={cx('relative', className)} role="search">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
      <input
        id={id}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-control border border-line bg-surface pl-9 pr-9 text-sm text-ink placeholder:text-stone-400 [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
