import { useState } from 'react'
import { Minus, Plus } from 'lucide-react'

// Open, ruled accordion (no boxes). WAI-ARIA pattern: header buttons control their
// panels; Enter/Space toggle, Up/Down/Home/End move between headers.
export function FAQ({ items }) {
  const [openId, setOpenId] = useState(0)

  const onKeyDown = (e, i) => {
    const buttons = [...e.currentTarget.closest('[data-faq]').querySelectorAll('button[data-faq-btn]')]
    let next = null
    if (e.key === 'ArrowDown') next = (i + 1) % buttons.length
    if (e.key === 'ArrowUp') next = (i - 1 + buttons.length) % buttons.length
    if (e.key === 'Home') next = 0
    if (e.key === 'End') next = buttons.length - 1
    if (next !== null) {
      e.preventDefault()
      buttons[next].focus()
    }
  }

  return (
    <div data-faq className="divide-y divide-line border-y border-line">
      {items.map((item, i) => {
        const open = openId === i
        return (
          <div key={item.q}>
            <h3>
              <button
                type="button"
                data-faq-btn
                id={`faq-btn-${i}`}
                aria-expanded={open}
                aria-controls={`faq-panel-${i}`}
                onClick={() => setOpenId(open ? null : i)}
                onKeyDown={(e) => onKeyDown(e, i)}
                className="group flex w-full items-center gap-4 py-4 text-left"
              >
                <span className={`font-display text-xs font-bold transition-colors ${open ? 'text-brand-600' : 'text-muted'}`} aria-hidden="true">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className={`flex-1 text-[17px] font-semibold transition-colors ${open ? 'text-brand-700' : 'text-ink group-hover:text-brand-700'}`}>{item.q}</span>
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
                    open ? 'rotate-180 bg-brand-600 text-white' : 'bg-stone-100 text-muted group-hover:bg-brand-50 group-hover:text-brand-700'
                  }`}
                  aria-hidden="true"
                >
                  {open ? <Minus className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                </span>
              </button>
            </h3>
            <div id={`faq-panel-${i}`} role="region" aria-labelledby={`faq-btn-${i}`} hidden={!open} className="animate-fade-in pb-5 pl-9 pr-11 text-[15px] leading-relaxed text-muted">
              {item.a}
            </div>
          </div>
        )
      })}
    </div>
  )
}
