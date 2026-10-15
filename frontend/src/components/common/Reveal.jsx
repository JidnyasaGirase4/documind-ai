import { useEffect, useRef, useState } from 'react'
import { cx } from '../../utils/format'

// Fades/slides children in when they scroll into view. Content is visible
// immediately if IntersectionObserver is unavailable.
export function Reveal({ as: Tag = 'div', delay = 0, className, children, ...rest }) {
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
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(ref.current)
    return () => io.disconnect()
  }, [visible])

  return (
    <Tag ref={ref} className={cx('reveal', visible && 'is-visible', className)} style={{ transitionDelay: `${delay}ms` }} {...rest}>
      {children}
    </Tag>
  )
}
