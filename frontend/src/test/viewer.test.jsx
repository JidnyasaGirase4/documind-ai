import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import { CitationViewer } from '../components/viewer/CitationViewer'
import { documentService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: { getDocument: vi.fn(), getPageImage: vi.fn(), getCitationHighlights: vi.fn() },
  }
})

const citations = [
  { documentId: 7, documentName: 'handbook.pdf', page: 2, excerpt: 'Sixteen weeks of paid leave.', chunkId: 'chunk-5' },
  { documentId: 8, documentName: 'policy.pdf', page: 1, excerpt: 'Ten weeks.', chunkId: null },
]

beforeEach(() => {
  vi.clearAllMocks()
  URL.createObjectURL = vi.fn(() => 'blob:page')
  URL.revokeObjectURL = vi.fn()
  documentService.getDocument.mockResolvedValue({ id: 7, pages: 4 })
  documentService.getPageImage.mockResolvedValue('blob:page')
})

describe('CitationViewer', () => {
  it('opens the cited page and draws highlights only when the server found the passage', async () => {
    documentService.getCitationHighlights.mockResolvedValue({ page: 2, reliable: true, coverage: 0.9, rects: [{ x: 0.1, y: 0.2, w: 0.5, h: 0.03 }] })
    renderWithProviders(<CitationViewer open onClose={() => {}} citations={citations} index={0} />, { withAuth: false })
    await waitFor(() => expect(documentService.getPageImage).toHaveBeenCalledWith(7, 2, expect.anything()))
    expect(await screen.findAllByTestId('citation-highlight')).toHaveLength(1)
    expect(screen.getByText(/supporting passage is highlighted/i)).toBeInTheDocument()
    expect(screen.getByText('of 4')).toBeInTheDocument()
  })

  it('shows the page without a highlight when the position is not reliable', async () => {
    documentService.getCitationHighlights.mockResolvedValue({ page: 2, reliable: false, coverage: 0.2, rects: [] })
    renderWithProviders(<CitationViewer open onClose={() => {}} citations={citations} index={0} />, { withAuth: false })
    expect(await screen.findByText(/could not be determined reliably/i)).toBeInTheDocument()
    expect(screen.queryByTestId('citation-highlight')).not.toBeInTheDocument()
  })

  it('does not request a highlight for a citation without a stored passage id and navigates pages', async () => {
    renderWithProviders(<CitationViewer open onClose={() => {}} citations={citations} index={1} />, { withAuth: false })
    await waitFor(() => expect(documentService.getPageImage).toHaveBeenCalledWith(8, 1, expect.anything()))
    expect(documentService.getCitationHighlights).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: /next page/i }))
    await waitFor(() => expect(documentService.getPageImage).toHaveBeenCalledWith(8, 2, expect.anything()))
  })
})
