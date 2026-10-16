import { useState } from 'react'
import { Crown, LogOut, UserMinus, UserPlus, Users } from 'lucide-react'
import { Card, CardHeader } from '../common/Card'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { Input, Select } from '../common/Field'
import { ConfirmDialog } from '../common/ConfirmDialog'
import { EmptyState } from '../common/EmptyState'
import { ErrorState } from '../common/ErrorState'
import { ListSkeleton } from '../common/LoadingSkeleton'
import { useAsync } from '../../hooks/useAsync'
import { useToast } from '../../context/ToastContext'
import { useAuth } from '../../context/AuthContext'
import { knowledgeService } from '../../services'

export const ROLE_LABEL = { owner: 'Owner', editor: 'Editor', viewer: 'Viewer' }
const ROLE_HELP = {
  viewer: 'Can view, search and ask questions about the documents. Cannot change anything.',
  editor: 'Can also add their own documents, remove documents and edit labels. Cannot manage members or delete the collection.',
}

export function RoleBadge({ role }) {
  return <Badge tone={role === 'owner' ? 'brand' : role === 'editor' ? 'success' : 'neutral'}>{ROLE_LABEL[role] || role}</Badge>
}

function InviteDialog({ open, collectionId, onClose, onInvited }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('viewer')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Enter the email address of a registered user.')
      return
    }
    setSaving(true)
    try {
      await knowledgeService.inviteMember(collectionId, { email: email.trim(), role })
      setEmail('')
      setRole('viewer')
      setError('')
      onInvited()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={saving ? () => {} : onClose} title="Share collection" description="The person must already have a DocuMind AI account. Access starts immediately.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input label="Email address" type="email" value={email} data-autofocus onChange={(e) => setEmail(e.target.value)} error={error} />
        <Select label="Permission" value={role} onChange={(e) => setRole(e.target.value)} hint={ROLE_HELP[role]}>
          <option value="viewer">Viewer</option>
          <option value="editor">Editor</option>
        </Select>
        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Share
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// Members and sharing. `isOwner` only decides which controls are shown; the API enforces the rules.
export function MembersPanel({ collection, isOwner, onLeft, onChanged }) {
  const toast = useToast()
  const { user } = useAuth()
  const { data, error, loading, reload } = useAsync(() => knowledgeService.listMembers(collection.id), [collection.id])
  const [inviteOpen, setInviteOpen] = useState(false)
  const [toRemove, setToRemove] = useState(null)
  const [removing, setRemoving] = useState(false)
  const [busyId, setBusyId] = useState(null)

  const changeRole = async (member, role) => {
    setBusyId(member.userId)
    try {
      await knowledgeService.changeMemberRole(collection.id, member.userId, role)
      toast.success(`${member.name} is now ${ROLE_LABEL[role].toLowerCase()}.`)
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
      reload({ silent: true })
    } finally {
      setBusyId(null)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await knowledgeService.removeMember(collection.id, toRemove.userId)
      const leaving = toRemove.userId === user?.id
      toast.success(leaving ? 'You left the collection.' : `${toRemove.name} no longer has access.`)
      setToRemove(null)
      if (leaving) onLeft()
      else {
        reload({ silent: true })
        onChanged?.()
      }
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRemoving(false)
    }
  }

  const members = data ?? []
  const shared = members.length > 1

  return (
    <Card className="mt-8">
      <CardHeader
        title="Members and sharing"
        description={isOwner ? 'Only the people listed here can open this collection. Your other documents stay private.' : 'People who can open this collection.'}
        action={
          isOwner && (
            <Button size="sm" onClick={() => setInviteOpen(true)}>
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Share
            </Button>
          )
        }
      />
      {loading ? (
        <ListSkeleton rows={2} />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : (
        <>
          {!shared && isOwner && (
            <EmptyState compact icon={Users} title="Private collection" description="Only you can see it. Share it to let teammates view or edit it." />
          )}
          <ul className="divide-y divide-line" aria-label="Collection members">
            {members.map((m) => {
              const isMe = m.userId === user?.id
              return (
                <li key={m.userId} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1.5 truncate font-medium text-ink">
                      {m.role === 'owner' && <Crown className="h-3.5 w-3.5 shrink-0 text-gold-500" aria-hidden="true" />}
                      {m.name}
                      {isMe && <span className="text-xs font-normal text-muted">(you)</span>}
                    </p>
                    <p className="truncate text-xs text-muted">{m.email}</p>
                  </div>
                  {isOwner && m.role !== 'owner' ? (
                    <Select label={`Permission for ${m.name}`} labelHidden value={m.role} disabled={busyId === m.userId} onChange={(e) => changeRole(m, e.target.value)} className="sm:w-32">
                      <option value="viewer">Viewer</option>
                      <option value="editor">Editor</option>
                    </Select>
                  ) : (
                    <RoleBadge role={m.role} />
                  )}
                  {m.role !== 'owner' && (isOwner || isMe) && (
                    <Button size="sm" variant="dangerGhost" aria-label={isMe ? 'Leave collection' : `Revoke access for ${m.name}`} onClick={() => setToRemove(m)}>
                      {isMe ? <LogOut className="h-4 w-4" aria-hidden="true" /> : <UserMinus className="h-4 w-4" aria-hidden="true" />}
                      <span className="sm:hidden">{isMe ? 'Leave' : 'Revoke'}</span>
                    </Button>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}

      <InviteDialog
        open={inviteOpen}
        collectionId={collection.id}
        onClose={() => setInviteOpen(false)}
        onInvited={() => {
          setInviteOpen(false)
          toast.success('Collection shared.')
          reload({ silent: true })
          onChanged?.()
        }}
      />
      <ConfirmDialog
        open={Boolean(toRemove)}
        title={toRemove?.userId === user?.id ? 'Leave this collection?' : 'Revoke access?'}
        description={
          toRemove
            ? toRemove.userId === user?.id
              ? 'You will no longer be able to open its documents or ask questions about them.'
              : `${toRemove.name} (${toRemove.email}) will immediately lose access to this collection's documents.`
            : ''
        }
        confirmLabel={toRemove?.userId === user?.id ? 'Leave' : 'Revoke access'}
        loading={removing}
        onConfirm={confirmRemove}
        onCancel={() => setToRemove(null)}
      />
    </Card>
  )
}
