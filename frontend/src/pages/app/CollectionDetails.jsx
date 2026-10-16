import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, FolderInput, Pencil, Plus, Trash2, X } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton, Skeleton } from '../../components/common/LoadingSkeleton'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { Button } from '../../components/common/Button'
import { Badge } from '../../components/common/Badge'
import { Modal } from '../../components/common/Modal'
import { Select } from '../../components/common/Field'
import { DocumentStatusBadge } from '../../components/documents/DocumentStatusBadge'
import { CollectionDialog } from '../../components/knowledge/CollectionDialog'
import { CollectionIcon } from '../../components/knowledge/collectionStyle'
import { MembersPanel, RoleBadge } from '../../components/knowledge/MembersPanel'
import { Link } from 'react-router-dom'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useToast } from '../../context/ToastContext'
import { documentService, knowledgeService } from '../../services'
import { formatBytes, pluralize } from '../../utils/format'

const PAGE_SIZE = 10

// Pick owned documents that are not yet in this collection (or move them from another collection).
function AddDocumentsDialog({ open, collectionId, onClose, onAdded }) {
  const toast = useToast()
  const [docs, setDocs] = useState(null)
  const [selected, setSelected] = useState([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setSelected([])
    setError('')
    setDocs(null)
    documentService
      .listDocuments({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' })
      .then((res) => setDocs(res.items.filter((d) => !d.collectionIds.includes(collectionId))))
      .catch((err) => setError(err.message))
  }, [open, collectionId])

  const add = async () => {
    setSaving(true)
    try {
      await knowledgeService.addDocuments(collectionId, selected)
      toast.success(`${selected.length} ${selected.length === 1 ? 'document' : 'documents'} added.`)
      onAdded()
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
      title="Add documents"
      description="Documents can belong to several collections."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={add} loading={saving} disabled={selected.length === 0}>
            Add {selected.length || ''} selected
          </Button>
        </>
      }
    >
      {error && (
        <p role="alert" className="mb-2 text-sm text-danger">
          {error}
        </p>
      )}
      {docs === null && !error ? (
        <ListSkeleton rows={3} />
      ) : docs && docs.length === 0 ? (
        <p className="text-sm text-muted">All of your documents are already in this collection.</p>
      ) : (
        <ul className="max-h-72 space-y-1 overflow-y-auto rounded-control border border-line p-2" aria-label="Documents to add">
          {docs?.map((d) => (
            <li key={d.id}>
              <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-stone-50">
                <input
                  type="checkbox"
                  checked={selected.includes(d.id)}
                  onChange={() => setSelected((s) => (s.includes(d.id) ? s.filter((x) => x !== d.id) : [...s, d.id]))}
                />
                <span className="truncate">{d.filename}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}

// Move one document into another collection (removed from this one in the same transaction).
function MoveDialog({ doc, fromId, onClose, onMoved }) {
  const toast = useToast()
  const [targets, setTargets] = useState([])
  const [target, setTarget] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!doc) return
    setTarget('')
    setError('')
    knowledgeService
      .listCollections({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' })
      .then((res) => setTargets(res.items.filter((c) => c.id !== fromId)))
      .catch((err) => setError(err.message))
  }, [doc, fromId])

  const move = async () => {
    setSaving(true)
    try {
      await knowledgeService.addDocuments(Number(target), [doc.id], fromId)
      toast.success('Document moved.')
      onMoved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={Boolean(doc)}
      onClose={saving ? () => {} : onClose}
      title="Move to another collection"
      description={doc?.filename}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={move} loading={saving} disabled={!target}>
            Move
          </Button>
        </>
      }
    >
      {error && (
        <p role="alert" className="mb-2 text-sm text-danger">
          {error}
        </p>
      )}
      {targets.length === 0 && !error ? (
        <p className="text-sm text-muted">You have no other collections. Create one first.</p>
      ) : (
        <Select label="Destination collection" value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="">Choose a collection…</option>
          {targets.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      )}
    </Modal>
  )
}

export default function CollectionDetails() {
  const { collectionId } = useParams()
  const id = Number(collectionId)
  const navigate = useNavigate()
  const toast = useToast()
  const [page, setPage] = useState(1)
  const [editOpen, setEditOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [toRemove, setToRemove] = useState(null)
  const [toMove, setToMove] = useState(null)

  const coll = useAsync(() => knowledgeService.getCollection(id), [id])
  const docs = useAsync(() => documentService.listDocuments({ page, pageSize: PAGE_SIZE, collectionId: id }), [id, page])
  useDocumentTitle(coll.data?.name || 'Collection')

  const refresh = useCallback(() => {
    coll.reload({ silent: true })
    docs.reload({ silent: true })
  }, [coll, docs])

  const back = (
    <Button to="/app/knowledge" variant="ghost" size="sm" className="mb-3 -ml-2">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      Back to Knowledge Base
    </Button>
  )

  if (coll.loading) {
    return (
      <>
        {back}
        <Skeleton className="mb-6 h-8 w-1/2" />
        <ListSkeleton />
      </>
    )
  }
  if (coll.error) {
    return (
      <>
        {back}
        <ErrorState error={coll.error} title={coll.error.status === 404 ? 'Collection not found' : undefined} onRetry={coll.error.status === 404 ? undefined : coll.reload} />
      </>
    )
  }
  const c = coll.data
  const isOwner = c.role === 'owner'
  const canEdit = c.role !== 'viewer'

  const save = async (values) => {
    await knowledgeService.updateCollection(c.id, values)
    toast.success('Collection updated.')
    setEditOpen(false)
    coll.reload({ silent: true })
  }

  const remove = async () => {
    setDeleting(true)
    try {
      await knowledgeService.deleteCollection(c.id)
      toast.success(`Collection "${c.name}" was deleted. Its documents were kept.`)
      navigate('/app/knowledge', { replace: true })
    } catch (err) {
      toast.error(err.message)
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  const removeDoc = async () => {
    try {
      await knowledgeService.removeDocument(c.id, toRemove.id)
      toast.success('Removed from this collection. The document itself was kept.')
      setToRemove(null)
      if (docs.data.items.length === 1 && page > 1) setPage(page - 1)
      else refresh()
    } catch (err) {
      toast.error(err.message)
    }
  }

  return (
    <>
      {back}
      <div className="mb-2 flex items-center gap-3">
        <CollectionIcon collection={c} />
        <Badge tone="neutral">{c.documentCount} {c.documentCount === 1 ? 'document' : 'documents'}</Badge>
        {isOwner ? <Badge tone={c.isShared ? 'brand' : 'neutral'}>{c.isShared ? `Shared with ${c.memberCount} ${c.memberCount === 1 ? 'person' : 'people'}` : 'Private'}</Badge> : <RoleBadge role={c.role} />}
        {!isOwner && c.ownerName && <span className="text-xs text-muted">Owned by {c.ownerName}</span>}
      </div>
      <PageHeader
        title={c.name}
        description={c.description || undefined}
        breadcrumbs={[{ label: 'Knowledge Base', to: '/app/knowledge' }, { label: c.name }]}
        actions={
          <>
            {canEdit && (
              <Button onClick={() => setAddOpen(true)}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add documents
              </Button>
            )}
            {isOwner && (
              <>
                <Button variant="secondary" onClick={() => setEditOpen(true)}>
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                  Edit
                </Button>
                <Button variant="dangerGhost" onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Delete
                </Button>
              </>
            )}
          </>
        }
      />

      {docs.loading ? (
        <ListSkeleton />
      ) : docs.error ? (
        <ErrorState error={docs.error} onRetry={docs.reload} />
      ) : docs.data.items.length === 0 ? (
        <EmptyState icon={FileText} title="This collection is empty" description={canEdit ? 'Add documents you have already uploaded.' : 'Nothing has been added to this collection yet.'} action={canEdit ? <Button onClick={() => setAddOpen(true)}>Add documents</Button> : undefined} />
      ) : (
        <>
          <ul className="space-y-3" aria-label="Documents in this collection">
            {docs.data.items.map((d) => (
              <li key={d.id} className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4 shadow-card sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <Link to={`/app/documents/${d.id}`} className="block break-words font-medium text-ink hover:text-brand-700 hover:underline sm:truncate">
                    {d.filename}
                  </Link>
                  <p className="mt-0.5 text-xs text-muted">
                    {formatBytes(d.size)}
                    {d.pages ? ` · ${pluralize(d.pages, 'page')}` : ''}
                    {d.category ? ` · ${d.category.name}` : ''}
                    {d.isOwner === false ? ' · added by a teammate' : ''}
                  </p>
                </div>
                <DocumentStatusBadge status={d.status} />
                {canEdit && (
                  <div className="flex gap-1">
                    {d.isOwner && (
                      <Button size="sm" variant="ghost" aria-label={`Move ${d.filename}`} onClick={() => setToMove(d)}>
                        <FolderInput className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    )}
                    <Button size="sm" variant="dangerGhost" aria-label={`Remove ${d.filename} from collection`} onClick={() => setToRemove(d)}>
                      <X className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <Pagination page={docs.data.page} pages={docs.data.pages} total={docs.data.total} pageSize={docs.data.pageSize} onChange={setPage} noun="documents" />
        </>
      )}

      <MembersPanel collection={c} isOwner={isOwner} onChanged={() => coll.reload({ silent: true })} onLeft={() => navigate('/app/knowledge', { replace: true })} />

      <CollectionDialog open={editOpen} collection={c} onClose={() => setEditOpen(false)} onSubmit={save} />
      <AddDocumentsDialog
        open={addOpen}
        collectionId={c.id}
        onClose={() => setAddOpen(false)}
        onAdded={() => {
          setAddOpen(false)
          refresh()
        }}
      />
      <MoveDialog
        doc={toMove}
        fromId={c.id}
        onClose={() => setToMove(null)}
        onMoved={() => {
          setToMove(null)
          refresh()
        }}
      />
      <ConfirmDialog
        open={confirmDelete}
        title="Delete this collection?"
        description={`"${c.name}" will be removed. Its ${c.documentCount} documents are NOT deleted; they stay in My Documents.`}
        confirmLabel="Delete collection"
        loading={deleting}
        onConfirm={remove}
        onCancel={() => setConfirmDelete(false)}
      />
      <ConfirmDialog
        open={Boolean(toRemove)}
        title="Remove from collection?"
        description={toRemove ? `"${toRemove.filename}" will leave this collection but stays in My Documents.` : ''}
        confirmLabel="Remove"
        destructive={false}
        onConfirm={removeDoc}
        onCancel={() => setToRemove(null)}
      />
    </>
  )
}
