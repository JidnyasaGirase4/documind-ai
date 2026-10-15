import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquareText, Pencil, Trash2 } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { SearchInput } from '../../components/common/SearchInput'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton } from '../../components/common/LoadingSkeleton'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { Modal } from '../../components/common/Modal'
import { Input } from '../../components/common/Field'
import { Button } from '../../components/common/Button'
import { Tooltip } from '../../components/common/Tooltip'
import { GetStarted } from '../../components/common/GetStarted'
import { useAsync } from '../../hooks/useAsync'
import { useDebounce } from '../../hooks/useDebounce'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useToast } from '../../context/ToastContext'
import { conversationService } from '../../services'
import { formatDateTime, pluralize } from '../../utils/format'

const PAGE_SIZE = 10

export default function History() {
  useDocumentTitle('Chat History')
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [renaming, setRenaming] = useState(null)
  const [title, setTitle] = useState('')
  const [titleError, setTitleError] = useState('')
  const [toDelete, setToDelete] = useState(null)
  const [busy, setBusy] = useState(false)
  const debounced = useDebounce(search, 350)

  const { data, error, loading, reload } = useAsync(
    () => conversationService.listConversations({ page, pageSize: PAGE_SIZE, search: debounced }),
    [page, debounced],
  )

  useEffect(() => {
    setPage(1)
  }, [debounced])

  const startRename = (c) => {
    setRenaming(c)
    setTitle(c.title)
    setTitleError('')
  }

  const submitRename = async (e) => {
    e.preventDefault()
    const t = title.trim()
    if (!t) return setTitleError('Enter a title.')
    if (t.length > 120) return setTitleError('Title must be 120 characters or fewer.')
    setBusy(true)
    try {
      await conversationService.renameConversation(renaming.id, t)
      toast.success('Conversation renamed.')
      setRenaming(null)
      reload({ silent: true })
    } catch (err) {
      setTitleError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const confirmDelete = async () => {
    setBusy(true)
    try {
      await conversationService.deleteConversation(toDelete.id)
      toast.success('Conversation deleted.')
      setToDelete(null)
      if (data.items.length === 1 && page > 1) setPage(page - 1)
      else reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Chat History"
        description="Revisit, rename or delete past conversations."
        actions={<Button to="/app/assistant">New chat</Button>}
      />
      <SearchInput className="mb-4 max-w-md" value={search} onChange={setSearch} placeholder="Search by title" label="Search conversations by title" />

      {loading ? (
        <ListSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : data.items.length === 0 ? (
        debounced ? (
          <EmptyState icon={MessageSquareText} title="No matching conversations" description="Try a different title." />
        ) : (
          <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-2">
            <div className="flex items-center justify-center rounded-card border border-dashed border-stone-300 bg-surface/60">
              <EmptyState
                compact
                icon={MessageSquareText}
                title="No conversations yet"
                description="Your conversations will appear here after you ask your first question."
                action={<Button to="/app/assistant">Ask a question</Button>}
              />
            </div>
            <GetStarted />
          </div>
        )
      ) : (
        <>
          <ul className="space-y-3" aria-label="Conversations">
            {data.items.map((c) => (
              <li key={c.id} className="hover-lift flex animate-fade-in-up flex-col gap-3 rounded-card border border-line bg-surface p-4 shadow-card hover:border-brand-200 sm:flex-row sm:items-center sm:gap-4">
                <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center sm:gap-4">
                <span className="icon-tile h-11 w-11">
                  <MessageSquareText className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <Link to={`/app/assistant/${c.id}`} className="block break-words font-medium text-ink hover:text-brand-700 hover:underline sm:truncate">
                    {c.title}
                  </Link>
                  <p className="mt-0.5 text-xs text-muted">
                    Updated {formatDateTime(c.updatedAt)}
                    {c.messageCount != null && ` · ${pluralize(c.messageCount, 'message')}`}
                  </p>
                </div>
                </div>
                <div className="flex shrink-0 justify-end gap-1 border-t border-line pt-3 sm:border-0 sm:pt-0">
                  <Tooltip text="Rename">
                    <button
                      type="button"
                      onClick={() => startRename(c)}
                      aria-label={`Rename ${c.title}`}
                      className="rounded-md p-2 text-muted hover:bg-stone-100 hover:text-ink"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  </Tooltip>
                  <Tooltip text="Delete">
                    <button
                      type="button"
                      onClick={() => setToDelete(c)}
                      aria-label={`Delete ${c.title}`}
                      className="rounded-md p-2 text-muted hover:bg-danger-soft hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </Tooltip>
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.pageSize} onChange={setPage} noun="conversations" />
        </>
      )}

      <Modal open={Boolean(renaming)} onClose={() => !busy && setRenaming(null)} title="Rename conversation">
        <form onSubmit={submitRename} noValidate>
          <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} error={titleError} data-autofocus maxLength={120} />
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="secondary" onClick={() => setRenaming(null)} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Save
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete this conversation?"
        description={toDelete ? `"${toDelete.title}" and all of its messages will be permanently removed.` : ''}
        loading={busy}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </>
  )
}
