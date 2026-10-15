import { useId } from 'react'

// CSS-only tooltip for icon-only controls. The child should still carry its own
// aria-label; the tooltip text is exposed via aria-describedby as a supplement.
export function Tooltip({ text, children, side = 'bottom' }) {
  const id = useId()
  const pos = side === 'right' ? 'left-full top-1/2 ml-2 -translate-y-1/2' : 'left-1/2 top-full mt-1.5 -translate-x-1/2'
  return (
    <span className="group relative inline-flex" aria-describedby={id}>
      {children}
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute z-40 whitespace-nowrap rounded-md bg-stone-900 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 ${pos}`}
      >
        {text}
      </span>
    </span>
  )
}
