import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PageHeader } from '../../components/common/PageHeader'
import { ChartCard } from '../../components/common/ChartCard'
import { ChartSkeleton } from '../../components/common/LoadingSkeleton'
import { ErrorState } from '../../components/common/ErrorState'
import { QualityPanel } from '../../components/analytics/QualityPanel'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { dashboardService } from '../../services'
import { formatDate } from '../../utils/format'

const STATUS_COLORS = { ready: '#15803d', processing: '#d4a93a', failed: '#c8281c', uploaded: '#a1a1aa', queued: '#a1a1aa' }
const STATUS_LABELS = { ready: 'Completed', processing: 'Processing', failed: 'Failed', uploaded: 'Queued', queued: 'Queued' }
const BRAND = '#8f1d3f'

const total = (rows) => rows.reduce((a, r) => a + (Number(r.count) || 0), 0)
const peak = (rows) => rows.reduce((best, r) => (!best || r.count > best.count ? r : best), null)
const day = (d) => formatDate(d, { month: 'short', day: 'numeric' })

function timeSummary(noun, rows) {
  if (!rows.length) return ''
  const p = peak(rows)
  return `${total(rows)} ${noun} across ${rows.length} days. Busiest day: ${formatDate(p.date)} with ${p.count}.`
}

export default function Analytics() {
  useDocumentTitle('Analytics')
  const { data, error, loading, reload } = useAsync(() => dashboardService.getAnalytics(), [])

  if (error) {
    return (
      <>
        <PageHeader title="Analytics" description="How you use DocuMind AI." />
        <ErrorState error={error} title="Could not load analytics" onRetry={reload} />
      </>
    )
  }

  const statuses = (data?.statuses ?? []).map((s) => ({ ...s, label: STATUS_LABELS[s.status] ?? s.status }))

  return (
    <>
      <PageHeader title="Analytics" description="How you use DocuMind AI." />
      {loading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
          <ChartSkeleton className="lg:col-span-2" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartCard
            title="Document uploads over time"
            summary={timeSummary('uploads', data.uploads)}
            columns={['Date', 'Uploads']}
            rows={data.uploads.map((r) => [formatDate(r.date), r.count])}
            empty={data.uploads.length ? null : 'No uploads recorded yet.'}
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.uploads} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8e3df" />
                <XAxis dataKey="date" tickFormatter={day} tick={{ fontSize: 14, fill: '#6b6360' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 14, fill: '#6b6360' }} />
                <Tooltip labelFormatter={(d) => formatDate(d)} />
                <Bar dataKey="count" name="Uploads" fill={BRAND} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard
            title="Processing status"
            summary={statuses.length ? statuses.map((s) => `${s.label}: ${s.count}`).join(' · ') : ''}
            columns={['Status', 'Documents']}
            rows={statuses.map((s) => [s.label, s.count])}
            empty={total(statuses) ? null : 'No documents to show yet.'}
          >
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={statuses} dataKey="count" nameKey="label" innerRadius={60} outerRadius={95} paddingAngle={2}>
                  {statuses.map((s) => (
                    <Cell key={s.status} fill={STATUS_COLORS[s.status] ?? '#94A3B8'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend formatter={(value) => <span style={{ color: '#1c181b', fontSize: 15 }}>{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          <div className="lg:col-span-2">
            <ChartCard
              title="Question activity"
              summary={timeSummary('questions', data.questions)}
              columns={['Date', 'Questions']}
              rows={data.questions.map((r) => [formatDate(r.date), r.count])}
              empty={data.questions.length ? null : 'No questions asked yet.'}
            >
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={data.questions} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8e3df" />
                  <XAxis dataKey="date" tickFormatter={day} tick={{ fontSize: 14, fill: '#6b6360' }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 14, fill: '#6b6360' }} />
                  <Tooltip labelFormatter={(d) => formatDate(d)} />
                  <Line type="monotone" dataKey="count" name="Questions" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </div>
      )}
      <QualityPanel />
    </>
  )
}
