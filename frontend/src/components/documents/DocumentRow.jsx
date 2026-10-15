import { Link } from 'react-router-dom'
import { Eye, FileText, MoreVertical, RotateCw, Trash2 } from 'lucide-react'
import { DocumentStatusBadge } from './DocumentStatusBadge'
import { Dropdown } from '../common/Dropdown'
import { Tooltip } from '../common/Tooltip'
import { formatBytes, formatDate } from '../../utils/format'

// Responsive list row: on phones the name gets the full width and the status/actions sit
// underneath; from the sm breakpoint everything is on one line.
export function DocumentRow({ doc, onDelete, onRetry, onPreview, busy }) {
  const items = [
    { label: 'View details', icon: Eye, onClick: onPreview },
    ...(doc.status === 'failed' ? [{ label: 'Retry processing', icon: RotateCw, onClick: () => onRetry(doc), disabled: busy }] : []),
    { label: 'Delete', icon: Trash2, danger: true, onClick: () => onDelete(doc) },
  ]

  return (
    <li className="hover-lift relative flex focus-within:z-30 animate-fade-in-up flex-col gap-3 rounded-card border border-line bg-surface p-4 shadow-card hover:border-brand-200 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center sm:gap-4">
        <span className="icon-tile h-11 w-11">
          <FileText className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <Link to={`/app/documents/${doc.id}`} className="block break-words font-medium text-ink hover:text-brand-700 hover:underline sm:truncate">
            {doc.filename}
          </Link>
          <p className="mt-0.5 text-xs text-muted">
            {formatBytes(doc.size)} · Uploaded {formatDate(doc.createdAt)}
            {doc.pages ? ` · ${doc.pages} pages` : ''}
          </p>
          {doc.status === 'failed' && doc.error && <p className="mt-1 text-xs text-danger">{doc.error}</p>}
        </div>
      </div>
      <div className="flex shrink-0 items-center justify-between gap-2 border-t border-line pt-3 sm:justify-end sm:border-0 sm:pt-0">
        <DocumentStatusBadge status={doc.status} />
        <Dropdown
          label={`Actions for ${doc.filename}`}
          trigger={(props) => (
            <Tooltip text="Actions">
              <button type="button" {...props} className="rounded-md p-2 text-muted hover:bg-stone-100 hover:text-ink">
                <MoreVertical className="h-4 w-4" />
              </button>
            </Tooltip>
          )}
          items={items}
        />
      </div>
    </li>
  )
}
