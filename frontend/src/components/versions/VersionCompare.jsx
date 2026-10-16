import { ArrowLeft, Info, Minus, Plus } from 'lucide-react'
import { Button } from '../common/Button'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { formatDateTime } from '../../utils/format'

function Inline({ parts, side }) {
  // side 'old' shows equal + deleted words, 'new' shows equal + inserted words.
  return parts.map((p, i) => {
    if (p.op === 'equal') return <span key={i}>{p.text}</span>
    if (p.op === 'del' && side === 'old') return <del key={i} className="rounded bg-rose-200/70 px-0.5 text-rose-900 decoration-rose-700">{p.text}</del>
    if (p.op === 'ins' && side === 'new') return <ins key={i} className="rounded bg-emerald-200/70 px-0.5 text-emerald-900 no-underline">{p.text}</ins>
    return null
  })
}

function Units({ units, tone }) {
  return units.map((u, i) => (
    <p key={i} className={tone}>
      <span className="mr-2 text-xs text-muted">p.{u.page}</span>
      {u.text}
    </p>
  ))
}

function Block({ block }) {
  if (block.type === 'skipped') {
    return (
      <li className="px-3 py-1 text-center text-xs text-muted">
        … {block.count} unchanged {block.count === 1 ? 'passage' : 'passages'} …
      </li>
    )
  }
  if (block.type === 'equal') {
    return (
      <li className="px-3 py-2 text-sm text-stone-600">
        <Units units={block.new} />
      </li>
    )
  }
  const removed = block.type === 'removed' || block.type === 'changed'
  const added = block.type === 'added' || block.type === 'changed'
  return (
    <li className="space-y-1 py-1">
      <span className="sr-only">{block.type === 'changed' ? 'Changed passage' : block.type === 'added' ? 'Added passage' : 'Removed passage'}</span>
      {removed && (
        <div className="flex gap-2 rounded-control border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-ink">
          <Minus className="mt-0.5 h-4 w-4 shrink-0 text-rose-700" aria-label="Removed" />
          <div className="min-w-0 break-words">
            {block.type === 'changed' ? block.old.map((u, i) => <span key={i} className="mr-1 text-xs text-muted">p.{u.page}</span>).slice(0, 1) : null}
            {block.type === 'changed' ? <Inline parts={block.inline} side="old" /> : <Units units={block.old} />}
          </div>
        </div>
      )}
      {added && (
        <div className="flex gap-2 rounded-control border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-ink">
          <Plus className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" aria-label="Added" />
          <div className="min-w-0 break-words">
            {block.type === 'changed' ? block.new.map((u, i) => <span key={i} className="mr-1 text-xs text-muted">p.{u.page}</span>).slice(0, 1) : null}
            {block.type === 'changed' ? <Inline parts={block.inline} side="new" /> : <Units units={block.new} />}
          </div>
        </div>
      )}
    </li>
  )
}

export function VersionCompare({ result, onBack }) {
  const { from, to, stats } = result
  return (
    <Card>
      <Button variant="ghost" size="sm" className="-ml-2 mb-3" onClick={onBack}>
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to version history
      </Button>
      <h2 className="font-display text-[17px] font-bold text-ink">
        Comparing version {from.number} → version {to.number}
      </h2>
      <p className="mt-1 text-sm text-muted">
        v{from.number} uploaded {formatDateTime(from.createdAt)} · v{to.number} uploaded {formatDateTime(to.createdAt)}
        {to.isCurrent ? ' (current)' : ''}
      </p>
      <p className="mt-3 flex items-start gap-2 rounded-control bg-stone-50 px-3 py-2 text-xs text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {result.notice}
      </p>

      {!result.comparable ? (
        <p role="alert" className="mt-4 rounded-control border border-gold-400/40 bg-gold-100 px-3 py-3 text-sm text-ink">
          These versions cannot be compared reliably. {result.reason}
        </p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-2" aria-label="Summary of changes">
            <Badge tone="success">{stats.added} added</Badge>
            <Badge tone="danger">{stats.removed} removed</Badge>
            <Badge tone="warning">{stats.changed} changed</Badge>
            <Badge>{stats.unchanged} unchanged</Badge>
          </div>
          {stats.identical ? (
            <p className="mt-4 text-sm text-muted">The extracted text of these two versions is identical.</p>
          ) : (
            <ul className="mt-4 max-h-[60vh] space-y-1 overflow-auto rounded-control border border-line p-2" aria-label="Differences">
              {result.blocks.map((b, i) => (
                <Block key={i} block={b} />
              ))}
            </ul>
          )}
        </>
      )}
    </Card>
  )
}
