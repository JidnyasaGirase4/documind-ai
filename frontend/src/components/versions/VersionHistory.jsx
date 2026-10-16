import { useRef, useState } from 'react'
import { Download, Eye, GitCompare, History, RotateCw, Undo2, Upload } from 'lucide-react'
import { Card, CardHeader } from '../common/Card'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Modal } from '../common/Modal'
import { Textarea } from '../common/Field'
import { ConfirmDialog } from '../common/ConfirmDialog'
import { ErrorState } from '../common/ErrorState'
import { EmptyState } from '../common/EmptyState'
import { ListSkeleton } from '../common/LoadingSkeleton'
import { useAsync } from '../../hooks/useAsync'
import { usePolling } from '../../hooks/usePolling'
import { useToast } from '../../context/ToastContext'
import { documentService } from '../../services'
import { DOCUMENT_POLL_INTERVAL_MS } from '../../utils/config'
import { formatBytes, formatDateTime, pluralize } from '../../utils/format'
import { VersionCompare } from './VersionCompare'

const STATUS = {
  ready: { tone: 'success', label: 'Ready' },
  queued: { tone: 'neutral', label: 'Queued' },
  processing: { tone: 'warning', label: 'Processing' },
  failed: { tone: 'danger', label: 'Failed' },
  uploaded: { tone: 'neutral', label: 'Uploaded' },
}
const inProgress = (s) => s === 'queued' || s === 'processing'

function UploadVersionDialog({ open, documentId, onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [note, setNote] = useState('')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const input = useRef(null)

  const close = () => {
    setFile(null)
    setNote('')
    setError('')
    setProgress(0)
    onClose()
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Choose a PDF file.')
      return
    }
    if (!/\.pdf$/i.test(file.name)) {
      setError('Only PDF files are supported.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const v = await documentService.uploadVersion(documentId, file, note.trim(), setProgress)
      onUploaded(v)
      close()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={busy ? () => {} : close} title="Upload a new version" description="The new version is processed in the background. The current version stays in use until the new one is ready.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="version-file" className="mb-1.5 block text-sm font-medium text-ink">
            PDF file
          </label>
          <input id="version-file" ref={input} type="file" accept="application/pdf,.pdf" data-testid="version-file-input" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="block w-full text-sm" />
        </div>
        <Textarea label="What changed? (optional)" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        {error && (
          <p role="alert" className="text-sm font-medium text-danger">
            {error}
          </p>
        )}
        {busy && (
          <div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} className="h-2 overflow-hidden rounded-full bg-stone-200">
            <div className="h-full bg-brand-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={close} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" loading={busy}>
            Upload version
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// Version history of one document. `canManage` (owner/editor) only controls which buttons are shown; the API enforces it.
export function VersionHistory({ documentId, canManage, onOpenVersion, onChanged }) {
  const toast = useToast()
  const { data, error, loading, reload } = useAsync(() => documentService.listVersions(documentId), [documentId])
  const [uploadOpen, setUploadOpen] = useState(false)
  const [selected, setSelected] = useState([])
  const [toRestore, setToRestore] = useState(null)
  const [restoring, setRestoring] = useState(false)
  const [comparison, setComparison] = useState({ loading: false, error: null, result: null })
  const [busyId, setBusyId] = useState(null)

  const versions = data ?? []
  usePolling(
    async () => {
      await reload({ silent: true })
      onChanged?.() // lets the page pick up a newly activated current version
    },
    DOCUMENT_POLL_INTERVAL_MS,
    versions.some((v) => inProgress(v.status)),
  )

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 2 ? [s[1], id] : [...s, id]))

  const compare = async () => {
    const [a, b] = versions.filter((v) => selected.includes(v.id)).sort((x, y) => x.number - y.number)
    setComparison({ loading: true, error: null, result: null })
    try {
      setComparison({ loading: false, error: null, result: await documentService.compareVersions(documentId, a.id, b.id) })
    } catch (err) {
      setComparison({ loading: false, error: err, result: null })
      toast.error(err.message)
    }
  }

  const restore = async () => {
    setRestoring(true)
    try {
      const v = await documentService.restoreVersion(documentId, toRestore.id)
      toast.success(`Restoring version ${toRestore.number} as version ${v.number}. It becomes current when processing finishes.`)
      setToRestore(null)
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
      setToRestore(null)
    } finally {
      setRestoring(false)
    }
  }

  const retry = async (v) => {
    setBusyId(v.id)
    try {
      await documentService.retryVersion(documentId, v.id)
      toast.success(`Processing of version ${v.number} restarted.`)
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const download = async (v) => {
    setBusyId(v.id)
    try {
      await documentService.downloadVersion(documentId, v)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusyId(null)
    }
  }

  if (comparison.result) {
    return <VersionCompare result={comparison.result} onBack={() => setComparison({ loading: false, error: null, result: null })} />
  }

  return (
    <Card>
      <CardHeader
        title="Version history"
        description="Every upload is kept. The current version is the one used for search and AI answers."
        action={
          canManage && (
            <Button size="sm" onClick={() => setUploadOpen(true)}>
              <Upload className="h-4 w-4" aria-hidden="true" />
              Upload new version
            </Button>
          )
        }
      />

      {loading ? (
        <ListSkeleton rows={2} />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : versions.length === 0 ? (
        <EmptyState compact icon={History} title="No versions yet" description="Versions appear here once the document has been uploaded." />
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="secondary" disabled={selected.length !== 2} loading={comparison.loading} onClick={compare}>
              <GitCompare className="h-4 w-4" aria-hidden="true" />
              Compare selected
            </Button>
            <span className="text-xs text-muted">{versions.length < 2 ? 'Upload another version to compare.' : `Select two versions to compare (${selected.length}/2).`}</span>
          </div>
          <ol className="space-y-3" aria-label="Versions, newest first">
            {versions.map((v) => {
              const st = STATUS[v.status] ?? STATUS.uploaded
              return (
                <li key={v.id} className={`rounded-control border p-3 ${v.isCurrent ? 'border-brand-300 bg-brand-50/40' : 'border-line bg-surface'}`}>
                  <div className="flex flex-wrap items-start gap-3">
                    {versions.length > 1 && (
                      <input
                        type="checkbox"
                        className="mt-1.5"
                        aria-label={`Select version ${v.number} for comparison`}
                        checked={selected.includes(v.id)}
                        onChange={() => toggle(v.id)}
                      />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">Version {v.number}</span>
                        {v.isCurrent ? <Badge tone="brand">Current</Badge> : <Badge>Earlier version</Badge>}
                        <Badge tone={st.tone}>{st.label}</Badge>
                        {v.restoredFrom != null && <Badge icon={Undo2}>Restored from v{v.restoredFrom}</Badge>}
                      </div>
                      <p className="mt-1 text-xs text-muted">
                        {formatDateTime(v.createdAt)}
                        {v.uploadedBy ? ` · ${v.uploadedBy.name}` : ''} · {formatBytes(v.size)}
                        {v.pages ? ` · ${pluralize(v.pages, 'page')}` : ''}
                      </p>
                      {v.note && <p className="mt-1 text-sm text-ink">{v.note}</p>}
                      {v.status === 'failed' && v.error && <p className="mt-1 text-sm text-danger">{v.error}</p>}
                      {inProgress(v.status) && <p className="mt-1 text-xs text-muted">Processing{v.progress != null ? ` · ${v.progress}%` : ''}. The current version stays active meanwhile.</p>}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Button size="sm" variant="ghost" aria-label={`View version ${v.number}`} onClick={() => onOpenVersion(v)}>
                        <Eye className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button size="sm" variant="ghost" aria-label={`Download version ${v.number}`} loading={busyId === v.id} onClick={() => download(v)}>
                        <Download className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      {canManage && v.status === 'failed' && (
                        <Button size="sm" variant="ghost" aria-label={`Retry processing of version ${v.number}`} loading={busyId === v.id} onClick={() => retry(v)}>
                          <RotateCw className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      )}
                      {canManage && !v.isCurrent && v.status === 'ready' && (
                        <Button size="sm" variant="secondary" aria-label={`Restore version ${v.number}`} onClick={() => setToRestore(v)}>
                          <Undo2 className="h-4 w-4" aria-hidden="true" />
                          Restore
                        </Button>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ol>
        </>
      )}

      <UploadVersionDialog
        open={uploadOpen}
        documentId={documentId}
        onClose={() => setUploadOpen(false)}
        onUploaded={(v) => {
          toast.success(`Version ${v.number} uploaded. It becomes current when processing finishes.`)
          reload({ silent: true })
        }}
      />
      <ConfirmDialog
        open={Boolean(toRestore)}
        title={`Restore version ${toRestore?.number}?`}
        description={toRestore ? `This creates a NEW latest version with the contents of version ${toRestore.number}. No version is deleted, and you can restore any other version later.` : ''}
        confirmLabel="Restore"
        destructive={false}
        loading={restoring}
        onConfirm={restore}
        onCancel={() => setToRestore(null)}
      />
    </Card>
  )
}
