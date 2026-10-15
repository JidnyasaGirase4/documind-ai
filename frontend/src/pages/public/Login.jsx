import { useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Lock, Mail } from 'lucide-react'
import { AuthShell, FormErrorSummary } from '../../components/common/AuthShell'
import { Input } from '../../components/common/Field'
import { PasswordInput } from '../../components/common/PasswordInput'
import { Button } from '../../components/common/Button'
import { useAuth } from '../../context/AuthContext'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { validateLogin } from '../../utils/validation'

export default function Login() {
  useDocumentTitle('Log In')
  const { login, isAuthenticated, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = location.state?.from || '/app/dashboard'

  const [form, setForm] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [apiError, setApiError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)

  if (isAuthenticated && !submitting) return <Navigate to={redirectTo} replace />

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const onSubmit = async (e) => {
    e.preventDefault()
    if (inFlight.current) return
    const v = validateLogin(form)
    setErrors(v)
    setApiError('')
    if (Object.keys(v).length) return
    inFlight.current = true
    setSubmitting(true)
    try {
      await login({ email: form.email.trim(), password: form.password })
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setApiError(err.message)
      setForm((f) => ({ ...f, password: '' }))
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to your DocuMind AI account."
      footer={
        <>
          New to DocuMind AI?{' '}
          <Link to="/register" className="font-medium text-brand-700 hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      {sessionExpired && !apiError && (
        <p role="status" className="mb-4 rounded-control bg-warning-soft p-3 text-sm text-warning">
          Your session has ended. Please log in again.
        </p>
      )}
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormErrorSummary errors={errors} apiError={apiError} />
        <Input label="Email" leftIcon={Mail} placeholder="you@example.com" type="email" autoComplete="email" value={form.email} onChange={set('email')} error={errors.email} />
        <PasswordInput label="Password" leftIcon={Lock} placeholder="Your password" value={form.password} onChange={set('password')} error={errors.password} />
        <Button type="submit" loading={submitting} className="w-full">
          {submitting ? 'Logging in…' : 'Log In'}
        </Button>
      </form>
    </AuthShell>
  )
}
