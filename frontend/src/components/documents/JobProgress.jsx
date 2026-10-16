import { RotateCw } from 'lucide-react'
import { Button } from '../common/Button'
import { formatRelative } from '../../utils/format'

const STAGE_LABELS = {
  extracting: 'Extracting text',
  chunking: 'Splitting into passages',
  embedding: 'Creating embeddings',
  indexing: 'Indexing',
}

// Shows what the background worker has actually reached (stage and percentage come from the stored job), never a
// made-up animation. Queued jobs show 0%; a job waiting for an automatic retry says when it will run again.
export function JobProgress({ doc, onRetry, retrying }) {
  const job = doc.job
  if (!job) return null

  if (doc.status === 'failed') {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-danger" role="alert">
        <span>{job.error || doc.error || 'Processing failed.'}</span>
        {job.attempts > 1 && (
          <span className="text-muted">
            ({job.attempts} {job.attempts === 1 ? 'attempt' : 'attempts'})
          </span>
        )}
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={() => onRetry(doc)} loading={retrying} className="!h-7 !px-2.5 !text-xs">
            <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
            Retry
          </Button>
        )}
      </div>
    )
  }

  if (doc.status !== 'queued' && doc.status !== 'processing' && doc.status !== 'uploaded') return null

  const queued = job.status === 'queued'
  const percent = queued ? 0 : Math.min(100, Math.max(0, job.progress ?? 0))
  const label = queued
    ? job.nextRunAt && job.attempts > 0
      ? `Waiting to retry ${formatRelative(job.nextRunAt)} (attempt ${job.attempts + 1} of ${job.maxAttempts})`
      : 'Waiting in the queue'
    : `${STAGE_LABELS[job.stage] ?? 'Processing'}${job.attempts > 1 ? ` · attempt ${job.attempts} of ${job.maxAttempts}` : ''}`

  return (
    <div className="mt-2" data-testid="job-progress">
      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span>{label}</span>
        <span className="tabular-nums">{percent}%</span>
      </div>
      <div
        className="mt-1 h-1.5 overflow-hidden rounded-full bg-stone-200"
        role="progressbar"
        aria-label={`Processing ${doc.filename}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <div className="h-full rounded-full bg-brand-500 transition-all duration-500" style={{ width: `${percent}%` }} />
      </div>
      {queued && job.error && job.attempts > 0 && <p className="mt-1 text-xs text-warning">{job.error}</p>}
    </div>
  )
}
