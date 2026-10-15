import { AlertCircle, RotateCw, WifiOff } from 'lucide-react'
import { Button } from './Button'

// `error` is an ApiError (or any Error). Retry is offered whenever a handler is given.
export function ErrorState({ error, title, onRetry, compact }) {
  const offline = error?.code === 'NETWORK_ERROR'
  const Icon = offline ? WifiOff : AlertCircle
  return (
    <div
      role="alert"
      className={`flex flex-col items-center rounded-card border border-danger/20 bg-danger-soft text-center ${compact ? 'px-4 py-6' : 'px-6 py-10'}`}
    >
      <Icon className="mb-3 h-7 w-7 text-danger" aria-hidden="true" />
      <h3 className="text-base font-semibold text-ink">{title || (offline ? 'Cannot connect to the server' : 'Something went wrong')}</h3>
      <p className="mt-1 max-w-md text-sm text-stone-700">{error?.message || 'An unexpected error occurred.'}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => onRetry()}>
          <RotateCw className="h-4 w-4" aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  )
}
