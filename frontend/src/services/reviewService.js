import { http } from './http'
import { normalizePage, normalizeReview, normalizeReviewEntry } from './normalize'

export async function getSummary() {
  const { data } = await http.get('/reviews/summary')
  return {
    today: data.today,
    dueSoonDays: data.due_soon_days,
    scheduled: data.scheduled,
    upcoming: data.upcoming,
    due: data.due,
    overdue: data.overdue,
    inReview: data.in_review,
    completed30: data.completed_last_30_days,
    recent: (data.recent ?? []).map((r) => ({
      documentId: r.document_id,
      title: r.title,
      versionNumber: r.version_number ?? null,
      outcome: r.outcome,
      reviewedAt: r.reviewed_at,
      reviewer: r.reviewer ?? null,
    })),
  }
}

export async function listReviews({ page = 1, pageSize = 10, status, collectionId, search, assignedToMe, sort } = {}) {
  const params = { page, page_size: pageSize }
  if (status) params.status = status
  if (collectionId) params.collection_id = collectionId
  if (search) params.search = search
  if (assignedToMe) params.assigned_to_me = true
  if (sort) params.sort = sort
  const { data } = await http.get('/reviews', { params })
  return normalizePage(data, normalizeReview, { page, pageSize })
}

export async function getReview(documentId) {
  const { data } = await http.get(`/documents/${documentId}/review`)
  return normalizeReview(data)
}

export async function saveSchedule(documentId, { intervalDays, nextReviewDate, notes }) {
  const body = {}
  if (intervalDays !== undefined) body.interval_days = intervalDays
  if (nextReviewDate !== undefined) body.next_review_date = nextReviewDate
  if (notes !== undefined) body.notes = notes
  const { data } = await http.put(`/documents/${documentId}/review`, body)
  return normalizeReview(data)
}

export async function clearSchedule(documentId) {
  const { data } = await http.delete(`/documents/${documentId}/review`)
  return normalizeReview(data)
}

export async function startReview(documentId) {
  const { data } = await http.post(`/documents/${documentId}/review/start`)
  return normalizeReview(data)
}

export async function completeReview(documentId, { outcome, notes, nextReviewDate }) {
  const body = { outcome }
  if (notes) body.notes = notes
  if (nextReviewDate) body.next_review_date = nextReviewDate
  const { data } = await http.post(`/documents/${documentId}/review/complete`, body)
  return normalizeReview(data)
}

export async function getHistory(documentId, { page = 1, pageSize = 20 } = {}) {
  const { data } = await http.get(`/documents/${documentId}/review/history`, { params: { page, page_size: pageSize } })
  return normalizePage(data, normalizeReviewEntry, { page, pageSize })
}
