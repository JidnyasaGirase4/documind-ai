import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { Card, CardHeader } from '../../components/common/Card'
import { Input } from '../../components/common/Field'
import { Button } from '../../components/common/Button'
import { ErrorState } from '../../components/common/ErrorState'
import { Skeleton } from '../../components/common/LoadingSkeleton'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { settingsService } from '../../services'
import { ACCEPTED_TYPE_LABEL, MAX_UPLOAD_MB } from '../../utils/config'
import { formatDate } from '../../utils/format'

export default function Settings() {
  useDocumentTitle('Settings')
  const { setUser, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const { data: profile, error, loading, reload } = useAsync(() => settingsService.getProfile(), [])
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState('')
  const [saving, setSaving] = useState(false)
  const saveRef = useRef(false)

  useEffect(() => {
    if (profile) setName(profile.name)
  }, [profile])

  const save = async (e) => {
    e.preventDefault()
    if (saveRef.current) return
    const n = name.trim()
    if (!n) return setNameError('Enter your name.')
    if (n.length > 100) return setNameError('Name must be 100 characters or fewer.')
    setNameError('')
    saveRef.current = true
    setSaving(true)
    try {
      const updated = await settingsService.updateProfile({ name: n })
      setUser((u) => ({ ...u, ...updated }))
      toast.success('Profile updated.')
      reload({ silent: true })
    } catch (err) {
      setNameError(err.message)
    } finally {
      saveRef.current = false
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Manage your profile and review how your data is handled." />
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        <div className="grid grid-cols-1 gap-4">
        <Card>
          <CardHeader title="Profile" />
          {loading ? (
            <Skeleton className="h-28 w-full" />
          ) : error ? (
            <ErrorState error={error} onRetry={reload} compact />
          ) : (
            <form onSubmit={save} noValidate className="space-y-4">
              <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} error={nameError} autoComplete="name" />
              <Input label="Email" value={profile.email} readOnly disabled hint="Your email address cannot be changed here." />
              <Button type="submit" loading={saving} disabled={name.trim() === profile.name}>
                Save changes
              </Button>
            </form>
          )}
        </Card>

        {profile && (
          <Card>
            <CardHeader title="Account information" />
            <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted">Email</dt>
                <dd className="break-all text-ink">{profile.email}</dd>
              </div>
              {profile.createdAt && (
                <div>
                  <dt className="text-muted">Member since</dt>
                  <dd className="text-ink">{formatDate(profile.createdAt)}</dd>
                </div>
              )}
            </dl>
          </Card>
        )}

        <Card>
          <CardHeader title="Session" />
          <Button
            variant="secondary"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Log out
          </Button>
        </Card>
        </div>

        <div className="grid grid-cols-1 gap-4">
        <Card>
          <CardHeader title="Uploads" />
          <p className="text-sm text-ink">
            Supported file type: <strong>{ACCEPTED_TYPE_LABEL}</strong>. Maximum size shown here: <strong>{MAX_UPLOAD_MB} MB</strong> per file.
          </p>
          <p className="mt-2 text-sm text-muted">
            PDFs need selectable text; scanned images are not processed. The server enforces the actual limits when you upload.
          </p>
        </Card>

        <Card>
          <CardHeader title="Data retention and deletion" />
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted">
            <li>Documents stay in your library until you delete them.</li>
            <li>Deleting a document removes the stored file and its indexed content.</li>
            <li>Deleting a conversation removes its messages and citations.</li>
            <li>Questions you ask are sent to an AI model together with relevant passages from your documents to generate answers.</li>
          </ul>
        </Card>

        </div>
      </div>
    </>
  )
}
