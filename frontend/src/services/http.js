import axios from 'axios'
import { API_BASE_URL, API_PREFIX, TOKEN_STORAGE_KEY } from '../utils/config'

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'UNKNOWN', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

// Bearer tokens live in localStorage: simple and survives reloads, but readable by
// any script running on the page (XSS). See README "Security notes".
export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY)
    } catch {
      return null
    }
  },
  set(token) {
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } catch {
      /* storage unavailable */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    } catch {
      /* storage unavailable */
    }
  },
}

let unauthorizedHandler = null
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

export const http = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const FALLBACK_MESSAGES = {
  401: 'Your session has expired. Please sign in again.',
  403: 'You do not have access to this resource.',
  404: 'We could not find what you were looking for.',
  413: 'That file is too large.',
  415: 'That file type is not supported.',
  429: 'Too many requests. Please wait a moment and try again.',
  503: 'The AI service is temporarily unavailable. Please try again shortly.',
}

// Turns any Axios failure into an ApiError with a user-safe message.
// Messages come from the backend's { error: { code, message, details } } shape and
// are rendered as plain text by React, never as HTML.
export function normalizeError(err) {
  if (err instanceof ApiError) return err
  if (axios.isCancel?.(err) || err?.code === 'ERR_CANCELED') {
    return new ApiError('Request cancelled.', { code: 'CANCELLED' })
  }
  if (err?.response) {
    const { status, data } = err.response
    const body = data?.error ?? data
    let message = typeof body?.message === 'string' ? body.message : null
    if (!message && typeof body?.detail === 'string') message = body.detail
    if (!message && Array.isArray(body?.detail)) {
      message = body.detail.map((d) => d?.msg).filter(Boolean).join(' ') || null
    }
    return new ApiError(message || FALLBACK_MESSAGES[status] || 'Something went wrong. Please try again.', {
      status,
      code: body?.code || `HTTP_${status}`,
      details: body?.details ?? null,
    })
  }
  if (err?.code === 'ECONNABORTED') {
    return new ApiError('The request took too long. Please try again.', { code: 'TIMEOUT' })
  }
  return new ApiError(
    `We could not reach the DocuMind server at ${API_BASE_URL}. Check your connection and that the backend is running.`,
    { code: 'NETWORK_ERROR' },
  )
}

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const apiError = normalizeError(err)
    const isAuthCall = /\/auth\/(login|register)$/.test(err?.config?.url || '')
    if (apiError.status === 401 && !isAuthCall && tokenStore.get()) {
      tokenStore.clear()
      unauthorizedHandler?.()
    }
    return Promise.reject(apiError)
  },
)
