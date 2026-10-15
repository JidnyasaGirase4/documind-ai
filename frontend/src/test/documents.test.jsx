import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import Documents from '../pages/app/Documents'
import { UploadDropzone } from '../components/documents/UploadDropzone'
import { documentService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: {
      listDocuments: vi.fn(),
      uploadDocument: vi.fn(),
      deleteDocument: vi.fn(),
      retryDocument: vi.fn(),
    },
  }
})

const page = (items) => ({ items, total: items.length, page: 1, pageSize: 10, pages: 1 })
const doc = (o) => ({ id: 1, filename: 'report.pdf', size: 2048, status: 'ready', error: null, pages: 3, createdAt: '2026-01-01T00:00:00Z', ...o })
const pdf = (name = 'a.pdf', size = 1000) => new File([new Uint8Array(size)], name, { type: 'application/pdf' })

beforeEach(() => vi.clearAllMocks())

describe('UploadDropzone', () => {
  it('rejects non-PDF files without calling onFiles', async () => {
    const onFiles = vi.fn()
    renderWithProviders(<UploadDropzone onFiles={onFiles} />, { withAuth: false })
    const input = screen.getByTestId('file-input')
    fireEvent.change(input, { target: { files: [new File(['x'], 'notes.txt', { type: 'text/plain' })] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('not a PDF')
    expect(onFiles).not.toHaveBeenCalled()
  })

  it('passes valid PDFs through and shows progress states', () => {
    const onFiles = vi.fn()
    renderWithProviders(
      <UploadDropzone
        onFiles={onFiles}
        uploads={[
          { id: 1, name: 'a.pdf', progress: 40, state: 'uploading' },
          { id: 2, name: 'b.pdf', progress: 100, state: 'error', error: 'File too large' },
        ]}
      />,
      { withAuth: false },
    )
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [pdf()] } })
    expect(onFiles).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('progressbar', { name: 'Uploading a.pdf' })).toHaveAttribute('aria-valuenow', '40')
    expect(screen.getByText('File too large')).toBeInTheDocument()
  })
})

describe('Documents page', () => {
  it('shows an empty state when there are no documents', async () => {
    documentService.listDocuments.mockResolvedValue(page([]))
    renderWithProviders(<Documents />, { route: '/app/documents', withAuth: false })
    expect(await screen.findByText('No documents yet')).toBeInTheDocument()
  })

  it('shows a retryable error state', async () => {
    documentService.listDocuments.mockRejectedValueOnce(Object.assign(new Error('Server exploded'), { code: 'HTTP_500' }))
    documentService.listDocuments.mockResolvedValue(page([doc()]))
    renderWithProviders(<Documents />, { route: '/app/documents', withAuth: false })
    expect(await screen.findByText('Server exploded')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText('report.pdf')).toBeInTheDocument()
  })

  it('does not report success until the API confirms the upload', async () => {
    documentService.listDocuments.mockResolvedValue(page([]))
    documentService.uploadDocument.mockRejectedValue(new Error('Unsupported file type'))
    renderWithProviders(<Documents />, { route: '/app/documents', withAuth: false })
    await screen.findByText('No documents yet')
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [pdf()] } })
    expect(await screen.findByText('Unsupported file type')).toBeInTheDocument()
    expect(screen.queryByText(/uploaded\. processing has started/i)).not.toBeInTheDocument()
  })

  it('shows failed status with the error and offers retry', async () => {
    documentService.listDocuments.mockResolvedValue(page([doc({ status: 'failed', error: 'No extractable text found.' })]))
    documentService.retryDocument.mockResolvedValue(null)
    renderWithProviders(<Documents />, { route: '/app/documents', withAuth: false })
    expect(await screen.findByText('No extractable text found.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /actions for report\.pdf/i }))
    await userEvent.click(screen.getByRole('menuitem', { name: /retry processing/i }))
    await waitFor(() => expect(documentService.retryDocument).toHaveBeenCalledWith(1))
  })

  it('asks for confirmation before deleting', async () => {
    documentService.listDocuments.mockResolvedValue(page([doc()]))
    documentService.deleteDocument.mockResolvedValue()
    renderWithProviders(<Documents />, { route: '/app/documents', withAuth: false })
    await screen.findByText('report.pdf')
    await userEvent.click(screen.getByRole('button', { name: /actions for report\.pdf/i }))
    await userEvent.click(screen.getByRole('menuitem', { name: /delete/i }))
    expect(documentService.deleteDocument).not.toHaveBeenCalled()
    await userEvent.click(within_dialog('Delete'))
    await waitFor(() => expect(documentService.deleteDocument).toHaveBeenCalledWith(1))
  })
})

function within_dialog(name) {
  const dialog = screen.getByRole('dialog')
  const btn = [...dialog.querySelectorAll('button')].find((b) => b.textContent.trim() === name)
  return btn
}
