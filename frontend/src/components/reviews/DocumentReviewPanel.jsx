import { useState } from 'react'
import { CalendarClock, CheckCircle2, PlayCircle, Trash2 } from 'lucide-react'
import { Card, CardHeader } from '../common/Card'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { Input, Select, Textarea } from '../common/Field'
import { ConfirmDialog } from '../common/ConfirmDialog'
import { ErrorState } from '../common/ErrorState'
import { ListSkeleton } from '../common/LoadingSkeleton'
import { useAsync } from '../../hooks/useAsync'
import { useToast } from '../../context/ToastContext'
import { reviewService } from '../../services'
import { formatDateTime } from '../../utils/format'
import { OUTCOMES, ReviewStatusBadge, dueText, formatReviewDate } from './reviewMeta'

const PRESETS = [30, 90, 180]
const isoToday = () => new Date().toISOString().slice(0, 10)

function ScheduleDialog({ open, review, onClose, onSave }) {
  const [interval, setInterval] = useState(String(review?.intervalDays ?? ''))
  const [date, setDate] = useState(review?.nextReviewDate ?? '')
  const [notes, setNotes] = useState(review?.notes ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const days = interval === '' ? null : Number(interval)
    if (days !== null && (!Number.isInteger(days) || days < 1 || days > 3650)) {
      setError('The interval must be a whole number of days between 1 and 3650.')
      return
    }
    if (date && date < isoToday()) {
      setError('The review date must be today or later.')
      return
    }
    if (days === null && !date) {
      setError('Choose a review date or an interval.')
      return
    }
    setBusy(true)
    try {
      await onSave({ intervalDays: days, nextReviewDate: date || undefined, notes: notes.trim() || null })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={busy ? () => {} : onClose} title="Review schedule" description="Dates are calendar dates in UTC. The status (upcoming, due, overdue) follows from the date automatically.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input label="Next review date" type="date" min={isoToday()} value={date} onChange={(e) => setDate(e.target.value)} data-autofocus />
        <div>
          <Input label="Repeat every (days)" inputMode="numeric" value={interval} onChange={(e) => setInterval(e.target.value.replace(/\D/g, ''))} hint="Used to propose the next date each time a review is completed." />
          <div className="mt-2 flex flex-wrap gap-2" aria-label="Interval presets">
            {PRESETS.map((p) => (
              <Button key={p} size="sm" variant={interval === String(p) ? 'primary' : 'secondary'} onClick={() => setInterval(String(p))}>
                {p} days
              </Button>
            ))}
          </div>
        </div>
        <Textarea label="Notes (optional)" rows={2} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {error && (
          <p role="alert" className="text-sm font-medium text-danger">
            {error}
          </p>
        )}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" loading={busy}>
            Save schedule
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function CompleteDialog({ open, review, onClose, onSave }) {
  const [outcome, setOutcome] = useState('approved')
  const [notes, setNotes] = useState('')
  const [date, setDate] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (date && date < isoToday()) {
      setError('The next review date must be today or later.')
      return
    }
    setBusy(true)
    try {
      await onSave({ outcome, notes: notes.trim(), nextReviewDate: date || undefined })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={busy ? () => {} : onClose} title="Complete review" description={`You are reviewing the current version${review?.versionNumber ? ` (version ${review.versionNumber})` : ''}. This is recorded under your name.`}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Select label="Outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)} data-autofocus>
          {Object.entries(OUTCOMES).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </Select>
        <Textarea label="Review notes (optional)" rows={3} maxLength={4000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Input
          label="Next review date (optional)"
          type="date"
          min={isoToday()}
          value={date}
          onChange={(e) => setDate(e.target.value)}
          hint={review?.intervalDays ? `Leave empty to schedule in ${review.intervalDays} days.` : 'Leave empty to schedule no further review.'}
        />
        {error && (
          <p role="alert" className="text-sm font-medium text-danger">
            {error}
          </p>
        )}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" loading={busy}>
            Record review
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// Review section of Document Details. `canManage` (owner/editor) only controls which buttons show; the API enforces it.
export function DocumentReviewPanel({ documentId, canManage }) {
  const toast = useToast()
  const review = useAsync(() => reviewService.getReview(documentId), [documentId])
  const history = useAsync(() => reviewService.getHistory(documentId, { pageSize: 10 }), [documentId])
  const [dialog, setDialog] = useState(null) // 'schedule' | 'complete' | 'clear'
  const [busy, setBusy] = useState(false)

  const refresh = () => {
    review.reload({ silent: true })
    history.reload({ silent: true })
  }

  const run = async (fn, message) => {
    setBusy(true)
    try {
      await fn()
      toast.success(message)
      setDialog(null)
      refresh()
    } catch (err) {
      toast.error(err.message)
      setDialog(null)
    } finally {
      setBusy(false)
    }
  }

  const r = review.data
  return (
    <Card>
      <CardHeader
        title="Content review"
        description="Schedule reviews and keep a record of who checked this document, when, and which version."
        action={
          canManage && r && (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" onClick={() => setDialog('schedule')}>
                <CalendarClock className="h-4 w-4" aria-hidden="true" />
                {r.nextReviewDate || r.intervalDays ? 'Edit schedule' : 'Schedule review'}
              </Button>
              {!r.inReview && (
                <Button size="sm" variant="secondary" loading={busy} onClick={() => run(() => reviewService.startReview(documentId), 'Review started.')}>
                  <PlayCircle className="h-4 w-4" aria-hidden="true" />
                  Start review
                </Button>
              )}
              <Button size="sm" onClick={() => setDialog('complete')}>
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                Complete review
              </Button>
            </div>
          )
        }
      />
      {review.loading ? (
        <ListSkeleton rows={2} />
      ) : review.error ? (
        <ErrorState error={review.error} onRetry={review.reload} />
      ) : (
        <>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted">Status</dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <ReviewStatusBadge status={r.status} />
                <span className="text-sm text-muted">{r.status === 'in_review' || r.status === 'reviewed' || r.status === 'not_scheduled' ? '' : dueText(r)}</span>
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted">Next review</dt>
              <dd className="mt-1 text-sm text-ink">
                {formatReviewDate(r.nextReviewDate)}
                {r.intervalDays ? <span className="text-muted"> · every {r.intervalDays} days</span> : null}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted">Last reviewed</dt>
              <dd className="mt-1 text-sm text-ink">
                {r.lastReviewedAt ? (
                  <>
                    {formatDateTime(r.lastReviewedAt)}
                    {r.lastReviewedBy ? ` by ${r.lastReviewedBy.name}` : ''}
                    {r.lastReviewedVersion ? ` · version ${r.lastReviewedVersion}` : ''}
                  </>
                ) : (
                  'Never'
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted">Assigned reviewer</dt>
              <dd className="mt-1 text-sm text-ink">{r.assignedReviewer?.name ?? 'Anyone with editor access'}</dd>
            </div>
          </dl>
          {r.versionChanged && (
            <p role="status" className="mt-4 rounded-control border border-gold-400/40 bg-gold-100 px-3 py-2 text-sm text-ink">
              A newer version (version {r.versionNumber}) has been uploaded since the last review (version {r.lastReviewedVersion}).
            </p>
          )}
          {r.notes && <p className="mt-3 text-sm text-ink">{r.notes}</p>}
          {canManage && (r.nextReviewDate || r.intervalDays) && (
            <Button size="sm" variant="dangerGhost" className="mt-3" onClick={() => setDialog('clear')}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Remove schedule
            </Button>
          )}

          <h3 className="mb-2 mt-6 font-display text-[15px] font-bold text-ink">Review history</h3>
          {history.loading ? (
            <ListSkeleton rows={2} />
          ) : history.error ? (
            <ErrorState error={history.error} onRetry={history.reload} />
          ) : history.data.items.length === 0 ? (
            <p className="text-sm text-muted">No reviews have been recorded yet.</p>
          ) : (
            <ol className="space-y-2" aria-label="Review history, newest first">
              {history.data.items.map((e) => (
                <li key={e.id} className="rounded-control border border-line bg-surface p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={e.outcome === 'approved' ? 'success' : e.outcome === 'outdated' ? 'danger' : 'warning'}>{OUTCOMES[e.outcome] ?? e.outcome}</Badge>
                    <span className="text-muted">
                      {formatDateTime(e.reviewedAt)} · {e.reviewer?.name ?? 'Former user'}
                      {e.versionNumber ? ` · version ${e.versionNumber}` : ''}
                    </span>
                  </div>
                  {e.notes && <p className="mt-1 text-ink">{e.notes}</p>}
                  <p className="mt-1 text-xs text-muted">Next review: {formatReviewDate(e.nextDate)}</p>
                </li>
              ))}
            </ol>
          )}
        </>
      )}

      {dialog === 'schedule' && (
        <ScheduleDialog
          open
          review={r}
          onClose={() => setDialog(null)}
          onSave={async (values) => {
            await reviewService.saveSchedule(documentId, values)
            toast.success('Review schedule saved.')
            setDialog(null)
            refresh()
          }}
        />
      )}
      {dialog === 'complete' && (
        <CompleteDialog
          open
          review={r}
          onClose={() => setDialog(null)}
          onSave={async (values) => {
            await reviewService.completeReview(documentId, values)
            toast.success('Review recorded.')
            setDialog(null)
            refresh()
          }}
        />
      )}
      <ConfirmDialog
        open={dialog === 'clear'}
        title="Remove the review schedule?"
        description="The dates and interval are cleared. Your review history is kept."
        confirmLabel="Remove schedule"
        loading={busy}
        onConfirm={() => run(() => reviewService.clearSchedule(documentId), 'Schedule removed.')}
        onCancel={() => setDialog(null)}
      />
    </Card>
  )
}
