import { useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Check, Circle, Lock, Mail, ShieldCheck, User } from 'lucide-react'
import { AuthShell, FormErrorSummary } from '../../components/common/AuthShell'
import { Input } from '../../components/common/Field'
import { PasswordInput } from '../../components/common/PasswordInput'
import { Button } from '../../components/common/Button'
import { useAuth } from '../../context/AuthContext'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { PASSWORD_RULES, validateRegister } from '../../utils/validation'

const EMPTY = { name: '', email: '', password: '', confirmPassword: '' }

export default function Register() {
  useDocumentTitle('Create Account')
  const { register, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [apiError, setApiError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)

  if (isAuthenticated && !submitting) return <Navigate to="/app/dashboard" replace />

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const onSubmit = async (e) => {
    e.preventDefault()
    if (inFlight.current) return
    const v = validateRegister(form)
    setErrors(v)
    setApiError('')
    if (Object.keys(v).length) return
    inFlight.current = true
    setSubmitting(true)
    try {
      await register({ name: form.name.trim(), email: form.email.trim(), password: form.password })
      // Passwords are cleared from component state as soon as the request completes.
      setForm(EMPTY)
      navigate('/app/dashboard', { replace: true })
    } catch (err) {
      setApiError(err.message)
      setForm((f) => ({ ...f, password: '', confirmPassword: '' }))
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start asking questions about your documents."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-brand-700 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormErrorSummary errors={errors} apiError={apiError} />
        <Input label="Name" leftIcon={User} autoComplete="name" value={form.name} onChange={set('name')} error={errors.name} />
        <Input label="Email" leftIcon={Mail} type="email" autoComplete="email" value={form.email} onChange={set('email')} error={errors.email} />
        <div>
          <PasswordInput label="Password" leftIcon={Lock} autoComplete="new-password" value={form.password} onChange={set('password')} error={errors.password} />
          <ul className="mt-2 space-y-1" aria-label="Password requirements">
            {PASSWORD_RULES.map((r) => {
              const ok = r.test(form.password)
              return (
                <li key={r.id} className={`flex items-center gap-1.5 text-xs ${ok ? 'text-success' : 'text-muted'}`}>
                  {ok ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Circle className="h-3.5 w-3.5" aria-hidden="true" />}
                  {r.label}
                  <span className="sr-only">{ok ? ' (met)' : ' (not met)'}</span>
                </li>
              )
            })}
          </ul>
        </div>
        <PasswordInput
          label="Confirm password"
          leftIcon={ShieldCheck}
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={set('confirmPassword')}
          error={errors.confirmPassword}
        />
        <Button type="submit" loading={submitting} className="w-full">
          {submitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthShell>
  )
}
