import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FolderPlus, Layers, Pencil, Plus, Tag as TagIcon, Trash2 } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { SearchInput } from '../../components/common/SearchInput'
import { Select } from '../../components/common/Field'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton } from '../../components/common/LoadingSkeleton'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { Badge } from '../../components/common/Badge'
import { RoleBadge } from '../../components/knowledge/MembersPanel'
import { CollectionDialog } from '../../components/knowledge/CollectionDialog'
import { LabelDialog } from '../../components/knowledge/LabelDialog'
import { CollectionIcon } from '../../components/knowledge/collectionStyle'
import { useAsync } from '../../hooks/useAsync'
import { useDebounce } from '../../hooks/useDebounce'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useToast } from '../../context/ToastContext'
import { knowledgeService } from '../../services'
import { cx } from '../../utils/format'

const PAGE_SIZE = 12
const SORTS = {
  'created_at:desc': { label: 'Newest first', sortBy: 'created_at', sortOrder: 'desc' },
  'name:asc': { label: 'Name A–Z', sortBy: 'name', sortOrder: 'asc' },
  'documents:desc': { label: 'Most documents', sortBy: 'documents', sortOrder: 'desc' },
  'updated_at:desc': { label: 'Recently updated', sortBy: 'updated_at', sortOrder: 'desc' },
}
const TABS = [
  { id: 'collections', label: 'Collections' },
  { id: 'categories', label: 'Categories' },
  { id: 'tags', label: 'Tags' },
]

function CollectionsTab() {
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [scope, setScope] = useState('all')
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState({ open: false, collection: null })
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const debounced = useDebounce(search, 350)
  const { sortBy, sortOrder } = SORTS[sort]
  const { data, error, loading, reload } = useAsync(
    () => knowledgeService.listCollections({ page, pageSize: PAGE_SIZE, search: debounced, sortBy, sortOrder, scope }),
    [page, debounced, sort, scope],
  )

  useEffect(() => setPage(1), [debounced, sort, scope])

  const save = async (values) => {
    if (dialog.collection) await knowledgeService.updateCollection(dialog.collection.id, values)
    else await knowledgeService.createCollection(values)
    toast.success(dialog.collection ? 'Collection updated.' : 'Collection created.')
    setDialog({ open: false, collection: null })
    reload({ silent: true })
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await knowledgeService.deleteCollection(toDelete.id)
      toast.success(`Collection "${toDelete.name}" was deleted. Its documents were kept.`)
      setToDelete(null)
      if (data.items.length === 1 && page > 1) setPage(page - 1)
      else reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <SearchInput className="sm:flex-1" value={search} onChange={setSearch} placeholder="Search collections" label="Search collections" />
        <Select label="Show collections" labelHidden value={scope} onChange={(e) => setScope(e.target.value)}>
          <option value="all">All collections</option>
          <option value="owned">Owned by me</option>
          <option value="shared">Shared with me</option>
        </Select>
        <Select label="Sort collections" labelHidden value={sort} onChange={(e) => setSort(e.target.value)}>
          {Object.entries(SORTS).map(([k, v]) => (
            <option key={k} value={k}>
              {v.label}
            </option>
          ))}
        </Select>
        <Button onClick={() => setDialog({ open: true, collection: null })}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          New collection
        </Button>
      </div>

      <div className="mt-4">
        {loading ? (
          <ListSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={reload} />
        ) : data.items.length === 0 ? (
          <EmptyState
            icon={FolderPlus}
            title={debounced || scope !== 'all' ? 'No matching collections' : 'No collections yet'}
            description={debounced || scope !== 'all' ? 'Try a different search or filter.' : 'Group related documents into a collection, for example "HR Policies" or "Project Alpha".'}
            action={
              !debounced && scope === 'all' && (
                <Button onClick={() => setDialog({ open: true, collection: null })}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Create your first collection
                </Button>
              )
            }
          />
        ) : (
          <>
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Collections">
              {data.items.map((c) => (
                <li key={c.id}>
                  <Card interactive className="flex h-full flex-col">
                    <div className="flex items-start gap-3">
                      <CollectionIcon collection={c} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/app/knowledge/collections/${c.id}`} className="block truncate font-semibold text-ink hover:text-brand-700 hover:underline">
                          {c.name}
                        </Link>
                        <p className="text-xs text-muted">
                          {c.documentCount} {c.documentCount === 1 ? 'document' : 'documents'}
                          {c.role !== 'owner' && c.ownerName ? ` · by ${c.ownerName}` : ''}
                        </p>
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {c.role === 'owner' ? <Badge tone={c.isShared ? 'brand' : 'neutral'}>{c.isShared ? `Shared · ${c.memberCount}` : 'Private'}</Badge> : <RoleBadge role={c.role} />}
                        </div>
                      </div>
                    </div>
                    {c.description && <p className="mt-3 line-clamp-2 text-sm text-muted">{c.description}</p>}
                    {c.role === 'owner' && (
                      <div className="mt-auto flex justify-end gap-1 pt-3">
                        <Button size="sm" variant="ghost" aria-label={`Edit ${c.name}`} onClick={() => setDialog({ open: true, collection: c })}>
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button size="sm" variant="dangerGhost" aria-label={`Delete ${c.name}`} onClick={() => setToDelete(c)}>
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    )}
                  </Card>
                </li>
              ))}
            </ul>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.pageSize} onChange={setPage} noun="collections" />
          </>
        )}
      </div>

      <CollectionDialog open={dialog.open} collection={dialog.collection} onClose={() => setDialog({ open: false, collection: null })} onSubmit={save} />
      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete this collection?"
        description={toDelete ? `"${toDelete.name}" will be removed. The ${toDelete.documentCount} documents inside it are NOT deleted; they stay in My Documents.` : ''}
        confirmLabel="Delete collection"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </>
  )
}

// Categories and tags share one list-with-dialogs layout.
function LabelsTab({ kind }) {
  const toast = useToast()
  const isTag = kind === 'tag'
  const noun = isTag ? 'tag' : 'category'
  const { data, error, loading, reload } = useAsync(() => (isTag ? knowledgeService.listTags() : knowledgeService.listCategories()), [kind])
  const [dialog, setDialog] = useState({ open: false, item: null })
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const save = async ({ name, description }) => {
    const item = dialog.item
    if (isTag) await (item ? knowledgeService.renameTag(item.id, name) : knowledgeService.createTag(name))
    else await (item ? knowledgeService.updateCategory(item.id, { name, description }) : knowledgeService.createCategory({ name, description }))
    toast.success(item ? `${isTag ? 'Tag' : 'Category'} updated.` : `${isTag ? 'Tag' : 'Category'} created.`)
    setDialog({ open: false, item: null })
    reload({ silent: true })
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await (isTag ? knowledgeService.deleteTag(toDelete.id) : knowledgeService.deleteCategory(toDelete.id))
      toast.success(`Deleted "${toDelete.name}". Documents were kept.`)
      setToDelete(null)
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <div className="flex justify-end">
        <Button onClick={() => setDialog({ open: true, item: null })}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          New {noun}
        </Button>
      </div>
      <div className="mt-4">
        {loading ? (
          <ListSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={reload} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={isTag ? TagIcon : Layers}
            title={`No ${noun === 'tag' ? 'tags' : 'categories'} yet`}
            description={isTag ? 'Tags are free-form labels such as "2026" or "contract". You can also add them directly on a document.' : 'Categories are reusable labels such as "HR Policies" or "Finance". Each document has at most one.'}
          />
        ) : (
          <ul className="divide-y divide-line rounded-card border border-line bg-surface shadow-card" aria-label={isTag ? 'Tags' : 'Categories'}>
            {data.map((item) => (
              <li key={item.id} className="flex items-center gap-3 p-3 sm:p-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{item.name}</p>
                  {item.description && <p className="truncate text-xs text-muted">{item.description}</p>}
                </div>
                <span className="shrink-0 text-xs text-muted">
                  {item.documentCount} {item.documentCount === 1 ? 'document' : 'documents'}
                </span>
                <Button size="sm" variant="ghost" aria-label={`Edit ${item.name}`} onClick={() => setDialog({ open: true, item })}>
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button size="sm" variant="dangerGhost" aria-label={`Delete ${item.name}`} onClick={() => setToDelete(item)}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <LabelDialog open={dialog.open} kind={noun} item={dialog.item} onClose={() => setDialog({ open: false, item: null })} onSubmit={save} />
      <ConfirmDialog
        open={Boolean(toDelete)}
        title={`Delete this ${noun}?`}
        description={toDelete ? `"${toDelete.name}" will be removed from ${toDelete.documentCount} documents. The documents themselves are not deleted.` : ''}
        confirmLabel={`Delete ${noun}`}
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </>
  )
}

export default function KnowledgeBase() {
  useDocumentTitle('Knowledge Base')
  const [tab, setTab] = useState('collections')

  return (
    <>
      <PageHeader title="Knowledge Base" description="Organize your documents into collections, categories and tags." />
      <div role="tablist" aria-label="Knowledge Base sections" className="mb-5 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setTab(t.id)}
            className={cx(
              '-mb-px border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors',
              tab === t.id ? 'border-brand-600 text-brand-700' : 'border-transparent text-muted hover:text-ink',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === 'collections' ? <CollectionsTab /> : <LabelsTab key={tab} kind={tab === 'tags' ? 'tag' : 'category'} />}
      </div>
    </>
  )
}
