import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from './utils'
import CollectionDetails from '../pages/app/CollectionDetails'
import { knowledgeService, documentService } from '../services'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, name: 'Olivia Owner', email: 'o@example.com' } }),
  AuthProvider: ({ children }) => children,
}))

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: { listDocuments: vi.fn() },
    knowledgeService: {
      getCollection: vi.fn(),
      listCollections: vi.fn(),
      updateCollection: vi.fn(),
      deleteCollection: vi.fn(),
      addDocuments: vi.fn(),
      removeDocument: vi.fn(),
      listMembers: vi.fn(),
      inviteMember: vi.fn(),
      changeMemberRole: vi.fn(),
      removeMember: vi.fn(),
    },
  }
})

const coll = (o) => ({ id: 4, name: 'Team', description: '', color: 'burgundy', icon: 'folder', documentCount: 1, role: 'owner', ownerName: 'Olivia Owner', isShared: true, memberCount: 2, ...o })
const doc = (o) => ({ id: 9, filename: 'leave.pdf', size: 1000, status: 'ready', pages: 2, category: null, tags: [], collectionIds: [4], role: 'owner', isOwner: true, ...o })
const members = [
  { userId: 1, name: 'Olivia Owner', email: 'o@example.com', role: 'owner' },
  { userId: 2, name: 'Eddie Editor', email: 'e@example.com', role: 'editor' },
  { userId: 3, name: 'Vera Viewer', email: 'v@example.com', role: 'viewer' },
]

function show({ role = 'owner', list = members } = {}) {
  knowledgeService.getCollection.mockResolvedValue(coll({ role }))
  knowledgeService.listMembers.mockResolvedValue(list)
  documentService.listDocuments.mockResolvedValue({ items: [doc({ role })], total: 1, page: 1, pageSize: 10, pages: 1 })
  return renderWithProviders(
    <Routes>
      <Route path="/app/knowledge/collections/:collectionId" element={<CollectionDetails />} />
    </Routes>,
    { route: '/app/knowledge/collections/4', withAuth: false },
  )
}

beforeEach(() => vi.clearAllMocks())

describe('Collection sharing (owner)', () => {
  it('lists members with email and role, and marks the collection as shared', async () => {
    show()
    const list = await screen.findByRole('list', { name: 'Collection members' })
    expect(within(list).getByText('e@example.com')).toBeInTheDocument()
    expect(within(list).getByLabelText('Permission for Eddie Editor')).toHaveValue('editor')
    expect(within(list).getByLabelText('Permission for Vera Viewer')).toHaveValue('viewer')
    expect(screen.getByText('Shared with 2 people')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument()
  })

  it('invites a user by email with a chosen role', async () => {
    knowledgeService.inviteMember.mockResolvedValue({})
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Share' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Email address'), 'new@example.com')
    await userEvent.selectOptions(within(dialog).getByLabelText('Permission'), 'editor')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Share' }))
    await waitFor(() => expect(knowledgeService.inviteMember).toHaveBeenCalledWith(4, { email: 'new@example.com', role: 'editor' }))
  })

  it('shows the server message when the email is not registered', async () => {
    knowledgeService.inviteMember.mockRejectedValue(new Error('No registered user has that email address.'))
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Share' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Email address'), 'ghost@example.com')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Share' }))
    expect(await within(dialog).findByText('No registered user has that email address.')).toBeInTheDocument()
  })

  it('changes a role', async () => {
    knowledgeService.changeMemberRole.mockResolvedValue({})
    show()
    await userEvent.selectOptions(await screen.findByLabelText('Permission for Vera Viewer'), 'editor')
    await waitFor(() => expect(knowledgeService.changeMemberRole).toHaveBeenCalledWith(4, 3, 'editor'))
  })

  it('asks for confirmation before revoking access', async () => {
    knowledgeService.removeMember.mockResolvedValue()
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Revoke access for Eddie Editor' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('immediately lose access')
    expect(knowledgeService.removeMember).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Revoke access' }))
    await waitFor(() => expect(knowledgeService.removeMember).toHaveBeenCalledWith(4, 2))
  })

  it('shows an error state when members cannot be loaded', async () => {
    show()
    knowledgeService.listMembers.mockRejectedValue(new Error('Members unavailable'))
    expect(await screen.findByText(/Members unavailable/)).toBeInTheDocument()
  })

  it('explains a private collection when nobody else has access', async () => {
    show({ list: [members[0]] })
    expect(await screen.findByText('Private collection')).toBeInTheDocument()
  })
})

describe('Collection sharing (permission-aware controls)', () => {
  it('a viewer cannot edit, add, share or change roles, but can leave', async () => {
    show({ role: 'viewer' })
    await screen.findByRole('list', { name: 'Collection members' })
    expect(screen.queryByRole('button', { name: 'Add documents' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Share' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Permission for/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Remove .* from collection/ })).not.toBeInTheDocument()
    expect(screen.getByText('Owned by Olivia Owner')).toBeInTheDocument()
  })

  it('an editor can add documents but cannot edit the collection or manage members', async () => {
    show({ role: 'editor' })
    expect(await screen.findByRole('button', { name: 'Add documents' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove leave.pdf from collection' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Share' })).not.toBeInTheDocument()
  })
})
