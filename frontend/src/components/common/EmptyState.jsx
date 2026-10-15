export function EmptyState({ icon: Icon, title, description, action, compact }) {
  return (
    <div className={`flex animate-fade-in-up flex-col items-center text-center ${compact ? 'px-4 py-6' : 'px-6 py-10'}`}>
      {Icon && (
        <span className="relative mb-5">
          <span className="absolute inset-0 -m-3 rounded-full bg-brand-100/60 blur-xl" aria-hidden="true" />
          <span className="icon-tile relative h-12 w-12">
            <Icon className="h-6 w-6" aria-hidden="true" />
          </span>
        </span>
      )}
      <h3 className="font-display text-base font-bold text-ink">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-[15px] text-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
