import { describe, expect, it } from 'vitest'
import { normalizeError } from '../services/http'

describe('normalizeError', () => {
  it('uses the backend error envelope message and code', () => {
    const err = normalizeError({ response: { status: 409, data: { error: { code: 'DOCUMENT_NOT_READY', message: 'This document is still being processed.', details: null } } } })
    expect(err.message).toBe('This document is still being processed.')
    expect(err.code).toBe('DOCUMENT_NOT_READY')
    expect(err.status).toBe(409)
  })

  it('joins FastAPI 422 validation messages', () => {
    const err = normalizeError({ response: { status: 422, data: { detail: [{ msg: 'Field required' }, { msg: 'Invalid email' }] } } })
    expect(err.message).toBe('Field required Invalid email')
  })

  it('falls back to a friendly message by status', () => {
    expect(normalizeError({ response: { status: 429, data: {} } }).message).toMatch(/too many requests/i)
  })

  it('reports a connection error when there is no response', () => {
    const err = normalizeError(new Error('Network Error'))
    expect(err.code).toBe('NETWORK_ERROR')
    expect(err.message).toMatch(/could not reach/i)
  })
})
