import { useEffect, useState } from 'react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Input, Textarea } from '../common/Field'
import { COLORS, ICONS } from './collectionStyle'
import { cx } from '../../utils/format'

// Create (collection = null) or edit a collection. `onSubmit` rejects with an Error whose message is shown inline.
export function CollectionDialog({ open, collection, onClose, onSubmit }) {
  const [form, setForm] = useState({ name: '', description: '', color: 'burgundy', icon: 'folder' })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm({
        name: collection?.name ?? '',
        description: collection?.description ?? '',
        color: collection?.color ?? 'burgundy',
        icon: collection?.icon ?? 'folder',
      })
      setError('')
    }
  }, [open, collection])

  const submit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setError('Please enter a name.')
      return
    }
    setSaving(true)
    try {
      await onSubmit({ ...form, name: form.name.trim() })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={saving ? () => {} : onClose} title={collection ? 'Edit collection' : 'New collection'}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Input label="Name" value={form.name} maxLength={100} data-autofocus onChange={(e) => setForm({ ...form, name: e.target.value })} error={error} />
        <Textarea label="Description (optional)" rows={3} maxLength={1000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium text-ink">Color</legend>
          <div className="flex flex-wrap gap-2">
            {Object.entries(COLORS).map(([key, hex]) => (
              <button
                key={key}
                type="button"
                aria-label={key}
                aria-pressed={form.color === key}
                onClick={() => setForm({ ...form, color: key })}
                className={cx('h-8 w-8 rounded-full border-2 transition', form.color === key ? 'border-ink ring-2 ring-brand-300 ring-offset-2' : 'border-transparent')}
                style={{ backgroundColor: hex }}
              />
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium text-ink">Icon</legend>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ICONS).map(([key, Icon]) => (
              <button
                key={key}
                type="button"
                aria-label={`${key} icon`}
                aria-pressed={form.icon === key}
                onClick={() => setForm({ ...form, icon: key })}
                className={cx('flex h-9 w-9 items-center justify-center rounded-lg border', form.icon === key ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-line text-muted hover:bg-stone-50')}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
              </button>
            ))}
          </div>
        </fieldset>
        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {collection ? 'Save changes' : 'Create collection'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
