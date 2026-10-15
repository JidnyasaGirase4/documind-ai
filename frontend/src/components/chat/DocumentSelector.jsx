import { useEffect, useRef, useState } from 'react'
import { ChevronDown, FileText } from 'lucide-react'

// Choose which ready documents a question is scoped to. Empty selection = all documents.
export function DocumentSelector({ documents, selected, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onDoc = (e) => !rootRef.current?.contains(e.target) && setOpen(false)
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const label =
    selected.length === 0
      ? 'All my documents'
      : selected.length === 1
        ? (documents.find((d) => d.id === selected[0])?.filename ?? '1 document')
        : `${selected.length} documents`

  const toggle = (id) => onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id])

  return (
    <div className="relative w-full sm:w-auto" ref={rootRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="true"
        aria-expanded={open}
        className="flex h-9 w-full items-center sm:w-auto sm:max-w-[16rem] gap-2 rounded-control border border-line bg-surface px-3 text-sm text-ink hover:bg-stone-50 disabled:opacity-60"
      >
        <FileText className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
        <span className="truncate">
          <span className="sr-only">Searching in: </span>
          {label}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
      </button>
      {open && (
        <div className="absolute left-0 z-30 mt-1 w-72 max-w-[85vw] rounded-card border border-line bg-surface p-2 shadow-pop">
          <fieldset>
            <legend className="sr-only">Documents to search</legend>
            <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-stone-50">
              <input type="checkbox" checked={selected.length === 0} onChange={() => onChange([])} className="h-4 w-4 accent-brand-600" />
              <span className="font-medium">All my documents</span>
            </label>
            <div className="my-1 border-t border-line" />
            <div className="max-h-60 overflow-y-auto">
              {documents.length === 0 && <p className="px-2 py-2 text-sm text-muted">No ready documents.</p>}
              {documents.map((d) => (
                <label key={d.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-stone-50">
                  <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggle(d.id)} className="h-4 w-4 accent-brand-600" />
                  <span className="truncate">{d.filename}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      )}
    </div>
  )
}
