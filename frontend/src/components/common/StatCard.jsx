import { cx } from '../../utils/format'

const TONES = {
  brand: { card: 'from-brand-50 to-white border-brand-100', chip: 'bg-gradient-to-br from-brand-500 to-brand-700', ring: 'bg-brand-200/40' },
  success: { card: 'from-emerald-50 to-white border-emerald-100', chip: 'bg-gradient-to-br from-emerald-500 to-emerald-700', ring: 'bg-emerald-200/40' },
  warning: { card: 'from-amber-50 to-white border-amber-100', chip: 'bg-gradient-to-br from-amber-400 to-amber-600', ring: 'bg-amber-200/40' },
  danger: { card: 'from-red-50 to-white border-red-100', chip: 'bg-gradient-to-br from-red-500 to-red-700', ring: 'bg-red-200/40' },
}

export function StatCard({ label, value, icon: Icon, tone = 'brand', loading, delay = 0 }) {
  const t = TONES[tone]
  return (
    <div
      className={cx('hover-lift relative animate-fade-in-up overflow-hidden rounded-card border bg-gradient-to-br p-4 shadow-card', t.card)}
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className={cx('absolute -bottom-6 -right-6 h-24 w-24 rounded-full', t.ring)} aria-hidden="true" />
      <div className="relative flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[15px] font-medium text-muted">{label}</p>
          {loading ? (
            <div className="skeleton mt-2 h-8 w-12" aria-label="Loading" />
          ) : (
            <p className="mt-0.5 font-display text-2xl font-bold tabular-nums text-ink">{value}</p>
          )}
        </div>
        <span className={cx('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white shadow-card', t.chip)}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>
    </div>
  )
}
