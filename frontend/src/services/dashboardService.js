import { http } from './http'

export async function getStats() {
  const { data } = await http.get('/dashboard/stats')
  return {
    total: data.total_documents ?? 0,
    ready: data.ready_documents ?? 0,
    processing: data.processing_documents ?? 0,
    failed: data.failed_documents ?? 0,
  }
}

// Optional feed of recent events: [{ type, title, timestamp }] (array or { items }).
export async function getActivity() {
  const { data } = await http.get('/dashboard/activity')
  const items = Array.isArray(data) ? data : (data?.items ?? [])
  return items.map((a, i) => ({
    id: a.id ?? i,
    type: a.type ?? 'event',
    title: a.title ?? a.description ?? '',
    timestamp: a.timestamp ?? a.created_at ?? null,
  }))
}

export async function getAnalytics() {
  const { data } = await http.get('/analytics/overview')
  return {
    uploads: data.uploads_over_time ?? [],
    statuses: data.status_distribution ?? [],
    questions: data.question_activity ?? [],
  }
}

// Measured from the caller's own stored feedback.
export async function getFeedbackStats() {
  const { data } = await http.get('/analytics/feedback')
  return data
}

// Measured from the caller's own query log (outcomes, latency percentiles, failure categories).
export async function getQueryStats() {
  const { data } = await http.get('/analytics/queries')
  return data
}

// Evaluation runs on the synthetic dataset: { latest, history }. Each metric carries a `kind`.
export async function getEvaluations() {
  const { data } = await http.get('/analytics/evaluations')
  return data
}

export async function getEvaluationRun(id) {
  const { data } = await http.get(`/analytics/evaluations/${id}`)
  return data
}
