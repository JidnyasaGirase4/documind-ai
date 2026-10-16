// The public demo's "backend": answers the app's API calls inside the browser from recorded data (fixtures.json = real responses of
// the real backend with the sample data). Used only in the demo build (VITE_DEMO=1, see services/http.js). Nothing leaves the browser:
// accounts, chats and feedback are kept in this browser's localStorage. Uploading, sharing, editing and AI model calls are not available.
import { AxiosError } from 'axios'
import fixtures from './fixtures.json'

const USERS_KEY = 'documind.demo.users'
const CHATS_KEY = 'documind.demo.conversations'
export const DEMO_ACCOUNT = { email: 'demo@example.com', password: 'DocuMind2026' }
const DISABLED = 'This action is disabled in the public demo. Run the full app locally to use it (see the project page).'
const STOP = new Set('a an and are as at be by can do does for from has have how i in is it its of on or our should that the their there this to was what when where which who why will with within you your must'.split(' '))

const store = {
  read(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback
    } catch {
      return fallback
    }
  },
  write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* storage unavailable: the demo keeps working for this page view */
    }
  },
}
let memory = {}
const users = () => store.read(USERS_KEY, memory[USERS_KEY] ?? [])
const chats = () => store.read(CHATS_KEY, memory[CHATS_KEY] ?? [])
const save = (key, value) => {
  memory[key] = value
  store.write(key, value)
}

class Fail extends Error {
  constructor(status, code, message) {
    super(message)
    this.status = status
    this.code = code
  }
}
const nowIso = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ---- helpers
function page(items, params = {}) {
  const size = Math.max(1, Number(params.page_size) || 10)
  const p = Math.max(1, Number(params.page) || 1)
  return { items: items.slice((p - 1) * size, p * size), total: items.length, page: p, page_size: size, pages: Math.max(1, Math.ceil(items.length / size)) }
}
const words = (s) => (String(s).toLowerCase().match(/[a-z0-9]+/g) || [])
const docById = (id) => fixtures.documents.find((d) => d.id === Number(id))
const need = (x, what = 'document') => {
  if (!x) throw new Fail(404, 'NOT_FOUND', `That ${what} was not found.`)
  return x
}
const currentVersionId = (docId) => (fixtures.versions[docId] || []).find((v) => v.is_current)?.id ?? fixtures.versions[docId]?.[0]?.id
const sortBy = (items, key, order) => [...items].sort((a, b) => (a[key] > b[key] ? 1 : a[key] < b[key] ? -1 : 0) * (order === 'asc' ? 1 : -1))

async function asset(path, type) {
  const base = import.meta.env.BASE_URL || './'
  const res = await fetch(`${base}demo/${path}`)
  if (!res.ok) throw new Fail(404, 'NOT_FOUND', 'That file is not part of the demo.')
  return new Blob([await res.arrayBuffer()], { type })
}

// ---- sign-in
function authHeader(cfg) {
  const h = cfg.headers
  const raw = (typeof h?.get === 'function' ? h.get('Authorization') : h?.Authorization) || ''
  return String(raw).replace(/^Bearer\s+/i, '')
}
const publicUser = (u) => ({ id: u.id, name: u.name, email: u.email, created_at: u.created_at })
function allUsers() {
  return [{ ...fixtures.user, password: DEMO_ACCOUNT.password }, ...users()]
}
function currentUser(cfg) {
  const m = /^demo-token-(\d+)$/.exec(authHeader(cfg))
  const u = m && allUsers().find((x) => x.id === Number(m[1]))
  if (!u) throw new Fail(401, 'UNAUTHORIZED', 'Your session has expired. Please sign in again.')
  return u
}

// ---- search over the sample passages (word-start matching; the full app also has meaning-based search)
function snippet(text, terms) {
  const low = text.toLowerCase()
  const at = Math.max(0, Math.min(...terms.map((t) => low.search(new RegExp(`\\b${t}`))).filter((i) => i >= 0), text.length))
  const start = Math.max(0, at - 80)
  const part = text.slice(start, start + 260)
  return `${start > 0 ? '…' : ''}${part}${start + 260 < text.length ? '…' : ''}`
}
const hits = (text, terms) => terms.filter((t) => new RegExp(`\\b${t}`).test(text.toLowerCase()))

function runSearch(body) {
  const query = String(body.query || '').trim()
  if (!query) throw new Fail(422, 'VALIDATION_ERROR', 'Type something to search for.')
  const terms = [...new Set(words(query))]
  const warnings = []
  if (body.mode !== 'keyword') warnings.push('demo_semantic_approximation')
  const inScope = (d) =>
    (!body.collection_id || d.collection_ids.includes(Number(body.collection_id))) &&
    (body.category_id === undefined || body.category_id === null || d.category?.id === Number(body.category_id)) &&
    (!body.tag_id || d.tags.some((t) => t.id === Number(body.tag_id))) &&
    (!body.file_type || body.file_type === 'pdf')
  const byDoc = new Map()
  const run = (needAll) => {
    byDoc.clear()
    for (const c of fixtures.chunks.filter((x) => x.is_current)) {
      const d = docById(c.document_id)
      if (!d || !inScope(d)) continue
      const matched = hits(c.text, terms)
      if (!matched.length || (needAll && matched.length < terms.length)) continue
      const list = byDoc.get(d.id) ?? []
      list.push({ c, matched })
      byDoc.set(d.id, list)
    }
  }
  run(true)
  if (!byDoc.size && terms.length > 1) {
    run(false)
    if (byDoc.size) warnings.push('relaxed_to_any_term')
  }
  let items = [...byDoc.entries()].map(([id, list]) => {
    const d = docById(id)
    list.sort((a, b) => b.matched.length - a.matched.length)
    const score = list[0].matched.length / terms.length + Math.min(0.2, list.length * 0.05)
    return {
      document_id: id,
      title: d.original_filename,
      score: Math.round(score * 1000) / 1000,
      matched_on: ['keyword'],
      passages: list.slice(0, 3).map(({ c }, i) => ({ chunk_id: c.chunk_id, page_number: c.page, snippet: snippet(c.text, terms), keyword_match: true, keyword_rank: i + 1, semantic_rank: null, semantic_similarity: null })),
      total_pages: d.total_pages,
      category: d.category,
      tags: d.tags,
      collections: fixtures.collections.filter((c) => d.collection_ids.includes(c.id)).map((c) => ({ id: c.id, name: c.name })),
      role: d.role,
      created_at: d.created_at,
    }
  })
  const sort = body.sort_by || 'relevance'
  items = sort === 'newest' ? sortBy(items, 'created_at', 'desc') : sort === 'oldest' ? sortBy(items, 'created_at', 'asc') : sort === 'title' ? sortBy(items, 'title', 'asc') : sortBy(items, 'score', 'desc')
  const p = page(items, body)
  return { query, mode: body.mode || 'hybrid', terms, phrases: [], ...p, total_exact: true, ranking: { method: 'keyword' }, warnings }
}

// ---- assistant: answers by quoting the best-matching sentences of the sample documents (no AI model in the demo)
function answer(question, documentIds) {
  const terms = [...new Set(words(question).filter((w) => !STOP.has(w) && w.length > 1))]
  const stem = (t) => (t.length > 6 ? t.slice(0, t.length - 2) : t)
  const pool = fixtures.chunks.filter((c) => c.is_current && (!documentIds?.length || documentIds.includes(c.document_id)))
  let best = null
  for (const c of pool) {
    for (const s of c.text.split(/(?<=[.!?])\s+/)) {
      const low = s.toLowerCase()
      const matched = terms.filter((t) => new RegExp(`\\b${stem(t)}`).test(low))
      const score = matched.length + (/\d/.test(s) ? 0.25 : 0)
      if (matched.length >= Math.min(2, terms.length) && (!best || score > best.score)) best = { score, sentence: s, chunk: c, matched }
    }
  }
  if (!best) {
    return { content: "I couldn't find enough evidence in your documents to answer that. Try rephrasing the question, or select the documents that should contain the answer.", citations: [] }
  }
  const { chunk } = best
  const d = docById(chunk.document_id)
  return {
    content: `${best.sentence.trim()} [S1]\n\n(Demo answer: the public demo quotes the best-matching sentence from the sample documents. The full app writes a complete answer with a local AI model.)`,
    citations: [{ document_id: d.id, document_name: d.original_filename, page_number: chunk.page, excerpt: chunk.text.slice(0, 400), chunk_id: chunk.chunk_id, version_id: chunk.version_id, version_number: chunk.version_number, version_is_current: true }],
  }
}

// ---- the routes
const routes = []
const route = (method, pattern, fn) => routes.push({ method, re: new RegExp(`^${pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)')}$`), fn })

route('post', '/auth/register', ({ body }) => {
  const name = String(body.name || '').trim()
  const email = String(body.email || '').trim().toLowerCase()
  const errs = []
  if (!name) errs.push('Name is required.')
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errs.push('Enter a valid email address.')
  if (String(body.password || '').length < 8) errs.push('Password must be at least 8 characters.')
  if (errs.length) throw new Fail(422, 'VALIDATION_ERROR', errs.join(' '))
  if (allUsers().some((u) => u.email === email)) throw new Fail(409, 'EMAIL_EXISTS', 'An account with this email already exists.')
  const list = users()
  const u = { id: 1000 + list.length + 1, name, email, password: body.password, created_at: nowIso() }
  save(USERS_KEY, [...list, u])
  return publicUser(u)
})
route('post', '/auth/login', ({ body }) => {
  const email = String(body.email || '').trim().toLowerCase()
  const u = allUsers().find((x) => x.email === email && x.password === body.password)
  if (!u) throw new Fail(401, 'INVALID_CREDENTIALS', 'Incorrect email or password.')
  return { access_token: `demo-token-${u.id}`, token_type: 'bearer' }
})
route('get', '/auth/me', ({ user }) => publicUser(user))
route('get', '/settings/profile', ({ user }) => publicUser(user))
route('patch', '/settings/profile', ({ user, body }) => {
  const name = String(body.name || '').trim()
  if (!name) throw new Fail(422, 'VALIDATION_ERROR', 'Name is required.')
  if (user.id === fixtures.user.id) return { ...publicUser(user), name }
  const list = users().map((u) => (u.id === user.id ? { ...u, name } : u))
  save(USERS_KEY, list)
  return publicUser({ ...user, name })
})

route('get', '/dashboard/stats', () => fixtures.dashboard_stats)
route('get', '/dashboard/activity', () => fixtures.dashboard_activity)
for (const k of ['overview', 'feedback', 'queries', 'evaluations']) route('get', `/analytics/${k}`, () => fixtures.analytics[k])
route('get', '/analytics/evaluations/:id', () => need(null, 'evaluation'))

route('get', '/documents', ({ params }) => {
  let items = params.scope === 'shared' ? [] : fixtures.documents
  const s = String(params.search || '').toLowerCase()
  if (s) items = items.filter((d) => d.original_filename.toLowerCase().includes(s))
  if (params.status) items = items.filter((d) => d.processing_status === params.status)
  if (params.collection_id) items = items.filter((d) => d.collection_ids.includes(Number(params.collection_id)))
  if (params.category_id !== undefined && params.category_id !== '') items = items.filter((d) => (params.category_id === 'none' ? !d.category : d.category?.id === Number(params.category_id)))
  if (params.tag_id) items = items.filter((d) => d.tags.some((t) => t.id === Number(params.tag_id)))
  const key = { name: 'original_filename', filename: 'original_filename', size: 'file_size' }[params.sort_by] || params.sort_by || 'created_at'
  return page(sortBy(items, key, params.sort_order || 'desc'), params)
})
route('get', '/documents/:id', ({ m }) => need(docById(m.id)))
route('get', '/documents/:id/versions', ({ m }) => need(fixtures.versions[m.id]))
route('get', '/documents/:id/versions/compare', ({ m, params }) => need(fixtures.compare[`${m.id}:${params.from}:${params.to}`], 'comparison'))
route('get', '/documents/:id/highlights', ({ params }) => need(fixtures.highlights[params.chunk_id], 'passage'))
route('get', '/documents/:id/review', ({ m }) => need(fixtures.review[m.id], 'review schedule'))
route('get', '/documents/:id/review/history', ({ m, params }) => {
  const h = fixtures.review_history[m.id]
  return h && !Array.isArray(h) ? { ...h, ...page(h.items ?? [], params) } : page(h ?? [], params)
})
route('get', '/documents/:id/pages/:n/image', async ({ m, params }) => {
  const vid = params.version_id || currentVersionId(m.id)
  const f = fixtures.files.pages.find((x) => x.version_id === Number(vid) && x.page === Number(m.n))
  return { blob: await asset(need(f, 'page').file, 'image/png') }
})
const pdf = async (m, versionId) => {
  const f = fixtures.files.pdfs.find((x) => x.version_id === Number(versionId ?? currentVersionId(m.id)))
  return { blob: await asset(need(f, 'file').file, 'application/pdf') }
}
route('get', '/documents/:id/preview', ({ m, params }) => pdf(m, params.version_id))
route('get', '/documents/:id/versions/:vid/download', ({ m }) => pdf(m, m.vid))

route('get', '/collections', ({ params }) => {
  let items = fixtures.collections
  const s = String(params.search || '').toLowerCase()
  if (s) items = items.filter((c) => c.name.toLowerCase().includes(s))
  return page(sortBy(items, params.sort_by === 'name' ? 'name' : params.sort_by || 'name', params.sort_order || 'asc'), params)
})
route('get', '/collections/:id', ({ m }) => need(fixtures.collections.find((c) => c.id === Number(m.id)), 'collection'))
route('get', '/collections/:id/members', ({ m }) => fixtures.members[m.id] ?? [])
route('get', '/categories', () => fixtures.categories)
route('get', '/tags', () => fixtures.tags)

route('get', '/reviews/summary', () => fixtures.review_summary)
route('get', '/reviews', ({ params }) => {
  let items = fixtures.reviews_list
  if (params.status) items = items.filter((r) => r.status === params.status)
  const s = String(params.search || '').toLowerCase()
  if (s) items = items.filter((r) => r.title.toLowerCase().includes(s))
  if (params.collection_id) items = items.filter((r) => docById(r.document_id)?.collection_ids.includes(Number(params.collection_id)))
  return page(items, params)
})
route('get', '/conflicts', ({ params }) => page(fixtures.conflicts, params))
route('get', '/conflicts/reports/:id', () => need(null, 'report'))
route('get', '/conflicts/:id/decisions', ({ m }) => fixtures.decisions[m.id] ?? [])

// chats are the only things a visitor can create in the demo
route('get', '/conversations', ({ params }) => {
  let items = chats().map(({ messages, ...c }) => ({ ...c, message_count: messages.length }))
  const s = String(params.search || '').toLowerCase()
  if (s) items = items.filter((c) => c.title.toLowerCase().includes(s))
  return page(sortBy(items, 'updated_at', 'desc'), params)
})
route('post', '/conversations', ({ body }) => {
  const list = chats()
  const c = { id: (list.reduce((n, x) => Math.max(n, x.id), 0) || 0) + 1, title: body.title || 'New conversation', created_at: nowIso(), updated_at: nowIso(), messages: [] }
  save(CHATS_KEY, [c, ...list])
  return { ...c, message_count: 0 }
})
const findChat = (id) => need(chats().find((c) => c.id === Number(id)), 'conversation')
const patchChat = (id, fn) => {
  const list = chats().map((c) => (c.id === Number(id) ? fn(c) : c))
  save(CHATS_KEY, list)
  return list.find((c) => c.id === Number(id))
}
route('get', '/conversations/:id', ({ m }) => {
  const c = findChat(m.id)
  return { ...c, message_count: c.messages.length }
})
route('patch', '/conversations/:id', ({ m, body }) => {
  findChat(m.id)
  return patchChat(m.id, (c) => ({ ...c, title: String(body.title || c.title).slice(0, 120) }))
})
route('delete', '/conversations/:id', ({ m }) => {
  findChat(m.id)
  save(CHATS_KEY, chats().filter((c) => c.id !== Number(m.id)))
  return null
})
route('post', '/conversations/:id/messages', async ({ m, body }) => {
  const c = findChat(m.id)
  const text = String(body.content || '').trim()
  if (!text) throw new Fail(422, 'VALIDATION_ERROR', 'Type a question first.')
  await sleep(700)
  const next = c.messages.reduce((n, x) => Math.max(n, x.id), 0) + 1
  const a = answer(text, body.document_ids)
  const user_message = { id: next, role: 'user', content: text, citations: [], feedback: null, created_at: nowIso() }
  const assistant_message = { id: next + 1, role: 'assistant', content: a.content, citations: a.citations, feedback: null, created_at: nowIso() }
  patchChat(m.id, (x) => ({ ...x, title: x.messages.length ? x.title : text.slice(0, 60), updated_at: nowIso(), messages: [...x.messages, user_message, assistant_message] }))
  return { user_message, assistant_message }
})
route('put', '/conversations/:id/messages/:mid/feedback', ({ m, body }) => {
  findChat(m.id)
  const fb = { rating: body.rating, category: body.category ?? null, comment: body.comment ?? null }
  patchChat(m.id, (c) => ({ ...c, messages: c.messages.map((x) => (x.id === Number(m.mid) ? { ...x, feedback: fb } : x)) }))
  return fb
})
route('delete', '/conversations/:id/messages/:mid/feedback', ({ m }) => {
  findChat(m.id)
  patchChat(m.id, (c) => ({ ...c, messages: c.messages.map((x) => (x.id === Number(m.mid) ? { ...x, feedback: null } : x)) }))
  return null
})
route('post', '/search', ({ body }) => runSearch(body))

// ---- adapter
function toBody(data) {
  if (!data) return {}
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch {
      return {}
    }
  }
  return typeof FormData !== 'undefined' && data instanceof FormData ? {} : data
}

export async function handle(cfg) {
  const method = (cfg.method || 'get').toLowerCase()
  const path = String(cfg.url || '').replace(/^https?:\/\/[^/]+/, '').replace(/^\/api\/v1/, '').split('?')[0]
  const fail = (status, data) => new AxiosError(data.error.message, status >= 500 ? 'ERR_BAD_RESPONSE' : 'ERR_BAD_REQUEST', cfg, {}, { status, statusText: '', data, headers: {}, config: cfg, request: {} })
  try {
    await sleep(120)
    const found = routes.find((r) => r.method === method && r.re.test(path))
    const open = path === '/auth/login' || path === '/auth/register'
    if (!found) {
      if (!open) currentUser(cfg)
      throw method === 'get' ? new Fail(404, 'NOT_FOUND', 'That page of the demo does not exist.') : new Fail(403, 'DEMO_DISABLED', DISABLED)
    }
    const user = open ? null : currentUser(cfg)
    const out = await found.fn({ m: found.re.exec(path).groups ?? {}, params: cfg.params ?? {}, body: toBody(cfg.data), user })
    const blob = out && out.blob
    return { data: blob ?? (out === undefined ? null : out), status: out === null ? 204 : 200, statusText: 'OK', headers: blob ? { 'content-type': blob.type } : {}, config: cfg, request: {} }
  } catch (e) {
    if (e instanceof Fail) throw fail(e.status, { error: { code: e.code, message: e.message } })
    throw e
  }
}

export function resetDemoForTests() {
  memory = {}
}
