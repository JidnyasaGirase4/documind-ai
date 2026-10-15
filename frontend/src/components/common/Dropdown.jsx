import { useEffect, useId, useRef, useState } from 'react'
import { cx } from '../../utils/format'

// Small action menu. `trigger` receives props to spread onto its button.
// items: [{ label, icon, onClick, danger, disabled, to }]
export function Dropdown({ trigger, items, align = 'right', label }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return undefined
    const onDoc = (e) => {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false)
        rootRef.current?.querySelector('button')?.focus()
      }
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    rootRef.current?.querySelector('[role="menuitem"]:not([disabled])')?.focus()
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const onMenuKey = (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const els = [...rootRef.current.querySelectorAll('[role="menuitem"]:not([disabled])')]
    const i = els.indexOf(document.activeElement)
    const next = e.key === 'ArrowDown' ? (i + 1) % els.length : (i - 1 + els.length) % els.length
    els[next]?.focus()
  }

  return (
    <div className="relative" ref={rootRef}>
      {trigger({
        'aria-haspopup': 'menu',
        'aria-expanded': open,
        'aria-controls': open ? menuId : undefined,
        'aria-label': label,
        onClick: () => setOpen((o) => !o),
      })}
      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKey}
          className={cx(
            'absolute z-30 mt-2 min-w-[12rem] animate-scale-in rounded-xl border border-line bg-surface p-1 shadow-pop',
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {items.map((it) => {
            const Icon = it.icon
            return (
              <button
                key={it.label}
                role="menuitem"
                type="button"
                disabled={it.disabled}
                onClick={() => {
                  setOpen(false)
                  it.onClick?.()
                }}
                className={cx(
                  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors disabled:opacity-50',
                  it.danger ? 'text-danger hover:bg-danger-soft' : 'text-ink hover:bg-stone-50',
                )}
              >
                {Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
                {it.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
