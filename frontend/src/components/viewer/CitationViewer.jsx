import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, ExternalLink, FileText, Highlighter, Loader2 } from 'lucide-react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { documentService } from '../../services'
import { openDocumentPreview } from '../../utils/preview'

// In-app PDF viewer for citations. Pages are rendered by the backend, so the highlight rectangles (fractions of the
// page) line up exactly with the image. A highlight is only drawn when the server says it located the passage.
export function CitationViewer({ open, onClose, citations = [], index = 0, onIndexChange }) {
  const citation = citations[index]
  const documentId = citation?.documentId
  const [page, setPage] = useState(citation?.page ?? 1)
  const [pageInput, setPageInput] = useState(String(citation?.page ?? 1))
  const [totalPages, setTotalPages] = useState(null)
  const [image, setImage] = useState({ url: null, loading: false, error: null })
  const [hl, setHl] = useState({ data: null, loading: false, error: null })

  // Jump to the cited page whenever another citation is chosen.
  useEffect(() => {
    if (!citation) return
    setPage(citation.page ?? 1)
    setPageInput(String(citation.page ?? 1))
  }, [citation?.documentId, citation?.page, citation?.chunkId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open || !documentId) return undefined
    let live = true
    setTotalPages(null)
    documentService
      .getDocument(documentId)
      .then((d) => live && setTotalPages(d.pages))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [open, documentId])

  useEffect(() => {
    if (!open || !documentId || !page) return undefined
    const ctl = new AbortController()
    let url = null
    setImage({ url: null, loading: true, error: null })
    documentService
      .getPageImage(documentId, page, { signal: ctl.signal, versionId: citation?.versionId })
      .then((u) => {
        url = u
        if (ctl.signal.aborted) URL.revokeObjectURL(u)
        else setImage({ url: u, loading: false, error: null })
      })
      .catch((error) => !ctl.signal.aborted && setImage({ url: null, loading: false, error }))
    return () => {
      ctl.abort()
      if (url) URL.revokeObjectURL(url)
    }
  }, [open, documentId, page, citation?.versionId])

  useEffect(() => {
    if (!open || !documentId || !citation?.chunkId) {
      setHl({ data: null, loading: false, error: null })
      return undefined
    }
    const ctl = new AbortController()
    setHl({ data: null, loading: true, error: null })
    documentService
      .getCitationHighlights(documentId, citation.chunkId, { signal: ctl.signal })
      .then((data) => !ctl.signal.aborted && setHl({ data, loading: false, error: null }))
      .catch((error) => !ctl.signal.aborted && setHl({ data: null, loading: false, error }))
    return () => ctl.abort()
  }, [open, documentId, citation?.chunkId])

  const goTo = (n) => {
    const max = totalPages ?? Infinity
    const next = Math.min(Math.max(1, Math.round(n)), max)
    setPage(next)
    setPageInput(String(next))
  }

  const rects = useMemo(() => (hl.data?.reliable && hl.data.page === page ? hl.data.rects : []), [hl.data, page])

  if (!citation) return null
  const onCitedPage = citation.page === page

  const openFull = async () => {
    try {
      await openDocumentPreview(documentId, page, citation.versionId)
    } catch {
      /* the viewer stays open */
    }
  }

  const note = citation.plain
    ? 'Browse the document page by page.'
    : !citation.chunkId
    ? 'Opened at the cited page. This older answer has no stored passage position, so nothing is highlighted.'
    : hl.loading
      ? 'Locating the passage…'
      : hl.error
        ? 'Could not locate the passage, showing the cited page only.'
        : hl.data?.reliable
          ? onCitedPage
            ? 'The supporting passage is highlighted.'
            : 'The cited passage is on a different page.'
          : 'The exact position of the passage could not be determined reliably, so no highlight is shown. The cited page is open.'

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title={citation.documentName || 'Source document'}
      description={citation.plain ? `Page ${page}${totalPages ? ` of ${totalPages}` : ''}` : `Source ${index + 1} of ${citations.length} · cited page ${citation.page}`}
      footer={
        <>
          <Button variant="secondary" onClick={openFull}>
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            Open full PDF
          </Button>
          <Button onClick={onClose}>Close</Button>
        </>
      }
    >
      {citations.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-2" role="tablist" aria-label="Sources in this answer">
          {citations.map((c, i) => (
            <button
              key={`${c.documentId}-${c.page}-${i}`}
              type="button"
              role="tab"
              aria-selected={i === index}
              onClick={() => onIndexChange?.(i)}
              className={`inline-flex max-w-[16rem] items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
                i === index ? 'border-brand-300 bg-brand-50 text-brand-700' : 'border-line bg-surface text-ink hover:bg-stone-50'
              }`}
            >
              <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">
                {i + 1}. {c.documentName || 'Document'} · p.{c.page}
              </span>
            </button>
          ))}
        </div>
      )}

      {(citation.versionNumber != null || citation.historical) && (
        <p className={`mb-3 rounded-control px-3 py-2 text-sm ${citation.versionIsCurrent === false || citation.historical ? 'border border-gold-400/40 bg-gold-100 text-ink' : 'bg-stone-50 text-muted'}`} role="status">
          {citation.versionIsCurrent === false || citation.historical
            ? `You are viewing ${citation.versionNumber != null ? `version ${citation.versionNumber}` : 'a version'}, an earlier version of this document. It is the exact file this was taken from, not the latest one.`
            : `Version ${citation.versionNumber} (current).`}
        </p>
      )}

      {citation.excerpt && (
        <blockquote className="mb-3 rounded-control border-l-4 border-amber-300 bg-amber-50 px-3 py-2 text-sm italic text-stone-700">
          “{citation.excerpt}”
        </blockquote>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button size="sm" variant="secondary" onClick={() => goTo(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        <form
          className="flex items-center gap-1.5 text-sm"
          onSubmit={(e) => {
            e.preventDefault()
            const n = Number(pageInput)
            if (Number.isFinite(n) && n > 0) goTo(n)
          }}
        >
          <label htmlFor="viewer-page" className="sr-only">
            Page number
          </label>
          <input
            id="viewer-page"
            inputMode="numeric"
            value={pageInput}
            onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ''))}
            onBlur={() => setPageInput(String(page))}
            className="h-8 w-14 rounded-control border border-line bg-surface text-center text-sm"
          />
          <span className="text-muted">of {totalPages ?? '…'}</span>
        </form>
        <Button size="sm" variant="secondary" onClick={() => goTo(page + 1)} disabled={totalPages != null && page >= totalPages} aria-label="Next page">
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
        {!citation.plain && !onCitedPage && (
          <Button size="sm" variant="ghost" onClick={() => goTo(citation.page)}>
            Back to cited page
          </Button>
        )}
        <p className="flex w-full items-center gap-1.5 text-xs text-muted sm:ml-auto sm:w-auto" role="status">
          {hl.loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Highlighter className="h-3.5 w-3.5" aria-hidden="true" />}
          {note}
        </p>
      </div>

      <div className="max-h-[60vh] overflow-auto rounded-control border border-line bg-stone-100 p-2">
        {image.loading && (
          <div className="flex h-64 items-center justify-center text-muted" role="status">
            <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
            <span className="sr-only">Loading page…</span>
          </div>
        )}
        {image.error && (
          <p role="alert" className="p-6 text-center text-sm text-danger">
            {image.error.message || 'This page could not be loaded.'}
          </p>
        )}
        {image.url && (
          <div className="relative mx-auto w-full max-w-[820px] shadow-card">
            <img src={image.url} alt={`Page ${page} of ${citation.documentName || 'the document'}`} className="block w-full select-none" draggable="false" />
            {rects.map((r, i) => (
              <span
                key={i}
                data-testid="citation-highlight"
                aria-hidden="true"
                className="pointer-events-none absolute rounded-sm bg-amber-300/50 mix-blend-multiply ring-1 ring-amber-400/60"
                style={{ left: `${r.x * 100}%`, top: `${r.y * 100}%`, width: `${r.w * 100}%`, height: `${r.h * 100}%` }}
              />
            ))}
          </div>
        )}
      </div>
    </Modal>
  )
}
