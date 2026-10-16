import { useEffect, useState } from 'react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Input, Textarea } from '../common/Field'

// Create or rename a category (with description) or a tag (name only).
export function LabelDialog({ open, kind, item, onClose, onSubmit }) {
  const isTag = kind === 'tag'
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setName(item?.name ?? '')
      setDescription(item?.description ?? '')
      setError('')
    }
  }, [open, item])

  const submit = async (e) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Please enter a name.')
      return
    }
    setSaving(true)
    try {
      await onSubmit({ name: name.trim(), description })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={saving ? () => {} : onClose} title={`${item ? 'Edit' : 'New'} ${kind}`}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input label="Name" value={name} maxLength={isTag ? 50 : 100} data-autofocus onChange={(e) => setName(e.target.value)} error={error} />
        {!isTag && <Textarea label="Description (optional)" rows={3} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} />}
        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {item ? 'Save' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
