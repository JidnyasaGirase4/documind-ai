import { useEffect, useRef } from 'react'

// Calls `callback` every `intervalMs` while `enabled`. Waits for the previous call to
// finish, skips ticks while the tab is hidden, and stops on unmount or when disabled.
export function usePolling(callback, intervalMs, enabled) {
  const cb = useRef(callback)
  cb.current = callback

  useEffect(() => {
    if (!enabled) return undefined
    let stopped = false
    let timer
    const tick = async () => {
      if (!document.hidden) {
        try {
          await cb.current()
        } catch {
          /* the caller surfaces errors; keep polling */
        }
      }
      if (!stopped) timer = setTimeout(tick, intervalMs)
    }
    timer = setTimeout(tick, intervalMs)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [enabled, intervalMs])
}
