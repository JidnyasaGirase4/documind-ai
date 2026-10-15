import { AnimatedHeading } from '../../components/common/AnimatedHeading'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, FileText, Loader2, MessageSquareText, Upload } from 'lucide-react'
import { StatCard } from '../../components/common/StatCard'
import { Card, CardHeader } from '../../components/common/Card'
import { Button } from '../../components/common/Button'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton } from '../../components/common/LoadingSkeleton'
import { DocumentStatusBadge } from '../../components/documents/DocumentStatusBadge'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useAuth } from '../../context/AuthContext'
import { conversationService, dashboardService, documentService } from '../../services'
import { formatBytes, formatRelative } from '../../utils/format'

function ProcessingOverview({ stats }) {
  const parts = [
    { key: 'ready', label: 'Ready', value: stats.ready, cls: 'bg-success' },
    { key: 'processing', label: 'Processing', value: stats.processing, cls: 'bg-warning' },
    { key: 'failed', label: 'Failed', value: stats.failed, cls: 'bg-danger' },
  ]
  const sum = parts.reduce((a, p) => a + p.value, 0)
  if (!sum) return <p className="text-sm text-muted">No documents have been processed yet.</p>
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full bg-stone-100" role="img" aria-label={parts.map((p) => `${p.label}: ${p.value}`).join(', ')}>
        {parts.map((p) => p.value > 0 && <div key={p.key} className={p.cls} style={{ width: `${(p.value / sum) * 100}%` }} />)}
      </div>
      <ul className="mt-4 grid grid-cols-3 gap-3 text-sm">
        {parts.map((p) => (
          <li key={p.key}>
            <span className="flex items-center gap-1.5 text-muted">
              <span className={`h-2.5 w-2.5 rounded-full ${p.cls}`} aria-hidden="true" />
              {p.label}
            </span>
            <span className="text-lg font-semibold tabular-nums text-ink">{p.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Dashboard() {
  useDocumentTitle('Dashboard')
  const { user } = useAuth()
  const stats = useAsync(() => dashboardService.getStats(), [])
  const activity = useAsync(() => dashboardService.getActivity(), [])
  const docs = useAsync(() => documentService.listDocuments({ pageSize: 5, sortBy: 'created_at', sortOrder: 'desc' }), [])
  const convs = useAsync(() => conversationService.listConversations({ pageSize: 5 }), [])

  const s = stats.data

  return (
    <>
      <section className="relative mb-5 overflow-hidden rounded-2xl bg-gradient-to-br from-plum-800 via-plum-900 to-plum-950 p-5 text-white shadow-lift sm:p-6">
        <div className="pointer-events-none absolute -right-10 -top-16 h-56 w-56 animate-blob rounded-full bg-brand-600/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 left-1/3 h-48 w-48 animate-blob rounded-full bg-gold-400/15 blur-3xl [animation-delay:-6s]" />
        <div className="dot-grid pointer-events-none absolute inset-0 opacity-20 invert" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-gold-400">Dashboard</p>
            <AnimatedHeading as="h1" tone="dark" text={user?.name ? `Welcome back, ${user.name.split(' ')[0]}` : 'Welcome back'} highlight={user?.name ? user.name.split(' ')[0] : undefined} className="mt-1 break-words text-xl font-bold sm:text-2xl" />
            <p className="mt-1 text-sm text-plum-100">An overview of your documents and conversations.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button to="/app/documents" variant="glass">
              <Upload className="h-4 w-4" aria-hidden="true" />
              Upload PDF
            </Button>
            <Button to="/app/assistant">
              <MessageSquareText className="h-4 w-4" aria-hidden="true" />
              Ask a Question
            </Button>
          </div>
        </div>
      </section>

      {stats.error ? (
        <ErrorState error={stats.error} title="Could not load your statistics" onRetry={stats.reload} compact />
      ) : (
        <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total documents" value={s?.total} icon={FileText} loading={stats.loading} />
          <StatCard label="Ready" value={s?.ready} icon={CheckCircle2} tone="success" loading={stats.loading} />
          <StatCard label="Processing" value={s?.processing} icon={Loader2} tone="warning" loading={stats.loading} />
          <StatCard label="Failed" value={s?.failed} icon={AlertTriangle} tone="danger" loading={stats.loading} />
        </div>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Recent uploads"
            action={
              <Link to="/app/documents" className="text-sm font-medium text-brand-700 hover:underline">
                View all
              </Link>
            }
          />
          {docs.loading ? (
            <ListSkeleton rows={3} />
          ) : docs.error ? (
            <ErrorState error={docs.error} onRetry={docs.reload} compact />
          ) : docs.data.items.length === 0 ? (
            <EmptyState
              compact
              icon={FileText}
              title="No documents yet"
              description="Upload a PDF to start asking questions about it."
              action={<Button to="/app/documents">Upload your first PDF</Button>}
            />
          ) : (
            <ul className="divide-y divide-line">
              {docs.data.items.map((d) => (
                <li key={d.id} className="flex items-center gap-3 py-3">
                  <FileText className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <Link to={`/app/documents/${d.id}`} className="block truncate text-sm font-medium text-ink hover:text-brand-700 hover:underline">
                      {d.filename}
                    </Link>
                    <p className="text-xs text-muted">
                      {formatBytes(d.size)} · {formatRelative(d.createdAt)}
                    </p>
                  </div>
                  <DocumentStatusBadge status={d.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="Processing overview" />
          {stats.loading ? <div className="skeleton h-24 w-full" /> : s ? <ProcessingOverview stats={s} /> : null}
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Recent conversations"
            action={
              <Link to="/app/history" className="text-sm font-medium text-brand-700 hover:underline">
                View all
              </Link>
            }
          />
          {convs.loading ? (
            <ListSkeleton rows={3} />
          ) : convs.error ? (
            <ErrorState error={convs.error} onRetry={convs.reload} compact />
          ) : convs.data.items.length === 0 ? (
            <EmptyState
              compact
              icon={MessageSquareText}
              title="No conversations yet"
              description="Ask your first question to start a conversation."
              action={<Button to="/app/assistant">Ask a question</Button>}
            />
          ) : (
            <ul className="divide-y divide-line">
              {convs.data.items.map((c) => (
                <li key={c.id}>
                  <Link to={`/app/assistant/${c.id}`} className="flex items-center gap-3 py-3 hover:text-brand-700">
                    <MessageSquareText className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">{c.title}</span>
                    <span className="shrink-0 text-xs text-muted">{formatRelative(c.updatedAt)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="Recent activity" />
          {activity.loading ? (
            <ListSkeleton rows={2} />
          ) : activity.error ? (
            <ErrorState error={activity.error} onRetry={activity.reload} compact />
          ) : activity.data.length === 0 ? (
            <p className="text-sm text-muted">No recent activity.</p>
          ) : (
            <ul className="space-y-3">
              {activity.data.slice(0, 6).map((a) => (
                <li key={a.id} className="text-sm">
                  <p className="text-ink">{a.title}</p>
                  <p className="text-xs text-muted">{formatRelative(a.timestamp)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
