import { cx } from '../../utils/format'

export function Card({ as: Tag = 'div', className, padded = true, interactive = false, children, ...rest }) {
  return (
    <Tag
      className={cx(
        'min-w-0 rounded-card border border-line bg-surface shadow-card',
        padded && 'p-4 sm:p-5',
        interactive && 'hover-lift hover:border-brand-200',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  )
}

export function CardHeader({ title, description, action, as: Heading = 'h2' }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <Heading className="font-display text-[17px] font-bold text-ink">{title}</Heading>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}
