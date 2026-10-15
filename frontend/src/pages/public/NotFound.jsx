import { Button } from '../../components/common/Button'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'

export default function NotFound() {
  useDocumentTitle('Page not found')
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-sm font-semibold text-brand-600">404</p>
      <h1 className="mt-2 text-2xl font-bold text-ink">Page not found</h1>
      <p className="mt-2 text-muted">The page you are looking for does not exist or has moved.</p>
      <Button to="/" className="mt-6">
        Back to home
      </Button>
    </div>
  )
}
