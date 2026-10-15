import { useCallback, useEffect, useRef, useState } from 'react'

// Runs an async loader on mount and whenever `deps` change. Silent reloads (used for
// polling) keep existing data on screen instead of flashing skeletons. Stale
// responses from superseded requests are discarded.
export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const loaderRef = useRef(loader)
  const reqId = useRef(0)
  loaderRef.current = loader

  const run = useCallback(async ({ silent = false } = {}) => {
    const id = ++reqId.current
    if (!silent) setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await loaderRef.current()
      if (id === reqId.current) setState({ data, error: null, loading: false })
    } catch (error) {
      if (id !== reqId.current) return
      if (silent) setState((s) => ({ ...s, loading: false }))
      else setState({ data: null, error, loading: false })
    }
  }, [])

  useEffect(() => {
    run()
    return () => {
      reqId.current += 1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const setData = useCallback((data) => setState((s) => ({ ...s, data })), [])

  return { ...state, reload: run, setData }
}
