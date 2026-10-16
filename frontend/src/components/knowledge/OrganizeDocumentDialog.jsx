import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Input, Select } from '../common/Field'
import { knowledgeService } from '../../services'

// Assign a document's category, tags and collections. Editing never re-uploads or re-processes the file.
export function OrganizeDocumentDialog({ open, doc, onClose, onSave }) {
  const [categories, setCategories] = useState([])
  const [collections, setCollections] = useState([])
  const [categoryId, setCategoryId] = useState('')
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [collectionIds, setCollectionIds] = useState([])
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open || !doc) return
    setCategoryId(doc.category ? String(doc.category.id) : '')
    setTags(doc.tags.map((t) => t.name))
    setCollectionIds(doc.collectionIds)
    setTagInput('')
    setError('')
    setLoadError('')
    Promise.all([knowledgeService.listCategories(), knowledgeService.listCollections({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' })])
      .then(([cats, colls]) => {
        setCategories(cats)
        setCollections(colls.items)
      })
      .catch((err) => setLoadError(err.message))
  }, [open, doc])

  const addTag = () => {
    const name = tagInput.trim().replace(/\s+/g, ' ')
    if (!name) return
    if (tags.some((t) => t.toLowerCase() === name.toLowerCase())) {
      setError(`"${name}" is already added.`)
      return
    }
    setTags([...tags, name])
    setTagInput('')
    setError('')
  }

  const toggleCollection = (id) => setCollectionIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]))

  const save = async () => {
    setSaving(true)
    try {
      await onSave({ categoryId: categoryId ? Number(categoryId) : null, tags, collectionIds })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={saving ? () => {} : onClose}
      title="Organize document"
      description={doc?.filename}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving} disabled={Boolean(loadError)}>
            Save
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {loadError && (
          <p role="alert" className="text-sm text-danger">
            {loadError}
          </p>
        )}
        <Select label="Category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">No category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>

        <div>
          <Input
            label="Tags"
            value={tagInput}
            maxLength={50}
            placeholder="Type a tag and press Enter"
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                addTag()
              }
            }}
            error={error}
          />
          {tags.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-2" aria-label="Selected tags">
              {tags.map((t) => (
                <li key={t} className="inline-flex items-center gap-1 rounded-full bg-brand-50 py-0.5 pl-2.5 pr-1 text-xs font-medium text-brand-700">
                  {t}
                  <button type="button" aria-label={`Remove tag ${t}`} className="rounded-full p-0.5 hover:bg-brand-100" onClick={() => setTags(tags.filter((x) => x !== t))}>
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <fieldset>
          <legend className="mb-1.5 text-sm font-medium text-ink">Collections</legend>
          {collections.length === 0 ? (
            <p className="text-sm text-muted">You have no collections yet. Create one from the Knowledge Base page.</p>
          ) : (
            <ul className="max-h-44 space-y-1 overflow-y-auto rounded-control border border-line p-2">
              {collections.map((c) => (
                <li key={c.id}>
                  <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-stone-50">
                    <input type="checkbox" checked={collectionIds.includes(c.id)} onChange={() => toggleCollection(c.id)} />
                    {c.name}
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>
      </div>
    </Modal>
  )
}
