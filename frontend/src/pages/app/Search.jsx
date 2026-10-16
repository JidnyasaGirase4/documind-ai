import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FileText, Loader2, Search as SearchIcon, SearchX, Users, X } from 'lucide-react'
import { PageHeader } from '../../components/common/PageHeader'
import { Select } from '../../components/common/Field'
import { Pagination } from '../../components/common/Pagination'
import { EmptyState } from '../../components/common/EmptyState'
import { ErrorState } from '../../components/common/ErrorState'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { ListSkeleton } from '../../components/common/LoadingSkeleton'
import { Highlighted } from '../../utils/highlight'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { knowledgeService, searchService } from '../../services'
import { cx, pluralize } from '../../utils/format'

const MODES = [
  { id: 'hybrid', label: 'Hybrid', hint: 'Keywords and meaning combined' },
  { id: 'keyword', label: 'Keyword', hint: 'Exact words and "phrases"' },
  { id: 'semantic', label: 'Semantic', hint: 'Finds passages with a similar meaning' },
]
const SORTS = { relevance: 'Most relevant', newest: 'Newest first', title: 'Title A–Z' }
const WARNINGS = {
  semantic_unavailable: 'Semantic search is unavailable right now, so these are keyword results only.',
  relaxed_to_any_term: 'No document contained every word, so these results contain at least one of them.',
}
const PAGE_SIZE = 10

function ResultCard({ item, terms, phrases }) {
  const first = item.passages[0]
  const link = (p) => `/app/documents/${item.documentId}${p ? `?page=${p.page}&chunk=${encodeURIComponent(p.chunkId)}` : ''}`
  return (
    <li>
      <Card interactive className="animate-fade-in-up">
        <div className="flex items-start gap-3">
          <span className="icon-tile h-10 w-10 shrink-0">
            <FileText className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <Link to={link(first)} className="block break-words font-semibold text-ink hover:text-brand-700 hover:underline">
              <Highlighted text={item.title} terms={terms} phrases={phrases} />
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
              {item.pages ? <span>{pluralize(item.pages, 'page')}</span> : null}
              {item.category && <Badge tone="brand">{item.category.name}</Badge>}
              {item.tags.map((t) => (
                <Badge key={t.id}>#{t.name}</Badge>
              ))}
              {item.collections.map((c) => (
                <Badge key={c.id} icon={Users}>
                  {c.name}
                </Badge>
              ))}
              {item.role !== 'owner' && <Badge tone="success">Shared · {item.role}</Badge>}
            </div>
          </div>
        </div>

        {item.passages.length > 0 ? (
          <ul className="mt-3 space-y-2" aria-label={`Matching passages in ${item.title}`}>
            {item.passages.map((p) => (
              <li key={p.chunkId} className="rounded-control border border-line bg-stone-50 p-3">
                <p className="text-[15px] leading-relaxed text-ink">
                  <Highlighted text={p.snippet} terms={terms} phrases={phrases} />
                </p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                  <span className="flex flex-wrap items-center gap-2">
                    <Link to={link(p)} className="font-medium text-brand-700 hover:underline">
                      Open page {p.page}
                    </Link>
                    {p.keywordMatch && <span>keyword match</span>}
                    {p.similarity !== null && (
                      <span title="Raw embedding cosine similarity. It is not a probability or a confidence value.">semantic similarity {p.similarity.toFixed(2)}</span>
                    )}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">Matched on {item.matchedOn.join(', ')}.</p>
        )}
      </Card>
    </li>
  )
}

export default function SearchPage() {
  useDocumentTitle('Search')
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const mode = MODES.some((m) => m.id === params.get('mode')) ? params.get('mode') : 'hybrid'
  const collectionId = params.get('collection') ?? ''
  const categoryId = params.get('category') ?? ''
  const tagId = params.get('tag') ?? ''
  const sortBy = SORTS[params.get('sort')] ? params.get('sort') : 'relevance'
  const page = Math.max(1, Number(params.get('page')) || 1)
  const [text, setText] = useState(q)
  const inputRef = useRef(null)

  // Keep the box in step with the URL (back/forward, header search box).
  useEffect(() => setText(q), [q])

  const update = (patch, { keepPage = false } = {}) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(patch)) {
      if (v === '' || v === null || v === undefined) next.delete(k)
      else next.set(k, v)
    }
    if (!keepPage) next.delete('page')
    setParams(next)
  }

  const filters = useAsync(
    () =>
      Promise.all([knowledgeService.listCollections({ pageSize: 100, sortBy: 'name', sortOrder: 'asc' }), knowledgeService.listCategories(), knowledgeService.listTags()]).then(
        ([collections, categories, tags]) => ({ collections: collections.items, categories, tags }),
      ),
    [],
  )
  const opts = filters.data

  const results = useAsync(
    () => (q.trim() ? searchService.search({ query: q, mode, collectionId, categoryId, tagId, sortBy, page, pageSize: PAGE_SIZE }) : Promise.resolve(null)),
    [q, mode, collectionId, categoryId, tagId, sortBy, page],
  )

  const submit = (e) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) {
      inputRef.current?.focus()
      return
    }
    if (trimmed === q) results.reload()
    else update({ q: trimmed })
  }

  const hasFilters = Boolean(collectionId || categoryId || tagId)
  const clearFilters = () => update({ collection: '', category: '', tag: '' })
  const data = results.data

  return (
    <>
      <PageHeader title="Search" description="Find passages across every document you can access, without opening a conversation." />

      <form onSubmit={submit} role="search" aria-label="Search documents" className="space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <label htmlFor="search-box" className="sr-only">
              Search query
            </label>
            <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              id="search-box"
              ref={inputRef}
              type="search"
              value={text}
              maxLength={300}
              autoFocus={!q}
              onChange={(e) => setText(e.target.value)}
              placeholder='Try: parental leave, or "retention policy"'
              className="h-12 w-full rounded-control border border-line bg-surface pl-11 pr-10 text-base text-ink shadow-card placeholder:text-stone-400 [&::-webkit-search-cancel-button]:hidden"
            />
            {text && (
              <button
                type="button"
                aria-label="Clear search text"
                onClick={() => {
                  setText('')
                  inputRef.current?.focus()
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-muted hover:text-ink"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
          <Button type="submit" size="lg" loading={results.loading && Boolean(q)}>
            Search
          </Button>
        </div>

        <div role="radiogroup" aria-label="Search mode" className="flex flex-wrap gap-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="radio"
              aria-checked={mode === m.id}
              title={m.hint}
              onClick={() => update({ mode: m.id === 'hybrid' ? '' : m.id })}
              className={cx(
                'rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors',
                mode === m.id ? 'border-brand-600 bg-brand-600 text-white' : 'border-line bg-surface text-ink hover:bg-stone-50',
              )}
            >
              {m.label}
            </button>
          ))}
          <span className="self-center text-xs text-muted">{MODES.find((m) => m.id === mode).hint}</span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Select label="Collection" labelHidden value={collectionId} onChange={(e) => update({ collection: e.target.value })}>
            <option value="">All collections</option>
            {opts?.collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.role !== 'owner' ? ' (shared)' : ''}
              </option>
            ))}
          </Select>
          <Select label="Category" labelHidden value={categoryId} onChange={(e) => update({ category: e.target.value })}>
            <option value="">All categories</option>
            <option value="0">Uncategorised</option>
            {opts?.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Select label="Tag" labelHidden value={tagId} onChange={(e) => update({ tag: e.target.value })}>
            <option value="">All tags</option>
            {opts?.tags.map((t) => (
              <option key={t.id} value={t.id}>
                #{t.name}
              </option>
            ))}
          </Select>
          <Select label="Sort results" labelHidden value={sortBy} onChange={(e) => update({ sort: e.target.value === 'relevance' ? '' : e.target.value })}>
            {Object.entries(SORTS).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
          <span>File type: PDF (the only supported type)</span>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="h-3.5 w-3.5" aria-hidden="true" />
              Clear filters
            </Button>
          )}
        </div>
      </form>

      <div className="mt-5" aria-live="polite">
        {!q.trim() ? (
          <EmptyState icon={SearchIcon} title="Search your knowledge base" description="Type a word, a question or an exact phrase in quotes. Results come only from documents you own or that were shared with you." />
        ) : results.loading || (!data && !results.error) ? (
          <div role="status">
            <p className="mb-3 flex items-center gap-2 text-sm text-muted">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Searching…
            </p>
            <ListSkeleton rows={3} />
          </div>
        ) : results.error ? (
          <ErrorState error={results.error} title={results.error.status === 422 ? 'Check your search' : undefined} onRetry={results.error.status === 422 ? undefined : results.reload} />
        ) : data.items.length === 0 ? (
          <EmptyState
            icon={SearchX}
            title="No results"
            description={hasFilters ? 'Nothing matched with these filters. Try removing a filter or using different words.' : 'Try fewer or different words, or switch to Semantic mode to search by meaning.'}
            action={
              hasFilters ? (
                <Button variant="secondary" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        ) : (
          <>
            {data.warnings.map((w) => (
              <p key={w} role="status" className="mb-3 rounded-control border border-gold-400/40 bg-gold-100 px-3 py-2 text-sm text-ink">
                {WARNINGS[w] ?? w}
              </p>
            ))}
            <p className="mb-3 text-sm text-muted">
              {data.totalExact ? data.total : `${data.total}+`} {data.total === 1 ? 'document' : 'documents'} · ranked by{' '}
              {sortBy === 'relevance' ? (data.ranking?.method === 'rrf' ? 'combined keyword and semantic rank' : data.ranking?.method === 'semantic' ? 'semantic similarity' : 'keyword match') : SORTS[sortBy].toLowerCase()}
            </p>
            <ul className="space-y-3" aria-label="Search results">
              {data.items.map((item) => (
                <ResultCard key={item.documentId} item={item} terms={data.terms} phrases={data.phrases} />
              ))}
            </ul>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.pageSize} onChange={(p) => update({ page: p === 1 ? '' : p }, { keepPage: true })} noun="documents" />
          </>
        )}
      </div>
    </>
  )
}
