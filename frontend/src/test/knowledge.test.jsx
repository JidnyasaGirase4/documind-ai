import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import KnowledgeBase from '../pages/app/KnowledgeBase'
import Documents from '../pages/app/Documents'
import { knowledgeService, documentService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: { listDocuments: vi.fn(), uploadDocument: vi.fn(), deleteDocument: vi.fn(), retryDocument: vi.fn(), updateMetadata: vi.fn() },
    knowledgeService: {
      listCollections: vi.fn(),
      createCollection: vi.fn(),
      updateCollection: vi.fn(),
      deleteCollection: vi.fn(),
      listCategories: vi.fn(),
      listTags: vi.fn(),
    },
  }
})

const page = (items) => ({ items, total: items.length, page: 1, pageSize: 12, pages: 1 })
const coll = (o) => ({ id: 1, name: 'HR', description: 'People docs', color: 'burgundy', icon: 'users', documentCount: 2, role: 'owner', isShared: false, memberCount: 0, ...o })
const doc = (o) => ({ id: 1, filename: 'leave.pdf', size: 2048, status: 'ready', error: null, pages: 3, createdAt: '2026-01-01T00:00:00Z', category: null, tags: [], collectionIds: [], ...o })

beforeEach(() => {
  vi.clearAllMocks()
  knowledgeService.listCategories.mockResolvedValue([])
  knowledgeService.listTags.mockResolvedValue([])
})

describe('KnowledgeBase collections', () => {
  it('lists collections with their document counts', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([coll(), coll({ id: 2, name: 'Finance', documentCount: 1 })]))
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    expect(await screen.findByRole('link', { name: 'HR' })).toHaveAttribute('href', '/app/knowledge/collections/1')
    expect(screen.getByText('2 documents')).toBeInTheDocument()
    expect(screen.getByText('1 document')).toBeInTheDocument()
  })

  it('shows an empty state and creates the first collection', async () => {
    knowledgeService.listCollections.mockResolvedValueOnce(page([])).mockResolvedValue(page([coll({ name: 'Research' })]))
    knowledgeService.createCollection.mockResolvedValue(coll({ name: 'Research' }))
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    expect(await screen.findByText('No collections yet')).toBeInTheDocument()

    await userEvent.click(screen.getAllByRole('button', { name: /new collection|create your first/i })[0])
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Name'), 'Research')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Create collection' }))

    await waitFor(() => expect(knowledgeService.createCollection).toHaveBeenCalledWith(expect.objectContaining({ name: 'Research', color: 'burgundy' })))
    expect(await screen.findByRole('link', { name: 'Research' })).toBeInTheDocument()
  })

  it('shows a server error (duplicate name) inside the dialog', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([coll()]))
    knowledgeService.createCollection.mockRejectedValue(new Error('You already have a collection with that name.'))
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    await screen.findByRole('link', { name: 'HR' })
    await userEvent.click(screen.getByRole('button', { name: 'New collection' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Name'), 'hr')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Create collection' }))
    expect(await within(dialog).findByText('You already have a collection with that name.')).toBeInTheDocument()
  })

  it('edits a collection', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([coll()]))
    knowledgeService.updateCollection.mockResolvedValue(coll({ name: 'People' }))
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Edit HR' }))
    const dialog = await screen.findByRole('dialog')
    const name = within(dialog).getByLabelText('Name')
    await userEvent.clear(name)
    await userEvent.type(name, 'People')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(knowledgeService.updateCollection).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'People' })))
  })

  it('confirms before deleting and says the documents are kept', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([coll()]))
    knowledgeService.deleteCollection.mockResolvedValue()
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Delete HR' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('NOT deleted')
    expect(knowledgeService.deleteCollection).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete collection' }))
    await waitFor(() => expect(knowledgeService.deleteCollection).toHaveBeenCalledWith(1))
  })

  it('shows an error state with retry when loading fails', async () => {
    knowledgeService.listCollections.mockRejectedValueOnce(new Error('Server unavailable')).mockResolvedValue(page([coll()]))
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    expect(await screen.findByText(/Server unavailable/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again|retry/i }))
    expect(await screen.findByRole('link', { name: 'HR' })).toBeInTheDocument()
  })

  it('switches to the categories tab', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([]))
    knowledgeService.listCategories.mockResolvedValue([{ id: 5, name: 'Finance', description: '', documentCount: 3 }])
    renderWithProviders(<KnowledgeBase />, { withAuth: false })
    await userEvent.click(await screen.findByRole('tab', { name: 'Categories' }))
    expect(await screen.findByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('3 documents')).toBeInTheDocument()
  })
})

describe('Documents filters', () => {
  it('filters the document list by collection, category and tag', async () => {
    knowledgeService.listCollections.mockResolvedValue(page([coll({ id: 7, name: 'Policies' })]))
    knowledgeService.listCategories.mockResolvedValue([{ id: 3, name: 'HR Policies', description: '', documentCount: 1 }])
    knowledgeService.listTags.mockResolvedValue([{ id: 9, name: 'leave', description: '', documentCount: 1 }])
    documentService.listDocuments.mockResolvedValue({ items: [doc({ category: { id: 3, name: 'HR Policies' }, tags: [{ id: 9, name: 'leave' }] })], total: 1, page: 1, pageSize: 10, pages: 1 })
    renderWithProviders(<Documents />, { withAuth: false })

    expect(await screen.findByText('leave.pdf')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Category and tags' })).getByText('#leave')).toBeInTheDocument()

    await userEvent.selectOptions(await screen.findByLabelText('Collection'), '7')
    await waitFor(() => expect(documentService.listDocuments).toHaveBeenLastCalledWith(expect.objectContaining({ collectionId: '7' })))
    await userEvent.selectOptions(screen.getByLabelText('Category'), '3')
    await userEvent.selectOptions(screen.getByLabelText('Tag'), '9')
    await waitFor(() => expect(documentService.listDocuments).toHaveBeenLastCalledWith(expect.objectContaining({ collectionId: '7', categoryId: '3', tagId: '9' })))
  })
})
