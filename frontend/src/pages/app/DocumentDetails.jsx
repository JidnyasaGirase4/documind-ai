import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, BookOpen, ExternalLink, FolderTree, MessageSquareText, RotateCw, Trash2 } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { Card } from '../../components/common/Card'
import { Button } from '../../components/common/Button'
import { ErrorState } from '../../components/common/ErrorState'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { Skeleton } from '../../components/common/LoadingSkeleton'
import { DocumentStatusBadge, isInProgress } from '../../components/documents/DocumentStatusBadge'
import { JobProgress } from '../../components/documents/JobProgress'
import { Badge } from '../../components/common/Badge'
import { OrganizeDocumentDialog } from '../../components/knowledge/OrganizeDocumentDialog'
import { DocumentReviewPanel } from '../../components/reviews/DocumentReviewPanel'
import { DocumentConflictsPanel } from '../../components/reviews/DocumentConflictsPanel'
import { VersionHistory } from '../../components/versions/VersionHistory'
import { CitationViewer } from '../../components/viewer/CitationViewer'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { usePolling } from '../../hooks/usePolling'
import { useToast } from '../../context/ToastContext'
import { documentService } from '../../services'
import { DOCUMENT_POLL_INTERVAL_MS } from '../../utils/config'
import { formatBytes, formatDateTime } from '../../utils/format'
import { openDocumentPreview } from '../../utils/preview'

function Meta({ label, children }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children}</dd>
    </div>
  )
}

export default function DocumentDetails() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: doc, error, loading, reload } = useAsync(() => documentService.getDocument(documentId), [documentId])
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [busy, setBusy] = useState('')
  const [searchParams] = useSearchParams()
  const targetPage = Number(searchParams.get('page')) || null
  const targetChunk = searchParams.get('chunk')
  const targetVersion = Number(searchParams.get('version')) || null
  const [viewerOpen, setViewerOpen] = useState(Boolean(targetPage)) // arriving from a search result opens that page
  const [organizeOpen, setOrganizeOpen] = useState(false)
  const [viewVersion, setViewVersion] = useState(null) // a specific version opened from the history
  useDocumentTitle(doc?.filename || 'Document')

  usePolling(() => reload({ silent: true }), DOCUMENT_POLL_INTERVAL_MS, Boolean(doc && isInProgress(doc.status)))

  const preview = async () => {
    setBusy('preview')
    try {
      await openDocumentPreview(doc.id)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy('')
    }
  }

  const retry = async () => {
    setBusy('retry')
    try {
      await documentService.retryDocument(doc.id)
      toast.success('Processing restarted.')
      reload({ silent: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy('')
    }
  }

  const remove = async () => {
    setBusy('delete')
    try {
      await documentService.deleteDocument(doc.id)
      toast.success('Document deleted.')
      navigate('/app/documents', { replace: true })
    } catch (err) {
      toast.error(err.message)
      setBusy('')
      setConfirmOpen(false)
    }
  }

  const back = (
    <Button to="/app/documents" variant="ghost" size="sm" className="mb-3 -ml-2">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      Back to documents
    </Button>
  )

  if (loading) {
    return (
      <>
        {back}
        <Skeleton className="mb-6 h-8 w-1/2" />
        <Skeleton className="h-48 w-full" />
      </>
    )
  }
  if (error) {
    return (
      <>
        {back}
        <ErrorState error={error} title={error.status === 404 ? 'Document not found' : undefined} onRetry={error.status === 404 ? undefined : reload} />
      </>
    )
  }

  return (
    <>
      {back}
      <PageHeader
        title={doc.filename}
        breadcrumbs={[{ label: 'My Documents', to: '/app/documents' }, { label: doc.filename }]}
        actions={
          <>
            {doc.status === 'ready' && (
              <Button to="/app/assistant" variant="secondary">
                <MessageSquareText className="h-4 w-4" aria-hidden="true" />
                Ask about this
              </Button>
            )}
            {doc.status === 'ready' && (
              <Button variant="secondary" onClick={() => setViewerOpen(true)}>
                <BookOpen className="h-4 w-4" aria-hidden="true" />
                View pages
              </Button>
            )}
            {doc.role !== 'viewer' && (
            <Button variant="secondary" onClick={() => setOrganizeOpen(true)}>
              <FolderTree className="h-4 w-4" aria-hidden="true" />
              Organize
            </Button>
            )}
            <Button variant="secondary" onClick={preview} loading={busy === 'preview'}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              Open PDF
            </Button>
            {doc.isOwner && (
              <Button variant="dangerGhost" onClick={() => setConfirmOpen(true)}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
            )}
          </>
        }
      />

      <Card>
        <div className="mb-5 flex items-center gap-3">
          <DocumentStatusBadge status={doc.status} />
          {isInProgress(doc.status) && <span className="text-sm text-muted">Processing can take a while for large files. This page updates automatically.</span>}
        </div>

        {isInProgress(doc.status) && <JobProgress doc={doc} />}

        {!doc.isOwner && (
          <p className="mb-4 text-sm text-muted">
            This document is shared with you through a collection. Your permission: <strong>{doc.role}</strong>.
          </p>
        )}

        {doc.status === 'failed' && (
          <div role="alert" className="mb-5 rounded-control border border-danger/20 bg-danger-soft p-4">
            <p className="text-sm font-medium text-danger">Processing failed</p>
            <p className="mt-1 text-sm text-stone-700">{doc.error || 'No details were provided by the server.'}</p>
            {doc.role !== 'viewer' && (
            <Button className="mt-3" size="sm" variant="secondary" onClick={retry} loading={busy === 'retry'}>
              <RotateCw className="h-4 w-4" aria-hidden="true" />
              Retry processing
            </Button>
            )}
          </div>
        )}

        <dl className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Meta label="File name">
            <span className="break-all">{doc.filename}</span>
          </Meta>
          <Meta label="File size">{formatBytes(doc.size)}</Meta>
          <Meta label="Pages">{doc.pages ?? '—'}</Meta>
          <Meta label="Uploaded">{formatDateTime(doc.createdAt)}</Meta>
          <Meta label="Current version">{doc.versionNumber ? `Version ${doc.versionNumber}` : '—'}</Meta>
          <Meta label="Category">{doc.category ? <Badge tone="brand">{doc.category.name}</Badge> : <span className="text-muted">None</span>}</Meta>
          <Meta label="Tags">
            {doc.tags.length ? (
              <span className="flex flex-wrap gap-1.5">
                {doc.tags.map((t) => (
                  <Badge key={t.id}>#{t.name}</Badge>
                ))}
              </span>
            ) : (
              <span className="text-muted">None</span>
            )}
          </Meta>
        </dl>
      </Card>

      <OrganizeDocumentDialog
        open={organizeOpen}
        doc={doc}
        onClose={() => setOrganizeOpen(false)}
        onSave={async (values) => {
          await documentService.updateMetadata(doc.id, values)
          toast.success('Document updated.')
          setOrganizeOpen(false)
          reload({ silent: true })
        }}
      />

      <div className="mt-6">
        <DocumentReviewPanel documentId={doc.id} canManage={doc.role !== 'viewer'} />
      </div>

      <div className="mt-6">
        <DocumentConflictsPanel documentId={doc.id} canManage={doc.role !== 'viewer'} ready={doc.status === 'ready'} />
      </div>

      <div className="mt-6">
        <VersionHistory
          documentId={doc.id}
          canManage={doc.role !== 'viewer'}
          onChanged={() => reload({ silent: true })}
          onOpenVersion={(v) => {
            setViewVersion(v)
            setViewerOpen(true)
          }}
        />
      </div>

      <CitationViewer
        open={viewerOpen}
        onClose={() => {
          setViewerOpen(false)
          setViewVersion(null)
        }}
        citations={viewVersion ? [{ documentId: doc.id, documentName: doc.filename, page: 1, plain: true, versionId: viewVersion.id, versionNumber: viewVersion.number, historical: !viewVersion.isCurrent }] : [targetPage ? { documentId: doc.id, documentName: doc.filename, page: targetPage, chunkId: targetChunk || undefined, plain: !targetChunk, versionId: targetVersion || undefined, historical: Boolean(targetVersion) } : { documentId: doc.id, documentName: doc.filename, page: 1, plain: true }]}
        index={0}
      />

      <ConfirmDialog
        open={confirmOpen}
        title="Delete this document?"
        description={`"${doc.filename}" and its indexed content will be permanently removed. This cannot be undone.`}
        loading={busy === 'delete'}
        onConfirm={remove}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  )
}
