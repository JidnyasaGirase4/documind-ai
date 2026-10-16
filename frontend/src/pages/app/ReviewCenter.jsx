import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, CalendarCheck, CalendarClock, ClipboardCheck, FileText } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { SearchInput } from '../../components/common/SearchInput'
import { Select } from '../../components/common/Field'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton, Skeleton } from '../../components/common/LoadingSkeleton'
import { Card, CardHeader } from '../../components/common/Card'
import { Badge } from '../../components/common/Badge'
import { AnalyzeButton } from '../../components/reviews/AnalyzeButton'
import { FindingList } from '../../components/reviews/ConflictFindings'
import { OUTCOMES, ReviewStatusBadge, STATUS_META, dueText, formatReviewDate } from '../../components/reviews/reviewMeta'
import { useAsync } from '../../hooks/useAsync'
import { useDebounce } from '../../hooks/useDebounce'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { knowledgeService, reviewService, conflictService } from '../../services'
import { cx, formatDateTime } from '../../utils/format'

const TABS = [
  { id: 'reviews', label: 'Content reviews' },
  { id: 'conflicts', label: 'Potential conflicts' },
]

function SummaryCard({ icon: Icon, label, value, tone = 'text-brand-700', onClick, active }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active} className={cx('w-full rounded-card border bg-surface p-4 text-left shadow-card transition hover:border-brand-200', active ? 'border-brand-400' : 'border-line')}>
      <div className="flex items-center gap-3">
        <span className="icon-tile h-10 w-10">
          <Icon className={cx('h-5 w-5', tone)} aria-hidden="true" />
        </span>
        <div>
          <p className="text-2xl font-bold text-ink">{value}</p>
          <p className="text-sm text-muted">{label}</p>
        </div>
      </div>
    </button>
  )
}

function ReviewsTab() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [collectionId, setCollectionId] = useState('')
  const [mine, setMine] = useState(false)
  const [page, setPage] = useState(1)
  const debounced = useDebounce(search, 350)
  const summary = useAsync(() => reviewService.getSummary(), [])
  const collections = useAsync(() => knowledgeService.listCollections({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' }).then((r) => r.items), [])
  const list = useAsync(() => reviewService.listReviews({ page, pageSize: 10, status, collectionId, search: debounced, assignedToMe: mine }), [page, status, collectionId, debounced, mine])
  useEffect(() => setPage(1), [status, collectionId, debounced, mine])
  const s = summary.data
  const filtered = Boolean(status || collectionId || debounced || mine)

  return (
    <>
      {summary.loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : summary.error ? (
        <ErrorState error={summary.error} onRetry={summary.reload} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Review summary">
          <SummaryCard icon={CalendarCheck} label="Scheduled documents" value={s.scheduled} onClick={() => setStatus('')} active={status === ''} />
          <SummaryCard icon={CalendarClock} label={`Due within ${s.dueSoonDays} days`} value={s.due} tone="text-warning" onClick={() => setStatus('due')} active={status === 'due'} />
          <SummaryCard icon={AlertTriangle} label="Overdue" value={s.overdue} tone="text-danger" onClick={() => setStatus('overdue')} active={status === 'overdue'} />
          <SummaryCard icon={ClipboardCheck} label="Reviews completed (30 days)" value={s.completed30} tone="text-success" onClick={() => setStatus('')} />
        </div>
      )}

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end">
        <SearchInput className="sm:flex-1" value={search} onChange={setSearch} placeholder="Search by document name" label="Search reviews by document name" />
        <Select label="Status" labelHidden value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {Object.entries(STATUS_META)
            .filter(([k]) => k !== 'not_scheduled')
            .map(([k, m]) => (
              <option key={k} value={k}>
                {m.label}
              </option>
            ))}
        </Select>
        <Select label="Collection" labelHidden value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
          <option value="">All collections</option>
          {collections.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <label className="flex h-10 items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
          Assigned to me
        </label>
      </div>

      <div className="mt-4">
        {list.loading ? (
          <ListSkeleton />
        ) : list.error ? (
          <ErrorState error={list.error} onRetry={list.reload} />
        ) : list.data.items.length === 0 ? (
          <EmptyState
            icon={CalendarClock}
            title={filtered ? 'No matching reviews' : 'No reviews scheduled yet'}
            description={filtered ? 'Try different filters.' : 'Open a document and choose "Schedule review" to start tracking when it needs to be checked.'}
          />
        ) : (
          <>
            <ul className="space-y-3" aria-label="Reviews">
              {list.data.items.map((r) => (
                <li key={r.documentId} className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4 shadow-card sm:flex-row sm:items-center">
                  <span className="icon-tile hidden h-10 w-10 sm:flex">
                    <FileText className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <Link to={`/app/documents/${r.documentId}`} className="block break-words font-medium text-ink hover:text-brand-700 hover:underline">
                      {r.title}
                    </Link>
                    <p className="mt-0.5 text-xs text-muted">
                      Version {r.versionNumber ?? '?'} · Next review {formatReviewDate(r.nextReviewDate)}
                      {r.nextReviewDate ? ` (${dueText(r).toLowerCase()})` : ''}
                      {r.assignedReviewer ? ` · Reviewer ${r.assignedReviewer.name}` : ''}
                      {r.lastReviewedAt ? ` · Last reviewed ${formatDateTime(r.lastReviewedAt)}` : ''}
                    </p>
                    {r.versionChanged && <p className="mt-0.5 text-xs font-medium text-gold-600">New version since the last review</p>}
                  </div>
                  <ReviewStatusBadge status={r.status} />
                </li>
              ))}
            </ul>
            <Pagination page={list.data.page} pages={list.data.pages} total={list.data.total} pageSize={list.data.pageSize} onChange={setPage} noun="reviews" />
          </>
        )}
      </div>

      {s && s.recent.length > 0 && (
        <Card className="mt-8">
          <CardHeader title="Recently completed reviews" />
          <ul className="divide-y divide-line" aria-label="Recently completed reviews">
            {s.recent.map((r, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <Link to={`/app/documents/${r.documentId}`} className="font-medium text-ink hover:text-brand-700 hover:underline">
                  {r.title}
                </Link>
                <Badge tone={r.outcome === 'approved' ? 'success' : r.outcome === 'outdated' ? 'danger' : 'warning'}>{OUTCOMES[r.outcome] ?? r.outcome}</Badge>
                <span className="text-xs text-muted">
                  {formatDateTime(r.reviewedAt)} · {r.reviewer?.name ?? 'Former user'}
                  {r.versionNumber ? ` · version ${r.versionNumber}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}

function ConflictsTab() {
  const [reviewStatus, setReviewStatus] = useState('')
  const [stale, setStale] = useState('')
  const [collectionId, setCollectionId] = useState('')
  const [analyzeCollection, setAnalyzeCollection] = useState('')
  const [page, setPage] = useState(1)
  const collections = useAsync(() => knowledgeService.listCollections({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' }).then((r) => r.items), [])
  const list = useAsync(() => conflictService.listFindings({ page, pageSize: 10, reviewStatus, collectionId, stale }), [page, reviewStatus, collectionId, stale])
  useEffect(() => setPage(1), [reviewStatus, collectionId, stale])
  const editable = collections.data?.filter((c) => c.role !== 'viewer') ?? []

  return (
    <>
      <Card>
        <CardHeader title="Analyze a collection" description="Looks for passages in the collection's documents that may contradict each other. Findings are suggestions: nothing is changed and nothing is confirmed automatically." />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <Select label="Collection to analyze" labelHidden value={analyzeCollection} onChange={(e) => setAnalyzeCollection(e.target.value)}>
            <option value="">Choose a collection…</option>
            {editable.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          {analyzeCollection ? <AnalyzeButton key={analyzeCollection} collectionId={Number(analyzeCollection)} label="Analyze collection" onDone={() => list.reload({ silent: true })} /> : <p className="text-sm text-muted sm:pt-2">Choose a collection you can edit.</p>}
        </div>
      </Card>

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Select label="Decision" labelHidden value={reviewStatus} onChange={(e) => setReviewStatus(e.target.value)}>
          <option value="">All decisions</option>
          <option value="pending">Awaiting review</option>
          <option value="confirmed">Confirmed conflict</option>
          <option value="not_conflict">Not a conflict</option>
          <option value="needs_review">Needs further review</option>
        </Select>
        <Select label="Freshness" labelHidden value={stale} onChange={(e) => setStale(e.target.value)}>
          <option value="">Current and outdated findings</option>
          <option value="false">Up to date</option>
          <option value="true">Source changed (re-analyze)</option>
        </Select>
        <Select label="Collection filter" labelHidden value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
          <option value="">All collections</option>
          {collections.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      <div className="mt-4">
        {list.loading ? (
          <ListSkeleton />
        ) : list.error ? (
          <ErrorState error={list.error} onRetry={list.reload} />
        ) : (
          <>
            <FindingList findings={list.data.items} onChanged={() => list.reload({ silent: true })} emptyTitle={reviewStatus || stale || collectionId ? 'No matching findings' : 'No potential conflicts'} />
            <Pagination page={list.data.page} pages={list.data.pages} total={list.data.total} pageSize={list.data.pageSize} onChange={setPage} noun="findings" />
          </>
        )}
      </div>
    </>
  )
}

export default function ReviewCenter() {
  useDocumentTitle('Reviews')
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'conflicts' ? 'conflicts' : 'reviews'
  return (
    <>
      <PageHeader title="Reviews" description="Keep content up to date and check documents for contradictions." />
      <div role="tablist" aria-label="Review sections" className="mb-5 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setParams(t.id === 'reviews' ? {} : { tab: t.id })}
            className={cx('-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors', tab === t.id ? 'border-brand-600 text-brand-700' : 'border-transparent text-muted hover:text-ink')}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === 'reviews' ? <ReviewsTab /> : <ConflictsTab />}
      </div>
    </>
  )
}
