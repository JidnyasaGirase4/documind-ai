import { forwardRef, useId } from 'react'
import { cx } from '../../utils/format'

const CONTROL =
  'w-full rounded-control border bg-surface px-3 text-sm text-ink placeholder:text-stone-400 transition-colors disabled:bg-stone-50 disabled:text-muted'

function FieldShell({ id, label, hint, error, children, labelHidden }) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className={labelHidden ? 'sr-only' : 'mb-1.5 block text-sm font-medium text-ink'}>
          {label}
        </label>
      )}
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

function describedBy(id, hint, error) {
  if (error) return `${id}-error`
  if (hint) return `${id}-hint`
  return undefined
}

export const Input = forwardRef(function Input({ label, hint, error, labelHidden, className, id, rightSlot, leftIcon: LeftIcon, ...rest }, ref) {
  const auto = useId()
  const fid = id || auto
  return (
    <FieldShell id={fid} label={label} hint={hint} error={error} labelHidden={labelHidden}>
      <div className="relative">
        {LeftIcon && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-muted">
            <LeftIcon className="h-4 w-4" aria-hidden="true" />
          </span>
        )}
        <input
          ref={ref}
          id={fid}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(fid, hint, error)}
          className={cx(CONTROL, 'h-10', error ? 'border-danger' : 'border-line', rightSlot && 'pr-10', LeftIcon && 'pl-9', className)}
          {...rest}
        />
        {rightSlot && <div className="absolute inset-y-0 right-1 flex items-center">{rightSlot}</div>}
      </div>
    </FieldShell>
  )
})

export const Textarea = forwardRef(function Textarea({ label, hint, error, labelHidden, className, id, ...rest }, ref) {
  const auto = useId()
  const fid = id || auto
  return (
    <FieldShell id={fid} label={label} hint={hint} error={error} labelHidden={labelHidden}>
      <textarea
        ref={ref}
        id={fid}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error)}
        className={cx(CONTROL, 'py-2.5', error ? 'border-danger' : 'border-line', className)}
        {...rest}
      />
    </FieldShell>
  )
})

export const Select = forwardRef(function Select({ label, hint, error, labelHidden, className, id, children, ...rest }, ref) {
  const auto = useId()
  const fid = id || auto
  return (
    <FieldShell id={fid} label={label} hint={hint} error={error} labelHidden={labelHidden}>
      <select
        ref={ref}
        id={fid}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error)}
        className={cx(CONTROL, 'h-10', error ? 'border-danger' : 'border-line', className)}
        {...rest}
      >
        {children}
      </select>
    </FieldShell>
  )
})
