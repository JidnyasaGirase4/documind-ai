import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react'
import { Badge } from '../common/Badge'

export const STATUS_META = {
  uploaded: { label: 'Queued', tone: 'neutral', icon: Clock },
  queued: { label: 'Queued', tone: 'neutral', icon: Clock },
  processing: { label: 'Processing', tone: 'warning', icon: Loader2 },
  ready: { label: 'Completed', tone: 'success', icon: CheckCircle2 },
  failed: { label: 'Failed', tone: 'danger', icon: XCircle },
}

export function isInProgress(status) {
  return status === 'uploaded' || status === 'queued' || status === 'processing'
}

export function DocumentStatusBadge({ status }) {
  const meta = STATUS_META[status] ?? { label: status, tone: 'neutral', icon: Clock }
  const Icon = meta.icon
  return (
    <Badge tone={meta.tone}>
      <Icon className={`h-3 w-3 ${status === 'processing' ? 'animate-spin' : ''}`} aria-hidden="true" />
      {meta.label}
    </Badge>
  )
}
