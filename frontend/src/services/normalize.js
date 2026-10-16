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

export function normalizeJob(j) {
  if (!j) return null
  return {
    id: j.id,
    status: j.status,
    stage: j.stage ?? null,
    progress: j.progress ?? 0,
    attempts: j.attempts ?? 0,
    maxAttempts: j.max_attempts ?? 3,
    retryCount: j.retry_count ?? 0,
    error: j.error_message ?? null,
    errorCode: j.error_code ?? null,
    nextRunAt: j.next_run_at ?? null,
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
    job: normalizeJob(d.job),
    category: d.category ? { id: d.category.id, name: d.category.name } : null,
    tags: Array.isArray(d.tags) ? d.tags.map((t) => ({ id: t.id, name: t.name })) : [],
    collectionIds: Array.isArray(d.collection_ids) ? d.collection_ids : [],
    versionNumber: d.version_number ?? null,
    role: d.role ?? 'owner',
    isOwner: d.is_owner ?? true,
  }
}

export function normalizeVersion(v) {
  return {
    id: v.id,
    documentId: v.document_id,
    number: v.version_number,
    filename: v.original_filename,
    size: v.file_size,
    checksum: v.checksum_sha256 ?? null,
    pages: v.total_pages ?? null,
    status: v.processing_status,
    error: v.processing_error ?? null,
    isCurrent: Boolean(v.is_current),
    note: v.change_note ?? null,
    restoredFrom: v.restored_from_version_number ?? null,
    uploadedBy: v.uploaded_by ? { id: v.uploaded_by.id, name: v.uploaded_by.name } : null,
    createdAt: v.created_at ?? null,
    progress: v.progress ?? null,
  }
}

export function normalizeComparison(c) {
  const side = (s) => ({ id: s.id, number: s.version_number, createdAt: s.created_at, isCurrent: Boolean(s.is_current), status: s.processing_status })
  return {
    documentId: c.document_id,
    from: side(c.from_version),
    to: side(c.to_version),
    comparable: Boolean(c.comparable),
    reason: c.reason ?? null,
    stats: c.stats ?? { added: 0, removed: 0, changed: 0, unchanged: 0, identical: false },
    blocks: c.blocks ?? [],
    notice: c.notice ?? '',
  }
}

const person = (p) => (p ? { id: p.id, name: p.name } : null)

export function normalizeReview(r) {
  return {
    documentId: r.document_id,
    title: r.title,
    versionNumber: r.version_number ?? null,
    status: r.status,
    intervalDays: r.interval_days ?? null,
    nextReviewDate: r.next_review_date ?? null,
    daysUntilDue: r.days_until_due ?? null,
    assignedReviewer: person(r.assigned_reviewer),
    notes: r.notes ?? null,
    inReview: Boolean(r.in_review),
    lastReviewedAt: r.last_reviewed_at ?? null,
    lastReviewedBy: person(r.last_reviewed_by),
    lastOutcome: r.last_outcome ?? null,
    lastReviewedVersion: r.last_reviewed_version_number ?? null,
    versionChanged: Boolean(r.version_changed_since_review),
    role: r.role ?? 'viewer',
  }
}

export function normalizeReviewEntry(e) {
  return {
    id: e.id,
    documentId: e.document_id,
    versionNumber: e.version_number ?? null,
    reviewer: person(e.reviewer),
    reviewedAt: e.reviewed_at,
    outcome: e.outcome,
    notes: e.notes ?? null,
    previousDate: e.previous_next_review_date ?? null,
    nextDate: e.next_review_date ?? null,
  }
}

const source = (s) => ({
  documentId: s.document_id,
  title: s.title,
  versionId: s.version_id ?? null,
  versionNumber: s.version_number ?? null,
  isCurrent: Boolean(s.is_current_version),
  page: s.page ?? null,
  chunkId: s.chunk_id ?? null,
  excerpt: s.excerpt,
})

export function normalizeFinding(f) {
  return {
    id: f.id,
    reportId: f.report_id,
    kind: f.kind,
    type: f.conflict_type,
    assessment: f.assessment,
    explanation: f.explanation,
    quotesVerified: Boolean(f.quotes_verified),
    a: source(f.source_a),
    b: source(f.source_b),
    stale: Boolean(f.stale),
    reviewStatus: f.review_status,
    reviewedBy: person(f.reviewed_by),
    reviewedAt: f.reviewed_at ?? null,
    reviewNote: f.review_note ?? null,
    detectedAt: f.detected_at,
    canDecide: Boolean(f.can_decide),
  }
}

export function normalizeReport(r) {
  return {
    id: r.id,
    status: r.status,
    passages: r.passages_examined ?? 0,
    pairs: r.pairs_examined ?? 0,
    unparsed: r.pairs_unparsed ?? 0,
    compatible: r.pairs_compatible ?? 0,
    created: r.findings_created ?? 0,
    errorCode: r.error_code ?? null,
    error: r.error_message ?? null,
  }
}

export function normalizeCollection(c) {
  return {
    id: c.id,
    name: c.name,
    description: c.description ?? '',
    color: c.color ?? null,
    icon: c.icon ?? null,
    documentCount: c.document_count ?? 0,
    role: c.role ?? 'owner',
    ownerName: c.owner_name ?? null,
    isShared: Boolean(c.is_shared),
    memberCount: c.member_count ?? 0,
    createdAt: c.created_at ?? null,
    updatedAt: c.updated_at ?? null,
  }
}

export function normalizeMember(m) {
  return { userId: m.user_id, name: m.name, email: m.email, role: m.role, addedAt: m.added_at ?? null }
}

export function normalizeLabel(l) {
  return { id: l.id, name: l.name, description: l.description ?? '', documentCount: l.document_count ?? 0 }
}

export function normalizeCitation(c) {
  return {
    documentId: c.document_id ?? null,
    documentName: c.document_name ?? c.original_filename ?? c.filename ?? null,
    page: c.page_number ?? c.page ?? null,
    excerpt: c.excerpt ?? c.text ?? null,
    chunkId: c.chunk_id ?? null,
    versionId: c.version_id ?? null,
    versionNumber: c.version_number ?? null,
    versionIsCurrent: c.version_is_current ?? null,
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
    feedback: m.feedback ? { rating: m.feedback.rating, category: m.feedback.category ?? null, comment: m.feedback.comment ?? null } : null,
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
