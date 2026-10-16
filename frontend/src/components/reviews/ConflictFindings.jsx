import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ExternalLink, History as HistoryIcon } from 'lucide-react'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import { Modal } from '../common/Modal'
import { Textarea } from '../common/Field'
import { EmptyState } from '../common/EmptyState'
import { useToast } from '../../context/ToastContext'
import { conflictService } from '../../services'
import { formatDateTime } from '../../utils/format'

const TYPE = {
  value_mismatch: 'Different values',
  deadline_or_date: 'Deadline or date',
  limit_or_threshold: 'Limit or threshold',
  policy_contradiction: 'Opposite rules',
  version_change: 'Version change',
  other: 'Other',
}
const DECISION = {
  pending: { tone: 'neutral', label: 'Awaiting review' },
  confirmed: { tone: 'danger', label: 'Confirmed conflict' },
  not_conflict: { tone: 'success', label: 'Not a conflict' },
  needs_review: { tone: 'warning', label: 'Needs further review' },
}

// Opens the exact version and page the passage came from (the server finds the right file from the passage id).
export function evidenceLink(s) {
  const q = new URLSearchParams()
  if (s.page) q.set('page', s.page)
  if (s.chunkId) q.set('chunk', s.chunkId)
  if (s.versionId) q.set('version', s.versionId)
  return `/app/documents/${s.documentId}${q.toString() ? `?${q}` : ''}`
}

function Evidence({ label, s }) {
  return (
    <section aria-label={`Evidence ${label}`} className="min-w-0 rounded-control border border-line bg-stone-50 p-3">
      <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
        <span className="font-semibold text-ink">{label}</span>
        <Link to={evidenceLink(s)} className="inline-flex items-center gap-1 font-medium text-brand-700 hover:underline">
          {s.title}
          <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </Link>
        <Badge tone={s.isCurrent ? 'neutral' : 'warning'}>
          v{s.versionNumber ?? '?'}
          {s.isCurrent ? '' : ' (not current)'}
        </Badge>
        {s.page ? <span>page {s.page}</span> : null}
      </p>
      <blockquote className="mt-2 break-words border-l-4 border-amber-300 pl-3 text-sm text-stone-700">“{s.excerpt}”</blockquote>
    </section>
  )
}

function DecisionDialog({ finding, decision, onClose, onDone }) {
  const toast = useToast()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const label = DECISION[decision]?.label

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const updated = await conflictService.decide(finding.id, decision, note.trim())
      toast.success(`Recorded: ${label}.`)
      onDone(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal open onClose={busy ? () => {} : onClose} title={label} description="Your decision is recorded with your name and the time. It does not change either document.">
      <form onSubmit={submit} className="space-y-4">
        <Textarea label="Note (optional)" rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} data-autofocus />
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
            Record decision
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function History({ id }) {
  const [state, setState] = useState({ open: false, loading: false, items: null, error: null })
  const toggle = async () => {
    if (state.open) return setState((s) => ({ ...s, open: false }))
    setState((s) => ({ ...s, open: true, loading: true, error: null }))
    try {
      setState({ open: true, loading: false, items: await conflictService.getDecisions(id), error: null })
    } catch (error) {
      setState({ open: true, loading: false, items: null, error })
    }
  }
  return (
    <div className="mt-3">
      <Button size="sm" variant="ghost" aria-expanded={state.open} onClick={toggle}>
        <HistoryIcon className="h-4 w-4" aria-hidden="true" />
        Decision history
      </Button>
      {state.open && (
        <div className="mt-2 text-sm">
          {state.loading ? (
            <p className="text-muted">Loading…</p>
          ) : state.error ? (
            <p role="alert" className="text-danger">
              {state.error.message}
            </p>
          ) : state.items.length === 0 ? (
            <p className="text-muted">No decisions yet.</p>
          ) : (
            <ol className="space-y-1">
              {state.items.map((d) => (
                <li key={d.id} className="text-stone-700">
                  <strong>{DECISION[d.decision]?.label}</strong> · {d.decidedBy?.name ?? 'Former user'} · {formatDateTime(d.decidedAt)}
                  {d.note ? ` — ${d.note}` : ''}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}

export function FindingList({ findings, onChanged, emptyTitle = 'No potential conflicts', emptyText = 'Nothing has been flagged. Run an analysis to look for contradictions.' }) {
  const [deciding, setDeciding] = useState(null) // { finding, decision }
  if (findings.length === 0) return <EmptyState compact icon={AlertTriangle} title={emptyTitle} description={emptyText} />
  return (
    <>
      <ul className="space-y-4" aria-label="Potential conflicts">
        {findings.map((f) => {
          const d = DECISION[f.reviewStatus] ?? DECISION.pending
          return (
            <li key={f.id} className="rounded-card border border-line bg-surface p-4 shadow-card">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={f.assessment === 'potential_conflict' ? 'warning' : 'neutral'} icon={AlertTriangle}>
                  {f.assessment === 'potential_conflict' ? 'Potential conflict' : 'Needs human review'}
                </Badge>
                <Badge>{TYPE[f.type] ?? TYPE.other}</Badge>
                {f.kind === 'cross_version' && <Badge>Between versions</Badge>}
                {f.stale && <Badge tone="warning" title="A source document has a newer version. This finding is about the older text; run the analysis again.">Source changed · re-analyze</Badge>}
                <Badge tone={d.tone}>{d.label}</Badge>
              </div>
              <p className="mt-2 text-sm text-ink">{f.explanation}</p>
              <p className="mt-1 text-xs text-muted">
                AI-assisted suggestion{f.quotesVerified ? ' (quoted evidence matches both passages)' : ' (quoted evidence could not be verified)'}. It is not a fact until a person confirms it.
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <Evidence label="Source A" s={f.a} />
                <Evidence label="Source B" s={f.b} />
              </div>
              {f.reviewedBy && (
                <p className="mt-2 text-xs text-muted">
                  Last decision by {f.reviewedBy.name} on {formatDateTime(f.reviewedAt)}
                  {f.reviewNote ? ` — ${f.reviewNote}` : ''}
                </p>
              )}
              {f.canDecide ? (
                <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label={`Decide finding ${f.id}`}>
                  <Button size="sm" variant="secondary" onClick={() => setDeciding({ finding: f, decision: 'confirmed' })}>
                    Confirm conflict
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setDeciding({ finding: f, decision: 'not_conflict' })}>
                    Not a conflict
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setDeciding({ finding: f, decision: 'needs_review' })}>
                    Needs further review
                  </Button>
                </div>
              ) : (
                <p className="mt-3 text-xs text-muted">Only editors of both documents can record a decision.</p>
              )}
              <History id={f.id} />
            </li>
          )
        })}
      </ul>
      {deciding && (
        <DecisionDialog
          finding={deciding.finding}
          decision={deciding.decision}
          onClose={() => setDeciding(null)}
          onDone={() => {
            setDeciding(null)
            onChanged?.()
          }}
        />
      )}
    </>
  )
}
