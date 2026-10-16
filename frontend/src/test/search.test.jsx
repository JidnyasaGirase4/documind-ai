import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from './utils'
import SearchPage from '../pages/app/Search'
import { highlightParts } from '../utils/highlight'
import { knowledgeService, searchService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    searchService: { search: vi.fn() },
    knowledgeService: { listCollections: vi.fn(), listCategories: vi.fn(), listTags: vi.fn() },
  }
})

const passage = (o) => ({ chunkId: 'chunk-7', page: 2, snippet: 'Our document retention policy requires records be kept.', keywordMatch: true, keywordRank: 1, semanticRank: 1, similarity: 0.42, ...o })
const item = (o) => ({ documentId: 5, title: 'records.pdf', score: 0.03, matchedOn: ['text'], passages: [passage()], pages: 4, category: { id: 1, name: 'HR' }, tags: [{ id: 2, name: 'policy' }], collections: [{ id: 3, name: 'Team' }], role: 'viewer', ...o })
const result = (o) => ({ query: 'retention', mode: 'hybrid', terms: ['retention'], phrases: [], items: [item()], total: 1, totalExact: true, page: 1, pageSize: 10, pages: 1, ranking: { method: 'rrf' }, warnings: [], ...o })

function show(route = '/app/search') {
  return renderWithProviders(
    <Routes>
      <Route path="/app/search" element={<SearchPage />} />
    </Routes>,
    { route, withAuth: false },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  knowledgeService.listCollections.mockResolvedValue({ items: [{ id: 3, name: 'Team', role: 'viewer' }], total: 1, page: 1, pageSize: 100, pages: 1 })
  knowledgeService.listCategories.mockResolvedValue([{ id: 1, name: 'HR' }])
  knowledgeService.listTags.mockResolvedValue([{ id: 2, name: 'policy' }])
})

describe('Search page', () => {
  it('shows a helpful empty state before anything is searched and does not call the API', async () => {
    show()
    expect(await screen.findByText('Search your knowledge base')).toBeInTheDocument()
    expect(searchService.search).not.toHaveBeenCalled()
  })

  it('searches on submit (Enter) in hybrid mode and shows highlighted snippets, page link and metadata', async () => {
    searchService.search.mockResolvedValue(result())
    show()
    await userEvent.type(await screen.findByLabelText('Search query'), 'retention{Enter}')
    const list = await screen.findByRole('list', { name: 'Search results' })
    expect(searchService.search).toHaveBeenCalledWith(expect.objectContaining({ query: 'retention', mode: 'hybrid', sortBy: 'relevance', page: 1 }))
    const marks = within(list).getAllByText(/retention/i, { selector: 'mark' })
    expect(marks.length).toBeGreaterThan(0)
    const open = within(list).getByRole('link', { name: 'Open page 2' })
    expect(open).toHaveAttribute('href', '/app/documents/5?page=2&chunk=chunk-7')
    expect(within(list).getByText('HR')).toBeInTheDocument()
    expect(within(list).getByText('#policy')).toBeInTheDocument()
    expect(within(list).getByText('Team')).toBeInTheDocument()
    expect(within(list).getByText('Shared · viewer')).toBeInTheDocument()
    expect(screen.getByText(/semantic similarity 0\.42/)).toBeInTheDocument()
  })

  it('switches mode and applies filters and sorting', async () => {
    searchService.search.mockResolvedValue(result())
    show('/app/search?q=retention')
    await screen.findByRole('list', { name: 'Search results' })
    await userEvent.click(screen.getByRole('radio', { name: 'Keyword' }))
    await waitFor(() => expect(searchService.search).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'keyword' })))
    await userEvent.selectOptions(screen.getByLabelText('Category'), '0')
    await waitFor(() => expect(searchService.search).toHaveBeenLastCalledWith(expect.objectContaining({ categoryId: '0' })))
    await userEvent.selectOptions(screen.getByLabelText('Collection'), '3')
    await userEvent.selectOptions(screen.getByLabelText('Tag'), '2')
    await userEvent.selectOptions(screen.getByLabelText('Sort results'), 'title')
    await waitFor(() => expect(searchService.search).toHaveBeenLastCalledWith(expect.objectContaining({ mode: 'keyword', collectionId: '3', categoryId: '0', tagId: '2', sortBy: 'title' })))
  })

  it('shows a no-results state and clears filters', async () => {
    searchService.search.mockResolvedValue(result({ items: [], total: 0 }))
    show('/app/search?q=zebra&tag=2')
    expect(await screen.findByText('No results')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Clear filters' })[0])
    await waitFor(() => expect(searchService.search).toHaveBeenLastCalledWith(expect.objectContaining({ tagId: '' })))
  })

  it('shows an error state and retries', async () => {
    searchService.search.mockRejectedValueOnce(new Error('Semantic search is unavailable right now.')).mockResolvedValue(result())
    show('/app/search?q=retention&mode=semantic')
    expect(await screen.findByText(/Semantic search is unavailable/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again|retry/i }))
    expect(await screen.findByRole('list', { name: 'Search results' })).toBeInTheDocument()
  })

  it('explains degraded results', async () => {
    searchService.search.mockResolvedValue(result({ warnings: ['semantic_unavailable'], ranking: { method: 'keyword' } }))
    show('/app/search?q=retention')
    expect(await screen.findByText(/keyword results only/)).toBeInTheDocument()
  })

  it('shows a loading indicator while searching', async () => {
    let finish
    searchService.search.mockReturnValue(new Promise((r) => (finish = r)))
    show('/app/search?q=retention')
    expect(await screen.findByText('Searching…')).toBeInTheDocument()
    finish(result())
    expect(await screen.findByRole('list', { name: 'Search results' })).toBeInTheDocument()
  })
})

describe('highlightParts', () => {
  it('highlights word starts and phrases, case-insensitively', () => {
    const parts = highlightParts('Retention Policy: retentive records', ['retent'], ['retention policy'])
    expect(parts.filter((p) => p.hit).map((p) => p.text)).toEqual(['Retention Policy', 'retentive'])
  })

  it('never treats user input as a pattern', () => {
    expect(() => highlightParts('a (b) [c] a.b', ['(b', '[c', 'a.*', '\\'], ['a.b'])).not.toThrow()
    expect(highlightParts('x', [], []).every((p) => !p.hit)).toBe(true)
    expect(highlightParts('tent', ['ten'], []).filter((p) => p.hit).map((p) => p.text)).toEqual(['tent'])
  })
})
