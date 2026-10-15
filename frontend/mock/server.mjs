// DEV-ONLY mock of the DocuMind AI backend so every screen can be explored without FastAPI.
// It accepts ANY email/password and returns sample data. Answers are canned and labelled
// "[Mock]". Never deploy this. Run with: npm run mock  (listens on http://127.0.0.1:8000)
import http from 'node:http'

const PORT = Number(process.env.MOCK_PORT) || 8000
const now = Date.now()
const iso = (hoursAgo) => new Date(now - hoursAgo * 3600e3).toISOString()

let nextDocId = 100
let nextConvId = 100
let nextMsgId = 1000

const docs = [
  { id: 1, original_filename: 'employee-handbook-2026.pdf', file_size: 2457600, processing_status: 'ready', total_pages: 48, created_at: iso(5) },
  { id: 2, original_filename: 'quarterly-financial-report-q3.pdf', file_size: 5120000, processing_status: 'processing', total_pages: null, created_at: iso(2) },
  { id: 3, original_filename: 'scanned-contract.pdf', file_size: 880000, processing_status: 'failed', processing_error: 'No extractable text found. OCR is not supported yet.', created_at: iso(30) },
  { id: 4, original_filename: 'api-reference-v2.pdf', file_size: 1300000, processing_status: 'ready', total_pages: 120, created_at: iso(70) },
]

const seedMessages = [
  { id: 1, role: 'user', content: 'How many weeks of parental leave are offered?', created_at: iso(4) },
  {
    id: 2,
    role: 'assistant',
    created_at: iso(4),
    content: '[Mock] The handbook provides 16 weeks of paid parental leave for primary caregivers and 6 weeks for secondary caregivers.',
    citations: [
      { document_id: 1, document_name: 'employee-handbook-2026.pdf', page_number: 14, excerpt: 'Primary caregivers are entitled to sixteen weeks of paid leave, taken within the first year.' },
      { document_id: 1, document_name: 'employee-handbook-2026.pdf', page_number: 15, excerpt: 'Secondary caregivers receive six weeks of paid leave.' },
    ],
    follow_up_questions: ['Can leave be taken in parts?', 'Who counts as a primary caregiver?'],
  },
]

const convs = [
  { id: 'c1', title: 'Parental leave policy', created_at: iso(4), updated_at: iso(3), messages: seedMessages },
  { id: 'c2', title: 'Warranty terms overview', created_at: iso(50), updated_at: iso(48), messages: [] },
]

const pageOf = (items) => ({ items, total: items.length, page: 1, page_size: 10, pages: 1 })
const series = (n, f) => Array.from({ length: n }, (_, i) => ({ date: new Date(now - (n - 1 - i) * 864e5).toISOString().slice(0, 10), count: f(i) }))
const count = (s) => docs.filter((d) => d.processing_status === s).length
const asConv = (c) => ({ id: c.id, title: c.title, created_at: c.created_at, updated_at: c.updated_at, message_count: c.messages.length })

const json = (res, status, body) => {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json')
  res.end(body === undefined ? '' : JSON.stringify(body))
}

function readBody(req) {
  return new Promise((resolve) => {
    let data = ''
    req.on('data', (c) => (data += c))
    req.on('end', () => {
      try {
        resolve(data && req.headers['content-type']?.includes('json') ? JSON.parse(data) : {})
      } catch {
        resolve({})
      }
    })
  })
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', '*')
  res.setHeader('Access-Control-Allow-Methods', '*')
  if (req.method === 'OPTIONS') return res.end()

  const path = req.url.split('?')[0].replace('/api/v1', '')
  const key = `${req.method} ${path}`
  const body = await readBody(req)
  const docMatch = path.match(/^\/documents\/(\d+)(\/\w+)?$/)
  const convMatch = path.match(/^\/conversations\/([\w-]+)(\/messages)?$/)

  if (key === 'POST /auth/register') return json(res, 201, { id: 1, name: body.name, email: body.email })
  if (key === 'POST /auth/login') return json(res, 200, { access_token: 'mock-token', token_type: 'bearer' })
  if (key === 'GET /auth/me' || key === 'GET /settings/profile') return json(res, 200, { id: 1, name: 'Demo User', email: 'demo@example.com', created_at: iso(900) })
  if (key === 'PATCH /settings/profile') return json(res, 200, { id: 1, name: body.name || 'Demo User', email: 'demo@example.com', created_at: iso(900) })

  if (key === 'GET /dashboard/stats')
    return json(res, 200, { total_documents: docs.length, ready_documents: count('ready'), processing_documents: count('processing') + count('uploaded'), failed_documents: count('failed') })
  if (key === 'GET /dashboard/activity')
    return json(res, 200, [
      { type: 'upload', title: 'Uploaded quarterly-financial-report-q3.pdf', timestamp: iso(2) },
      { type: 'question', title: 'Asked a question in "Parental leave policy"', timestamp: iso(3) },
    ])
  if (key === 'GET /analytics/overview')
    return json(res, 200, {
      uploads_over_time: series(10, (i) => [1, 0, 2, 3, 1, 0, 4, 2, 1, 3][i]),
      status_distribution: ['ready', 'processing', 'failed', 'uploaded'].map((status) => ({ status, count: count(status) })),
      question_activity: series(10, (i) => [2, 5, 3, 8, 6, 4, 9, 7, 5, 11][i]),
    })

  if (key === 'GET /documents') return json(res, 200, pageOf(docs))
  if (key === 'POST /documents/upload') {
    const doc = { id: nextDocId++, original_filename: 'uploaded-file.pdf', file_size: 500000, processing_status: 'processing', created_at: new Date().toISOString() }
    docs.unshift(doc)
    setTimeout(() => {
      doc.processing_status = 'ready'
      doc.total_pages = 12
    }, 8000)
    return json(res, 201, doc)
  }
  if (docMatch) {
    const doc = docs.find((d) => d.id === Number(docMatch[1]))
    if (!doc) return json(res, 404, { error: { code: 'NOT_FOUND', message: 'Document not found.' } })
    if (req.method === 'GET' && !docMatch[2]) return json(res, 200, doc)
    if (req.method === 'DELETE') {
      docs.splice(docs.indexOf(doc), 1)
      return json(res, 204)
    }
    if (req.method === 'POST' && docMatch[2] === '/retry') {
      doc.processing_status = 'processing'
      doc.processing_error = null
      return json(res, 202, doc)
    }
    if (req.method === 'GET' && docMatch[2] === '/preview') return json(res, 404, { error: { code: 'NO_PREVIEW', message: 'The mock server has no PDF files to preview.' } })
  }

  if (key === 'GET /conversations') return json(res, 200, pageOf(convs.map(asConv)))
  if (key === 'POST /conversations') {
    const c = { id: `c${nextConvId++}`, title: 'New conversation', created_at: new Date().toISOString(), updated_at: new Date().toISOString(), messages: [] }
    convs.unshift(c)
    return json(res, 201, asConv(c))
  }
  if (convMatch) {
    const c = convs.find((x) => x.id === convMatch[1])
    if (!c) return json(res, 404, { error: { code: 'NOT_FOUND', message: 'Conversation not found.' } })
    if (req.method === 'GET' && !convMatch[2]) return json(res, 200, { ...asConv(c), messages: c.messages })
    if (req.method === 'PATCH') {
      c.title = body.title || c.title
      return json(res, 200, asConv(c))
    }
    if (req.method === 'DELETE') {
      convs.splice(convs.indexOf(c), 1)
      return json(res, 204)
    }
    if (req.method === 'POST' && convMatch[2]) {
      const user = { id: nextMsgId++, role: 'user', content: body.content, created_at: new Date().toISOString() }
      const assistant = {
        id: nextMsgId++,
        role: 'assistant',
        created_at: new Date().toISOString(),
        content: '[Mock] This is a canned answer from the development mock server. Connect the real backend for answers from your documents.',
        citations: [{ document_id: 1, document_name: 'employee-handbook-2026.pdf', page_number: 14, excerpt: 'Primary caregivers are entitled to sixteen weeks of paid leave.' }],
      }
      c.messages.push(user, assistant)
      if (c.title === 'New conversation') c.title = String(body.content).slice(0, 40)
      c.updated_at = new Date().toISOString()
      return setTimeout(() => json(res, 201, { user_message: user, assistant_message: assistant }), 900)
    }
  }

  return json(res, 404, { error: { code: 'NOT_FOUND', message: 'Not found.' } })
})

server.listen(PORT, '127.0.0.1', () => console.log(`DocuMind mock API (dev only) on http://127.0.0.1:${PORT} — any email/password works`))
