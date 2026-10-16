import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from './utils'
import Assistant from '../pages/app/Assistant'
import { ChatMessage } from '../components/chat/ChatMessage'
import { conversationService, documentService } from '../services'
import { normalizeMessage } from '../services/normalize'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: { listDocuments: vi.fn() },
    conversationService: {
      listConversations: vi.fn(),
      createConversation: vi.fn(),
      getConversation: vi.fn(),
      sendMessage: vi.fn(),
      deleteConversation: vi.fn(),
    },
  }
})

const page = (items) => ({ items, total: items.length, page: 1, pageSize: 10, pages: 1 })

beforeEach(() => {
  vi.clearAllMocks()
  documentService.listDocuments.mockResolvedValue(page([{ id: 7, filename: 'handbook.pdf', status: 'ready' }]))
  conversationService.listConversations.mockResolvedValue(page([]))
  conversationService.createConversation.mockResolvedValue({ id: 'c1', title: 'New conversation', updatedAt: '2026-01-01T00:00:00Z' })
  conversationService.getConversation.mockResolvedValue({ id: 'c1', title: 'New conversation', messages: [] })
})

function Tree() {
  return (
    <Routes>
      <Route path="/app/assistant" element={<Assistant />} />
      <Route path="/app/assistant/:conversationId" element={<Assistant />} />
    </Routes>
  )
}

describe('citation rendering', () => {
  it('renders only the citation details returned by the API', () => {
    const message = normalizeMessage({
      id: 1,
      role: 'assistant',
      content: 'Answer text',
      citations: [
        { document_id: 7, document_name: 'handbook.pdf', page_number: 14, excerpt: 'Sixteen weeks of paid leave.' },
        { document_id: 8, document_name: 'policy.pdf' },
      ],
    })
    const onOpen = vi.fn()
    renderWithProviders(<ChatMessage message={message} onOpenCitation={onOpen} />, { withAuth: false })
    expect(screen.getByText('handbook.pdf')).toBeInTheDocument()
    expect(screen.getByText('Page 14')).toBeInTheDocument()
    expect(screen.getByText(/Sixteen weeks of paid leave\./)).toBeInTheDocument()
    // second citation has no page or excerpt: nothing is invented
    expect(screen.getByText('policy.pdf')).toBeInTheDocument()
    expect(screen.getAllByText(/^Page /)).toHaveLength(1)
  })

  it('opens the cited document when a citation is clicked', async () => {
    const onOpen = vi.fn()
    const message = normalizeMessage({
      id: 1,
      role: 'assistant',
      content: 'A',
      citations: [{ document_id: 7, document_name: 'handbook.pdf', page_number: 2 }],
    })
    renderWithProviders(<ChatMessage message={message} onOpenCitation={onOpen} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: /open handbook\.pdf, page 2/i }))
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ documentId: 7, page: 2 }), expect.any(Array))
  })

  it('renders no sources section when none are returned', () => {
    renderWithProviders(<ChatMessage message={{ role: 'assistant', content: 'No evidence found.', citations: [] }} />, { withAuth: false })
    expect(screen.queryByText('Sources')).not.toBeInTheDocument()
  })
})

describe('Assistant chat', () => {
  it('sends a question, creates a conversation, and shows the answer with citations', async () => {
    conversationService.sendMessage.mockResolvedValue({
      userMessage: { id: 1, role: 'user', content: 'What is the leave policy?', citations: [] },
      assistantMessage: normalizeMessage({
        id: 2,
        role: 'assistant',
        content: 'Sixteen weeks.',
        citations: [{ document_id: 7, document_name: 'handbook.pdf', page_number: 14, excerpt: 'Sixteen weeks of paid leave.' }],
      }),
    })
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    const box = await screen.findByLabelText('Ask a question about your documents')
    await waitFor(() => expect(box).not.toBeDisabled())
    await userEvent.type(box, 'What is the leave policy?{Enter}')
    expect(await screen.findByText('Sixteen weeks.')).toBeInTheDocument()
    expect(screen.getByText('Page 14')).toBeInTheDocument()
    expect(conversationService.createConversation).toHaveBeenCalledTimes(1)
    expect(conversationService.sendMessage).toHaveBeenCalledWith('c1', { content: 'What is the leave policy?', documentIds: [] })
    await waitFor(() => expect(box).toHaveValue(''))
  })

  it('Shift+Enter inserts a newline instead of sending', async () => {
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    const box = await screen.findByLabelText('Ask a question about your documents')
    await waitFor(() => expect(box).not.toBeDisabled())
    await userEvent.type(box, 'line one{Shift>}{Enter}{/Shift}line two')
    expect(box).toHaveValue('line one\nline two')
    expect(conversationService.sendMessage).not.toHaveBeenCalled()
  })

  it('marks a message as failed and allows retry', async () => {
    conversationService.sendMessage.mockRejectedValueOnce(Object.assign(new Error('The AI service is temporarily unavailable.'), { status: 503 }))
    conversationService.sendMessage.mockResolvedValueOnce({
      userMessage: null,
      assistantMessage: normalizeMessage({ id: 3, role: 'assistant', content: 'Recovered answer', citations: [] }),
    })
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    const box = await screen.findByLabelText('Ask a question about your documents')
    await waitFor(() => expect(box).not.toBeDisabled())
    await userEvent.type(box, 'Hello?{Enter}')
    expect(await screen.findByText('The AI service is temporarily unavailable.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText('Recovered answer')).toBeInTheDocument()
  })

  it('lets the user pick several documents and sends exactly that selection', async () => {
    documentService.listDocuments.mockResolvedValue(
      page([
        { id: 7, filename: 'policy-2023.pdf', status: 'ready' },
        { id: 8, filename: 'policy-2024.pdf', status: 'ready' },
      ]),
    )
    conversationService.sendMessage.mockResolvedValue({
      userMessage: null,
      assistantMessage: normalizeMessage({ id: 5, role: 'assistant', content: 'They differ.', citations: [] }),
    })
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: /all my documents/i }))
    await userEvent.click(screen.getByRole('button', { name: /select all \(2\)/i }))
    expect(await screen.findByTestId('multi-doc-banner')).toHaveTextContent('Comparing 2 documents')
    await userEvent.keyboard('{Escape}')
    const box = screen.getByLabelText('Ask a question about your documents')
    await userEvent.type(box, 'Compare leave{Enter}')
    await waitFor(() =>
      expect(conversationService.sendMessage).toHaveBeenCalledWith('c1', { content: 'Compare leave', documentIds: [7, 8] }),
    )
  })

  it('tells the user to upload a document when none are ready', async () => {
    documentService.listDocuments.mockResolvedValue(page([]))
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    expect(await screen.findByText(/at least one processed PDF/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Ask a question about your documents')).toBeDisabled()
  })
})

describe('deleting a chat from the assistant list', () => {
  const chats = [
    { id: 11, title: 'First chat', updatedAt: '2026-01-01T00:00:00Z' },
    { id: 12, title: 'Second chat', updatedAt: '2026-01-02T00:00:00Z' },
  ]

  it('asks for confirmation and then deletes only that chat', async () => {
    conversationService.listConversations.mockResolvedValue(page(chats))
    conversationService.deleteConversation.mockResolvedValue()
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })

    await userEvent.click(await screen.findByRole('button', { name: 'Delete conversation First chat' }))
    expect(conversationService.deleteConversation).not.toHaveBeenCalled() // nothing happens until confirmed
    expect(screen.getByRole('dialog')).toHaveTextContent('"First chat"')

    conversationService.listConversations.mockResolvedValue(page([chats[1]]))
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(conversationService.deleteConversation).toHaveBeenCalledWith(11))
    expect(conversationService.deleteConversation).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.queryByText('First chat')).not.toBeInTheDocument())
    expect(screen.getByText('Second chat')).toBeInTheDocument()
  })

  it('deletes every chat after confirmation', async () => {
    conversationService.listConversations.mockResolvedValue(page(chats))
    conversationService.deleteConversation.mockResolvedValue()
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })

    await userEvent.click(await screen.findByRole('button', { name: 'Delete all chats' }))
    expect(conversationService.deleteConversation).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toHaveTextContent('Delete all chats?')

    conversationService.listConversations.mockResolvedValue(page([]))
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(conversationService.deleteConversation).toHaveBeenCalledTimes(2))
    expect(conversationService.deleteConversation).toHaveBeenCalledWith(11)
    expect(conversationService.deleteConversation).toHaveBeenCalledWith(12)
  })

  it('keeps the chat when the dialog is cancelled', async () => {
    conversationService.listConversations.mockResolvedValue(page(chats))
    renderWithProviders(<Tree />, { route: '/app/assistant', withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Delete conversation Second chat' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(conversationService.deleteConversation).not.toHaveBeenCalled()
    expect(screen.getByText('Second chat')).toBeInTheDocument()
  })
})
