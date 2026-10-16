import { Badge } from '../common/Badge'

export const STATUS_META = {
  not_scheduled: { tone: 'neutral', label: 'Not scheduled' },
  upcoming: { tone: 'neutral', label: 'Upcoming' },
  due: { tone: 'warning', label: 'Due' },
  overdue: { tone: 'danger', label: 'Overdue' },
  in_review: { tone: 'brand', label: 'In review' },
  reviewed: { tone: 'success', label: 'Reviewed' },
}

export const OUTCOMES = {
  approved: 'Approved as current',
  changes_required: 'Changes required',
  outdated: 'Outdated content',
  needs_clarification: 'Needs clarification',
}

export function ReviewStatusBadge({ status }) {
  const m = STATUS_META[status] ?? STATUS_META.not_scheduled
  return <Badge tone={m.tone}>{m.label}</Badge>
}

export function dueText(r) {
  if (r.nextReviewDate == null) return 'No review date'
  const d = r.daysUntilDue
  if (d === 0) return 'Due today'
  if (d < 0) return `${-d} ${d === -1 ? 'day' : 'days'} overdue`
  return `Due in ${d} ${d === 1 ? 'day' : 'days'}`
}

// Calendar dates arrive as YYYY-MM-DD; show them without any time-zone shifting.
export function formatReviewDate(value) {
  if (!value) return '—'
  const [y, m, d] = value.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, { dateStyle: 'medium', timeZone: 'UTC' })
}
