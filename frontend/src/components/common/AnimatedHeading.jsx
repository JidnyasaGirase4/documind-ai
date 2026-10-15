import { useEffect, useRef, useState } from 'react'
import { cx } from '../../utils/format'

// Heading with a signature entrance: every word rises out of a mask (slight tilt + blur),
// one after another, once the heading scrolls into view. Words in `highlight` get a
// continuously shimmering gradient, and an optional underline sweeps in afterwards.
// Screen readers get the plain text; the animated words are hidden from them.
export function AnimatedHeading({ as: Tag = 'h2', text, highlight, tone = 'light', underline = false, align = 'left', delay = 0, className }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(typeof IntersectionObserver === 'undefined')

  useEffect(() => {
    if (visible || !ref.current) return undefined
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          io.disconnect()
        }
      },
      { threshold: 0.4 },
    )
    io.observe(ref.current)
    return () => io.disconnect()
  }, [visible])

  const words = text.split(' ')
  const hl = highlight ? highlight.split(' ') : []
  let hlStart = -1
  if (hl.length) {
    for (let i = 0; i <= words.length - hl.length; i += 1) {
      if (hl.every((w, j) => words[i + j] === w)) {
        hlStart = i
        break
      }
    }
  }
  const STEP = 70

  return (
    <Tag ref={ref} className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {words.map((w, i) => {
          const isHl = hlStart >= 0 && i >= hlStart && i < hlStart + hl.length
          return (
            <span key={`${w}-${i}`}>
              <span className="word-mask">
                <span
                  className={cx('word', visible ? 'word-in' : 'word-out', isHl && (tone === 'dark' ? 'shimmer-dark' : 'shimmer-light'))}
                  style={{ transitionDelay: `${delay + i * STEP}ms` }}
                >
                  {w}
                </span>
              </span>
              {i < words.length - 1 ? ' ' : null}
            </span>
          )
        })}
      </span>
      {underline && (
        <span
          className={cx(
            'mt-3 block h-1 w-14 rounded-full bg-gradient-to-r from-brand-600 to-gold-500 transition-transform duration-700 ease-out',
            align === 'center' ? 'mx-auto origin-center' : 'origin-left',
            visible ? 'scale-x-100' : 'scale-x-0',
          )}
          style={{ transitionDelay: `${delay + words.length * STEP + 150}ms` }}
          aria-hidden="true"
        />
      )}
    </Tag>
  )
}
