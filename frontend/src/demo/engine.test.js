import { beforeEach, describe, expect, it } from 'vitest'
import { handle, resetDemoForTests } from './engine'

const call = (method, url, { data, params, token } = {}) =>
  handle({ method, url, data: data ? JSON.stringify(data) : undefined, params, headers: token ? { Authorization: `Bearer ${token}` } : {} })
const fails = async (p, status) => {
  const err = await p.then(() => null, (e) => e)
  expect(err?.response?.status).toBe(status)
  return err.response.data.error
}

describe('public demo engine', () => {
  beforeEach(() => {
    localStorage.clear()
    resetDemoForTests()
  })

  it('registers a visitor, rejects duplicates and signs in', async () => {
    await call('post', '/auth/register', { data: { name: 'Vi', email: 'Vi@Example.com', password: 'Visitor2026x' } })
    expect((await fails(call('post', '/auth/register', { data: { name: 'Vi', email: 'vi@example.com', password: 'Visitor2026x' } }), 409)).code).toBe('EMAIL_EXISTS')
    const { data } = await call('post', '/auth/login', { data: { email: 'vi@example.com', password: 'Visitor2026x' } })
    const me = await call('get', '/auth/me', { token: data.access_token })
    expect(me.data.name).toBe('Vi')
    await fails(call('post', '/auth/login', { data: { email: 'vi@example.com', password: 'wrong' } }), 401)
  })

  it('signs in the sample account and requires a token for data', async () => {
    await fails(call('get', '/documents'), 401)
    const { data } = await call('post', '/auth/login', { data: { email: 'demo@example.com', password: 'DocuMind2026' } })
    const docs = await call('get', '/documents', { token: data.access_token, params: { page_size: 3 } })
    expect(docs.data.total).toBe(6)
    expect(docs.data.items).toHaveLength(3)
  })

  it('searches the sample passages by word start and approximates semantic mode', async () => {
    const token = (await call('post', '/auth/login', { data: { email: 'demo@example.com', password: 'DocuMind2026' } })).data.access_token
    const { data } = await call('post', '/search', { token, data: { query: 'password rotation', mode: 'hybrid' } })
    expect(data.items[0].title).toBe('api-security-guidelines.pdf')
    expect(data.warnings).toContain('demo_semantic_approximation')
    const none = await call('post', '/search', { token, data: { query: 'zzzqqq', mode: 'keyword' } })
    expect(none.data.total).toBe(0)
  })

  it('answers from the documents with a citation, or says there is not enough evidence', async () => {
    const token = (await call('post', '/auth/login', { data: { email: 'demo@example.com', password: 'DocuMind2026' } })).data.access_token
    const conv = (await call('post', '/conversations', { token, data: {} })).data
    const ok = await call('post', `/conversations/${conv.id}/messages`, { token, data: { content: 'Within how many minutes must a Severity 1 incident be acknowledged?' } })
    expect(ok.data.assistant_message.content).toContain('15 minutes')
    expect(ok.data.assistant_message.citations[0].document_name).toBe('incident-response-runbook.pdf')
    const no = await call('post', `/conversations/${conv.id}/messages`, { token, data: { content: 'weather on mars' } })
    expect(no.data.assistant_message.citations).toEqual([])
    expect(no.data.assistant_message.content).toContain("couldn't find enough evidence")
  })

  it('switches off everything that changes shared data', async () => {
    const token = (await call('post', '/auth/login', { data: { email: 'demo@example.com', password: 'DocuMind2026' } })).data.access_token
    expect((await fails(call('post', '/collections', { token, data: { name: 'x' } }), 403)).code).toBe('DEMO_DISABLED')
    await fails(call('delete', '/documents/11', { token }), 403)
  })
})
