// Single place that maps backend payloads onto the shapes the UI uses.
// Field names are defined in docs/API_CONTRACT.md. Where the backend plan leaves
// names open (e.g. name vs full_name) the documented alternatives are accepted here
// so components never guess.

export function normalizeUser(u) {
  if (!u) return null
  return {
    id: u.id,
    name: u.name ?? u.full_name ?? '',
    email: u.email ?? '',
    createdAt: u.created_at ?? null,
  }
}

export function normalizeDocument(d) {
  return {
    id: d.id,
    filename: d.original_filename ?? d.filename ?? 'Untitled',
    size: d.file_size ?? null,
    status: d.processing_status ?? d.status ?? 'uploaded',
    error: d.processing_error ?? null,
    pages: d.total_pages ?? null,
    createdAt: d.created_at ?? null,
    updatedAt: d.updated_at ?? null,
  }
}

export function normalizeCitation(c) {
  return {
    documentId: c.document_id ?? null,
    documentName: c.document_name ?? c.original_filename ?? c.filename ?? null,
    page: c.page_number ?? c.page ?? null,
    excerpt: c.excerpt ?? c.text ?? null,
    chunkId: c.chunk_id ?? null,
  }
}

export function normalizeMessage(m) {
  const raw = m.citations ?? m.citation_metadata ?? []
  const list = Array.isArray(raw) ? raw : (raw?.citations ?? [])
  return {
    id: m.id,
    role: m.role,
    content: m.content ?? '',
    citations: list.map(normalizeCitation),
    followUps: Array.isArray(m.follow_up_questions) ? m.follow_up_questions.filter((q) => typeof q === 'string') : [],
    createdAt: m.created_at ?? null,
  }
}

export function normalizeConversation(c) {
  return {
    id: c.id,
    title: c.title || 'Untitled conversation',
    createdAt: c.created_at ?? null,
    updatedAt: c.updated_at ?? c.created_at ?? null,
    messageCount: c.message_count ?? null,
    messages: Array.isArray(c.messages) ? c.messages.map(normalizeMessage) : undefined,
  }
}

export function normalizePage(data, mapItem, { page = 1, pageSize = 10 } = {}) {
  if (Array.isArray(data)) {
    return { items: data.map(mapItem), total: data.length, page, pageSize, pages: 1 }
  }
  const items = (data?.items ?? []).map(mapItem)
  const size = data?.page_size ?? pageSize
  const total = data?.total ?? items.length
  return {
    items,
    total,
    page: data?.page ?? page,
    pageSize: size,
    pages: data?.pages ?? Math.max(1, Math.ceil(total / size)),
  }
}
