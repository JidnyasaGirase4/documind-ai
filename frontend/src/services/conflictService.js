import { http } from './http'
import { normalizeFinding, normalizePage, normalizeReport } from './normalize'

// Starts a background analysis of one document or one collection. Poll getReport() until it is no longer 'running'.
export async function analyze({ documentId, collectionId }) {
  const body = documentId ? { document_id: documentId } : { collection_id: collectionId }
  const { data } = await http.post('/conflicts/analyze', body)
  return normalizeReport(data)
}

export async function getReport(id) {
  const { data } = await http.get(`/conflicts/reports/${id}`)
  return normalizeReport(data)
}

export async function listFindings({ page = 1, pageSize = 10, reviewStatus, documentId, collectionId, stale } = {}) {
  const params = { page, page_size: pageSize }
  if (reviewStatus) params.review_status = reviewStatus
  if (documentId) params.document_id = documentId
  if (collectionId) params.collection_id = collectionId
  if (stale !== undefined && stale !== '') params.stale = stale
  const { data } = await http.get('/conflicts', { params })
  return normalizePage(data, normalizeFinding, { page, pageSize })
}

export async function decide(id, decision, note) {
  const { data } = await http.patch(`/conflicts/${id}/decision`, { decision, note: note || null })
  return normalizeFinding(data)
}

export async function getDecisions(id) {
  const { data } = await http.get(`/conflicts/${id}/decisions`)
  return data.map((d) => ({ id: d.id, decision: d.decision, note: d.note ?? null, decidedAt: d.decided_at, decidedBy: d.decided_by ?? null }))
}
