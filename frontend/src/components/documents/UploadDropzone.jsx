import { useRef, useState } from 'react'
import { CheckCircle2, Loader2, UploadCloud, XCircle } from 'lucide-react'
import { ACCEPTED_TYPE_LABEL, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from '../../utils/config'
import { validatePdf } from '../../utils/validation'
import { cx } from '../../utils/format'

// `uploads` is the controlled list of in-flight/finished uploads:
//   [{ id, name, progress, state: 'uploading' | 'done' | 'error', error? }]
// Files are validated client-side for fast feedback only; the backend re-validates.
export function UploadDropzone({ onFiles, uploads = [], disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [rejections, setRejections] = useState([])

  const handle = (fileList) => {
    const files = [...fileList]
    const valid = []
    const rejected = []
    for (const f of files) {
      const err = validatePdf(f, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB)
      if (err) rejected.push(err)
      else valid.push(f)
    }
    setRejections(rejected)
    if (valid.length) onFiles(valid)
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (!disabled) handle(e.dataTransfer.files)
        }}
        className={cx(
          'flex flex-col items-center rounded-card border-2 border-dashed px-6 py-10 text-center transition-all duration-200',
          dragging ? 'scale-[1.01] border-brand-500 bg-brand-50 shadow-glow' : 'border-stone-300 bg-surface hover:border-brand-300 hover:bg-brand-50/40',
        )}
      >
        <span className="icon-tile mb-4 h-14 w-14">
          <UploadCloud className={`h-7 w-7 ${dragging ? 'animate-bounce' : ''}`} aria-hidden="true" />
        </span>
        <p className="font-display text-base font-bold text-ink">Drag and drop PDF files here</p>
        <p className="mt-1 text-xs text-muted">
          Supported type: {ACCEPTED_TYPE_LABEL} · Up to {MAX_UPLOAD_MB} MB per file
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="sr-only"
          tabIndex={-1}
          aria-label="Choose PDF files to upload"
          data-testid="file-input"
          onChange={(e) => {
            handle(e.target.files)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="mt-4 inline-flex h-10 items-center rounded-control bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          Choose files
        </button>
      </div>

      {rejections.length > 0 && (
        <ul role="alert" className="mt-3 space-y-1 rounded-control bg-danger-soft p-3 text-sm text-danger">
          {rejections.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}

      {uploads.length > 0 && (
        <ul className="mt-3 space-y-2" aria-label="Uploads">
          {uploads.map((u) => (
            <li key={u.id} className="rounded-control border border-line bg-surface p-3 text-sm">
              <div className="flex items-center gap-2">
                {u.state === 'uploading' && <Loader2 className="h-4 w-4 animate-spin text-brand-600" aria-hidden="true" />}
                {u.state === 'done' && <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />}
                {u.state === 'error' && <XCircle className="h-4 w-4 text-danger" aria-hidden="true" />}
                <span className="min-w-0 flex-1 truncate">{u.name}</span>
                <span className="text-xs text-muted">
                  {u.state === 'uploading' && `${u.progress}%`}
                  {u.state === 'done' && 'Uploaded'}
                  {u.state === 'error' && 'Failed'}
                </span>
              </div>
              {u.state === 'uploading' && (
                <div
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-stone-100"
                  role="progressbar"
                  aria-label={`Uploading ${u.name}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={u.progress}
                >
                  <div className="h-full bg-brand-600 transition-all" style={{ width: `${u.progress}%` }} />
                </div>
              )}
              {u.state === 'error' && <p className="mt-1 text-xs text-danger">{u.error}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
