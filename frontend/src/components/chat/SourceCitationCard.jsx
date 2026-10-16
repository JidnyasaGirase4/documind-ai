import { ExternalLink, FileText } from 'lucide-react'

// Renders only what the API returned. A missing page or excerpt is simply omitted.
export function SourceCitationCard({ citation, index, onOpen }) {
  const { documentName, page, excerpt, documentId, versionNumber, versionIsCurrent } = citation
  const canOpen = Boolean(documentId && onOpen)
  const title = documentName || 'Source document'

  const body = (
    <>
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-brand-50 text-[13px] font-semibold text-brand-700">
          {index + 1}
        </span>
        <FileText className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
        <span className="min-w-0 flex-1 break-words text-sm font-medium text-ink sm:truncate">{title}</span>
        {versionNumber != null && (
          <span className={`shrink-0 text-xs ${versionIsCurrent === false ? 'font-medium text-gold-600' : 'text-muted'}`}>
            v{versionNumber}
            {versionIsCurrent === false ? ' (earlier version)' : ''}
          </span>
        )}
        {page != null && <span className="shrink-0 text-xs text-muted">Page {page}</span>}
        {canOpen && <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted" aria-hidden="true" />}
      </div>
      {excerpt && <p className="mt-1.5 line-clamp-3 text-left text-xs italic text-stone-600">“{excerpt}”</p>}
    </>
  )

  const base = 'block w-full rounded-control border border-line bg-stone-50 p-2.5'
  return canOpen ? (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      aria-label={`Open ${title}${versionNumber != null ? `, version ${versionNumber}` : ''}${page != null ? `, page ${page}` : ''}`}
      className={`${base} text-left transition-colors hover:border-brand-200 hover:bg-brand-50`}
    >
      {body}
    </button>
  ) : (
    <div className={base}>{body}</div>
  )
}
