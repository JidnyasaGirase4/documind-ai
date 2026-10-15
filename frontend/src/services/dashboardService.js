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
