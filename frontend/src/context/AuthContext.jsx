import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authService, setUnauthorizedHandler, tokenStore } from '../services'

const AuthContext = createContext(null)

// status: 'loading' (verifying a stored token) | 'authenticated' | 'anonymous'
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() => (tokenStore.get() ? 'loading' : 'anonymous'))
  const [sessionExpired, setSessionExpired] = useState(false)

  const clearSession = useCallback(() => {
    tokenStore.clear()
    setUser(null)
    setStatus('anonymous')
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSessionExpired(true)
      clearSession()
    })
    return () => setUnauthorizedHandler(null)
  }, [clearSession])

  useEffect(() => {
    if (status !== 'loading') return undefined
    let cancelled = false
    authService
      .getMe()
      .then((u) => {
        if (cancelled) return
        setUser(u)
        setStatus('authenticated')
      })
      .catch((err) => {
        if (cancelled) return
        // Drop the token only when the server rejected it; keep it across network errors.
        if (err.status === 401 || err.status === 403) clearSession()
        else setStatus('anonymous')
      })
    return () => {
      cancelled = true
    }
  }, [status, clearSession])

  const login = useCallback(async ({ email, password }) => {
    const token = await authService.login({ email, password })
    tokenStore.set(token)
    try {
      const me = await authService.getMe()
      setUser(me)
      setStatus('authenticated')
      setSessionExpired(false)
      return me
    } catch (err) {
      tokenStore.clear()
      throw err
    }
  }, [])

  const register = useCallback(
    async ({ name, email, password }) => {
      await authService.register({ name, email, password })
      return login({ email, password })
    },
    [login],
  )

  const logout = useCallback(() => {
    setSessionExpired(false)
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({ user, status, sessionExpired, login, register, logout, setUser, isAuthenticated: status === 'authenticated' }),
    [user, status, sessionExpired, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
