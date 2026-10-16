import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Info } from 'lucide-react'
import { Card, CardHeader } from '../common/Card'
import { ChartCard } from '../common/ChartCard'
import { ErrorState } from '../common/ErrorState'
import { Skeleton } from '../common/LoadingSkeleton'
import { Badge } from '../common/Badge'
import { useAsync } from '../../hooks/useAsync'
import { dashboardService } from '../../services'
import { formatDate, formatDateTime } from '../../utils/format'

const BRAND = '#8f1d3f'
const GOOD = '#15803d'
const BAD = '#c8281c'
const day = (d) => formatDate(d, { month: 'short', day: 'numeric' })
const pct = (v) => (v == null ? '—' : `${Math.round(v * 100)}%`)
const ms = (v) => (v == null ? '—' : v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`)

const KIND = {
  measured: { label: 'Measured', tone: 'success', help: 'Counted or timed directly from stored data.' },
  automated_estimate: { label: 'Automated estimate', tone: 'warning', help: 'Computed by a simple automatic check (word overlap), not a human or model judgement.' },
  llm_judge: { label: 'LLM judgement', tone: 'warning', help: 'Scored by a language model; can be wrong.' },
}

const METRIC_LABELS = [
  ['precision_at_k', 'Precision@K', pct],
  ['recall_at_k', 'Recall@K', pct],
  ['citation_correctness', 'Citation correctness', pct],
  ['faithfulness', 'Answer faithfulness', pct],
  ['keyword_recall', 'Expected-keyword recall', pct],
  ['correct_abstention_rate', 'Correct "not enough evidence"', pct],
  ['latency_ms_p50', 'Latency p50', ms],
  ['latency_ms_p95', 'Latency p95', ms],
  ['failure_rate', 'Failure rate', pct],
]

function Stat({ label, value, note }) {
  return (
    <div className="rounded-control border border-line bg-surface p-3">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-0.5 font-display text-xl font-bold tabular-nums text-ink">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
    </div>
  )
}

function Section({ state, children, skeleton = 'h-40' }) {
  if (state.loading) return <Skeleton className={`${skeleton} w-full`} />
  if (state.error) return <ErrorState error={state.error} title="Could not load this section" onRetry={state.reload} />
  return children
}

export function QualityPanel() {
  const feedback = useAsync(() => dashboardService.getFeedbackStats(), [])
  const queries = useAsync(() => dashboardService.getQueryStats(), [])
  const evals = useAsync(() => dashboardService.getEvaluations(), [])

  return (
    <section aria-labelledby="quality-heading" className="mt-8 space-y-4">
      <div>
        <h2 id="quality-heading" className="font-display text-lg font-bold text-ink">
          Answer quality
        </h2>
        <p className="mt-0.5 flex items-start gap-1.5 text-sm text-muted">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>
            Each figure is labelled by how it was obtained: <b>Measured</b> values are counted or timed from stored data;{' '}
            <b>Automated estimate</b> values come from a simple automatic check and are not a human judgement.
          </span>
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Your feedback on answers" description={`Last ${feedback.data?.days ?? 30} days · measured`} />
          <Section state={feedback}>
            {feedback.data?.total ? (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <Stat label="Helpful" value={feedback.data.up} />
                  <Stat label="Not helpful" value={feedback.data.down} />
                  <Stat label="Satisfaction" value={pct(feedback.data.satisfaction)} note={`of ${feedback.data.total} rated`} />
                </div>
                {feedback.data.down_categories.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-ink">Reasons given for thumbs-down</h3>
                    <ul className="mt-1 space-y-1 text-sm">
                      {feedback.data.down_categories.map((c) => (
                        <li key={c.category} className="flex justify-between gap-2 border-b border-line py-1">
                          <span>{c.category.replace(/_/g, ' ')}</span>
                          <span className="tabular-nums text-muted">{c.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {feedback.data.recent_comments.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-ink">Recent comments</h3>
                    <ul className="mt-1 space-y-2">
                      {feedback.data.recent_comments.map((c) => (
                        <li key={`${c.message_id}-${c.created_at}`} className="rounded-control bg-stone-50 p-2 text-sm">
                          <span className="block break-words">{c.comment}</span>
                          <span className="text-xs text-muted">
                            {c.rating === 'down' ? 'Thumbs-down' : 'Thumbs-up'} · {formatDateTime(c.created_at)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <p className="py-8 text-center text-sm text-muted">No feedback yet. Use the thumbs on an answer in the AI Assistant.</p>
            )}
          </Section>
        </Card>

        <Card>
          <CardHeader title="Your questions: outcomes and speed" description={`Last ${queries.data?.days ?? 30} days · measured from the query log`} />
          <Section state={queries}>
            {queries.data?.total_questions ? (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Stat label="Questions" value={queries.data.total_questions} />
                  <Stat label="Failure rate" value={pct(queries.data.failure_rate)} note={`${queries.data.errors} errors`} />
                  <Stat label="Not enough evidence" value={pct(queries.data.insufficient_rate)} note={`${queries.data.insufficient_evidence} questions`} />
                  <Stat label="Latency p50" value={ms(queries.data.latency_ms.p50)} />
                  <Stat label="Latency p95" value={ms(queries.data.latency_ms.p95)} />
                  <Stat label="Slowest" value={ms(queries.data.latency_ms.max)} />
                </div>
                {queries.data.failure_categories.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-ink">Why questions were not answered</h3>
                    <ul className="mt-1 space-y-1 text-sm">
                      {queries.data.failure_categories.map((c) => (
                        <li key={c.category} className="flex justify-between gap-2 border-b border-line py-1">
                          <span>{c.label}</span>
                          <span className="tabular-nums text-muted">{c.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <p className="py-8 text-center text-sm text-muted">No questions recorded yet.</p>
            )}
          </Section>
        </Card>
      </div>

      {queries.data?.latency_ms.count > 0 && (
        <ChartCard
          title="Average answer time per day"
          summary={`Average of ${queries.data.latency_ms.count} answered questions: ${ms(queries.data.latency_ms.avg)}.`}
          columns={['Date', 'Average (ms)', 'Questions']}
          rows={queries.data.latency_by_day.filter((r) => r.count).map((r) => [formatDate(r.date), r.avg_ms, r.count])}
        >
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={queries.data.latency_by_day} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8e3df" />
              <XAxis dataKey="date" tickFormatter={day} tick={{ fontSize: 13, fill: '#6b6360' }} />
              <YAxis tick={{ fontSize: 13, fill: '#6b6360' }} />
              <Tooltip labelFormatter={(d) => formatDate(d)} formatter={(v) => [ms(v), 'Average']} />
              <Line type="monotone" dataKey="avg_ms" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      {feedback.data?.total > 0 && (
        <ChartCard
          title="Feedback per day"
          summary={`${feedback.data.up} helpful and ${feedback.data.down} not helpful in the last ${feedback.data.days} days.`}
          columns={['Date', 'Helpful', 'Not helpful']}
          rows={feedback.data.by_day.filter((r) => r.up || r.down).map((r) => [formatDate(r.date), r.up, r.down])}
        >
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={feedback.data.by_day} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8e3df" />
              <XAxis dataKey="date" tickFormatter={day} tick={{ fontSize: 13, fill: '#6b6360' }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 13, fill: '#6b6360' }} />
              <Tooltip labelFormatter={(d) => formatDate(d)} />
              <Bar dataKey="up" name="Helpful" stackId="f" fill={GOOD} />
              <Bar dataKey="down" name="Not helpful" stackId="f" fill={BAD} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}

      <Card>
        <CardHeader
          title="RAG evaluation"
          description="Repeatable test of retrieval and answering on a fixed synthetic dataset (not your documents)."
        />
        <Section state={evals}>
          {evals.data?.latest ? (
            <EvaluationSummary run={evals.data.latest} history={evals.data.history} />
          ) : (
            <div className="rounded-control bg-stone-50 p-4 text-sm text-ink">
              <p className="font-medium">No evaluation has been run yet.</p>
              <p className="mt-1 text-muted">
                Run one from the backend folder: <code className="rounded bg-stone-200 px-1">python -m app.eval_cli</code>. Results will appear here. Nothing is shown until a real run exists.
              </p>
            </div>
          )}
        </Section>
      </Card>
    </section>
  )
}

function EvaluationSummary({ run, history }) {
  const m = run.metrics ?? {}
  const shown = METRIC_LABELS.filter(([key]) => m[key])
  return (
    <div>
      <p className="text-sm text-muted">
        Run #{run.id} · {formatDateTime(run.finished_at ?? run.started_at)} · dataset {run.dataset_name} v{run.dataset_version} ({m.questions} questions) · K = {run.k} ·{' '}
        {run.mode === 'full' ? 'retrieval and answers' : 'retrieval only (no LLM configured, so answer metrics are not available)'}
      </p>
      <p className="mt-1 text-xs text-muted">
        Embeddings: {run.config?.embedding_model ?? '—'} · LLM: {run.config?.llm_model || run.config?.llm_provider || 'not used'}
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map(([key, label, fmt]) => {
          const metric = m[key]
          const kind = KIND[metric.kind] ?? KIND.measured
          return (
            <div key={key} className="rounded-control border border-line bg-surface p-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
                <Badge tone={kind.tone} className="shrink-0" title={kind.help}>
                  {kind.label}
                </Badge>
              </div>
              <p className="mt-0.5 font-display text-xl font-bold tabular-nums text-ink">{fmt(metric.value)}</p>
              <p className="mt-0.5 text-xs text-muted">
                n = {metric.n}
                {metric.note ? ` · ${metric.note}` : ''}
              </p>
            </div>
          )
        })}
      </div>
      {history.length > 1 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-medium text-brand-700">Previous runs ({history.length - 1})</summary>
          <ul className="mt-2 space-y-1">
            {history.filter((r) => r.id !== run.id).map((r) => (
              <li key={r.id} className="flex flex-wrap justify-between gap-2 border-b border-line py-1">
                <span>
                  #{r.id} · {formatDateTime(r.started_at)} · {r.status}
                </span>
                <span className="tabular-nums text-muted">
                  P@K {pct(r.metrics?.precision_at_k?.value)} · R@K {pct(r.metrics?.recall_at_k?.value)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
