import { AlertCircle, Copy, RotateCw, Sparkles } from 'lucide-react'
import { SourceCitationCard } from './SourceCitationCard'
import { formatDateTime } from '../../utils/format'

const MARKER = /\[S(\d+)\]/g
const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/

// Turns "[S1]" markers into small numbered badges that open the matching source.
function withCitations(text, citations, onOpen) {
  const out = []
  let last = 0
  for (const m of text.matchAll(MARKER)) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const n = Number(m[1])
    const citation = citations?.[n - 1]
    out.push(
      <button
        key={`${m.index}-${n}`}
        type="button"
        disabled={!citation || !onOpen}
        onClick={() => citation && onOpen?.(citation)}
        title={citation ? `Source ${n}: ${citation.documentName ?? 'document'}, page ${citation.page}` : undefined}
        className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-0.5 items-center justify-center rounded-full bg-brand-50 px-1 text-[11px] font-semibold leading-none text-brand-700 ring-1 ring-brand-200 enabled:hover:bg-brand-100 disabled:cursor-default"
      >
        {n}
      </button>,
    )
    last = m.index + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

// Paragraphs and bullet lists, instead of one block of raw text.
function AnswerText({ content, citations, onOpen }) {
  const blocks = String(content ?? '')
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)
  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        const lines = block.split('\n').filter((l) => l.trim())
        if (lines.length > 0 && lines.every((l) => BULLET.test(l))) {
          return (
            <ul key={i} className="list-disc space-y-1.5 pl-5 marker:text-brand-500">
              {lines.map((l, j) => (
                <li key={j}>{withCitations(l.replace(BULLET, ''), citations, onOpen)}</li>
              ))}
            </ul>
          )
        }
        return <p key={i}>{withCitations(lines.join(' '), citations, onOpen)}</p>
      })}
    </div>
  )
}

// message: { role, content, citations[], followUps[], createdAt, status?: 'sending' | 'failed' }
export function ChatMessage({ message, onCopy, onRetry, onOpenCitation, onFollowUp }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex animate-fade-in-up flex-col items-end">
        <div
          className={`max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md px-4 py-3 text-sm text-white sm:max-w-[75%] ${
            message.status === 'failed' ? 'bg-danger' : 'bg-gradient-to-br from-brand-500 to-brand-600 shadow-btn'
          } ${message.status === 'sending' ? 'opacity-70' : ''}`}
        >
          {message.content}
        </div>
        {message.status === 'failed' ? (
          <div className="mt-1.5 flex items-center gap-2 text-xs text-danger" role="alert">
            <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{message.error || 'Message failed to send.'}</span>
            {onRetry && (
              <button type="button" onClick={() => onRetry(message)} className="inline-flex items-center gap-1 rounded font-medium underline">
                <RotateCw className="h-3 w-3" aria-hidden="true" />
                Retry
              </button>
            )}
          </div>
        ) : (
          message.createdAt && <p className="mt-1 text-[13px] text-muted">{formatDateTime(message.createdAt)}</p>
        )}
      </div>
    )
  }

  return (
    <div className="flex animate-fade-in-up gap-3">
      <span className="icon-tile mt-0.5 h-9 w-9 !rounded-full">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="break-words rounded-2xl rounded-tl-md border border-line bg-surface px-4 py-3.5 text-[15px] leading-relaxed text-ink shadow-card">
          <AnswerText content={message.content} citations={message.citations} onOpen={onOpenCitation} />
        </div>

        {message.citations?.length > 0 && (
          <section className="mt-2.5" aria-label="Sources">
            <h3 className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted">Sources</h3>
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {message.citations.map((c, i) => (
                <li key={`${c.documentId}-${c.page}-${c.chunkId ?? i}`}>
                  <SourceCitationCard citation={c} index={i} onOpen={onOpenCitation} />
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {message.createdAt && <span className="whitespace-nowrap">{formatDateTime(message.createdAt)}</span>}
          {onCopy && (
            <button
              type="button"
              onClick={() => onCopy(message.content)}
              className="inline-flex items-center gap-1 whitespace-nowrap rounded px-1 py-0.5 hover:bg-stone-100 hover:text-ink"
            >
              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
              Copy answer
            </button>
          )}
        </div>

        {message.followUps?.length > 0 && onFollowUp && (
          <div className="mt-2.5 flex flex-wrap gap-2" role="group" aria-label="Suggested follow-up questions">
            {message.followUps.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => onFollowUp(q)}
                className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-left text-xs font-medium text-brand-700 hover:bg-brand-100"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
