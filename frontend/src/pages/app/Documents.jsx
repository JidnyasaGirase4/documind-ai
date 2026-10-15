import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Upload } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { SearchInput } from '../../components/common/SearchInput'
import { Select } from '../../components/common/Field'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { ListSkeleton } from '../../components/common/LoadingSkeleton'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { Button } from '../../components/common/Button'
import { DocumentRow } from '../../components/documents/DocumentRow'
import { isInProgress } from '../../components/documents/DocumentStatusBadge'
import { UploadDropzone } from '../../components/documents/UploadDropzone'
import { useAsync } from '../../hooks/useAsync'
import { useDebounce } from '../../hooks/useDebounce'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { usePolling } from '../../hooks/usePolling'
import { useToast } from '../../context/ToastContext'
import { documentService } from '../../services'
import { DOCUMENT_POLL_INTERVAL_MS } from '../../utils/config'

const PAGE_SIZE = 10
const SORTS = {
  'created_at:desc': { label: 'Newest first', sortBy: 'created_at', sortOrder: 'desc' },
  'created_at:asc': { label: 'Oldest first', sortBy: 'created_at', sortOrder: 'asc' },
  'name:asc': { label: 'Name A–Z', sortBy: 'name', sortOrder: 'asc' },
  'name:desc': { label: 'Name Z–A', sortBy: 'name', sortOrder: 'desc' },
}

export default function Documents() {
  useDocumentTitle('My Documents')
  const toast = useToast()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [page, setPage] = useState(1)
  const [uploads, setUploads] = useState([])
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [retryingId, setRetryingId] = useState(null)
  const uploadId = useRef(0)
  const debouncedSearch = useDebounce(search, 350)

  const { sortBy, sortOrder } = SORTS[sort]
  const { data, error, loading, reload } = useAsync(
    () => documentService.listDocuments({ page, pageSize: PAGE_SIZE, search: debouncedSearch, status, sortBy, sortOrder }),
    [page, debouncedSearch, status, sort],
  )

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, status, sort])

  // Poll quietly while any listed document is still being processed.
  const hasInProgress = Boolean(data?.items.some((d) => isInProgress(d.status)))
  usePolling(() => reload({ silent: true }), DOCUMENT_POLL_INTERVAL_MS, hasInProgress)

  const uploadFiles = useCallback(
    async (files) => {
      const entries = files.map((f) => ({ id: ++uploadId.current, file: f }))
      setUploads((u) => [...entries.map((e) => ({ id: e.id, name: e.file.name, progress: 0, state: 'uploading' })), ...u].slice(0, 6))
      const patch = (id, p) => setUploads((u) => u.map((x) => (x.id === id ? { ...x, ...p } : x)))
      let succeeded = 0
      for (const { id, file } of entries) {
        try {
          await documentService.uploadDocument(file, (progress) => patch(id, { progress }))
          patch(id, { state: 'done', progress: 100 })
          succeeded += 1
        } catch (err) {
          patch(id, { state: 'error', error: err.message })
        }
      }
      if (succeeded) {
        toast.success(`${succeeded} ${succeeded === 1 ? 'file' : 'files'} uploaded. Processing has started.`)
        setPage(1)
        reload({ silent: true })
      }
      const failed = entries.length - succeeded
      if (failed) toast.error(`${failed} ${failed === 1 ? 'upload' : 'uploads'} failed.`)
    },
    [reload, toast],
  )

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await documentService.deleteDocument(toDelete.id)
      toast.success(`"${toDelete.filename}" was deleted.`)
      setToDelete(null)
      if (data.items.length === 1 && page > 1) setPage(page - 1)
      else reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
    }
  }

  const retry = async (doc) => {
    setRetryingId(doc.id)
    try {
      await documentService.retryDocument(doc.id)
      toast.success('Processing restarted.')
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRetryingId(null)
    }
  }

  const uploading = uploads.some((u) => u.state === 'uploading')
  const filtered = Boolean(debouncedSearch || status)

  return (
    <>
      <PageHeader title="My Documents" description="Upload PDFs and manage your document library." />

      <UploadDropzone onFiles={uploadFiles} uploads={uploads} disabled={uploading} />

      <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-end">
        <SearchInput className="sm:flex-1" value={search} onChange={setSearch} placeholder="Search by filename" label="Search documents by filename" />
        <div className="grid grid-cols-2 gap-3 sm:w-auto">
          <Select label="Status" labelHidden value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="uploaded">Queued</option>
            <option value="failed">Failed</option>
          </Select>
          <Select label="Sort by" labelHidden value={sort} onChange={(e) => setSort(e.target.value)}>
            {Object.entries(SORTS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="mt-4">
        {loading ? (
          <ListSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={reload} />
        ) : data.items.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={filtered ? 'No matching documents' : 'No documents yet'}
            description={filtered ? 'Try a different search or clear the filters.' : 'Upload your first PDF to start asking questions about it.'}
            action={
              filtered ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearch('')
                    setStatus('')
                  }}
                >
                  Clear filters
                </Button>
              ) : (
                <Button onClick={() => document.querySelector('[data-testid="file-input"]')?.click()}>
                  <Upload className="h-4 w-4" aria-hidden="true" />
                  Upload PDF
                </Button>
              )
            }
          />
        ) : (
          <>
            <ul className="space-y-3" aria-label="Documents">
              {data.items.map((d) => (
                <DocumentRow
                  key={d.id}
                  doc={d}
                  busy={retryingId === d.id}
                  onDelete={setToDelete}
                  onRetry={retry}
                  onPreview={() => navigate(`/app/documents/${d.id}`)}
                />
              ))}
            </ul>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.pageSize} onChange={setPage} noun="documents" />
          </>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(toDelete)}
        title="Delete this document?"
        description={toDelete ? `"${toDelete.filename}" and its indexed content will be permanently removed. This cannot be undone.` : ''}
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </>
  )
}
