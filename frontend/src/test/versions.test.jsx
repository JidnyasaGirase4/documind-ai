import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, within, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import { VersionHistory } from '../components/versions/VersionHistory'
import { CitationViewer } from '../components/viewer/CitationViewer'
import { documentService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    documentService: {
      listVersions: vi.fn(),
      uploadVersion: vi.fn(),
      restoreVersion: vi.fn(),
      retryVersion: vi.fn(),
      compareVersions: vi.fn(),
      downloadVersion: vi.fn(),
      getDocument: vi.fn(),
      getPageImage: vi.fn(),
      getCitationHighlights: vi.fn(),
    },
  }
})

const v = (o) => ({ id: 10, documentId: 1, number: 1, filename: 'policy.pdf', size: 2048, checksum: 'abc', pages: 2, status: 'ready', error: null, isCurrent: false, note: null, restoredFrom: null, uploadedBy: { id: 1, name: 'Olivia' }, createdAt: '2026-01-01T10:00:00Z', progress: null, ...o })
const history = [
  v({ id: 12, number: 3, isCurrent: true, note: 'Back to 16 weeks', restoredFrom: 1 }),
  v({ id: 11, number: 2, note: 'Updated leave' }),
  v({ id: 10, number: 1 }),
]

function show(props = {}) {
  return renderWithProviders(<VersionHistory documentId={1} canManage onOpenVersion={vi.fn()} onChanged={vi.fn()} {...props} />, { withAuth: false })
}

beforeEach(() => {
  vi.clearAllMocks()
  documentService.listVersions.mockResolvedValue(history)
})

describe('VersionHistory', () => {
  it('lists versions newest first with a current marker, notes, restore origin and uploader', async () => {
    show()
    const list = await screen.findByRole('list', { name: /versions, newest first/i })
    const items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(within(items[0]).getByText('Version 3')).toBeInTheDocument()
    expect(within(items[0]).getByText('Current')).toBeInTheDocument()
    expect(within(items[0]).getByText('Restored from v1')).toBeInTheDocument()
    expect(within(items[0]).getByText('Back to 16 weeks')).toBeInTheDocument()
    expect(within(items[1]).getByText('Earlier version')).toBeInTheDocument()
    expect(within(items[1]).getByText(/Olivia/)).toBeInTheDocument()
  })

  it('offers upload and restore to managers only, never restore for the current or an unfinished version', async () => {
    documentService.listVersions.mockResolvedValue([...history, v({ id: 13, number: 4, status: 'failed', error: 'boom' })].sort((a, b) => b.number - a.number))
    show()
    await screen.findByRole('list', { name: /versions/i })
    expect(screen.getByRole('button', { name: 'Upload new version' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restore version 3' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Restore version 4' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore version 2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry processing of version 4' })).toBeInTheDocument()
    expect(screen.getByText('boom')).toBeInTheDocument()
  })

  it('hides write actions for viewers but keeps view, download and compare', async () => {
    show({ canManage: false })
    await screen.findByRole('list', { name: /versions/i })
    expect(screen.queryByRole('button', { name: 'Upload new version' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /restore version/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View version 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download version 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Compare selected' })).toBeDisabled()
  })

  it('uploads a new version with a note and validates the file type', async () => {
    documentService.uploadVersion.mockResolvedValue(v({ id: 14, number: 4, status: 'queued' }))
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Upload new version' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Upload version' }))
    expect(await within(dialog).findByText('Choose a PDF file.')).toBeInTheDocument()
    fireEvent.change(within(dialog).getByTestId('version-file-input'), { target: { files: [new File(['x'], 'notes.txt', { type: 'text/plain' })] } })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Upload version' }))
    expect(await within(dialog).findByText('Only PDF files are supported.')).toBeInTheDocument()
    expect(documentService.uploadVersion).not.toHaveBeenCalled()
  })

  it('uploads a new version with a note', async () => {
    documentService.uploadVersion.mockResolvedValue(v({ id: 14, number: 4, status: 'queued' }))
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Upload new version' }))
    const dialog = await screen.findByRole('dialog')
    const pdf = new File(['%PDF-1.4'], 'policy-v4.pdf', { type: 'application/pdf' })
    fireEvent.change(within(dialog).getByTestId('version-file-input'), { target: { files: [pdf] } })
    await userEvent.type(within(dialog).getByLabelText(/what changed/i), 'New annex')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Upload version' }))
    await waitFor(() => expect(documentService.uploadVersion).toHaveBeenCalledWith(1, pdf, 'New annex', expect.any(Function)))
  })

  it('shows the server message when an upload is refused', async () => {
    documentService.uploadVersion.mockRejectedValue(new Error('This file is identical to the current version (v3), so no new version was created.'))
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Upload new version' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByTestId('version-file-input'), { target: { files: [new File(['%PDF'], 'same.pdf', { type: 'application/pdf' })] } })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Upload version' }))
    expect(await within(dialog).findByText(/identical to the current version/)).toBeInTheDocument()
  })

  it('asks for confirmation before restoring and explains that history is kept', async () => {
    documentService.restoreVersion.mockResolvedValue(v({ id: 15, number: 4, status: 'queued' }))
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Restore version 2' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('NEW latest version')
    expect(dialog).toHaveTextContent('No version is deleted')
    expect(documentService.restoreVersion).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Restore' }))
    await waitFor(() => expect(documentService.restoreVersion).toHaveBeenCalledWith(1, 11))
  })

  it('compares two selected versions (older first) and returns to the history', async () => {
    documentService.compareVersions.mockResolvedValue({
      documentId: 1,
      from: { id: 10, number: 1, createdAt: '2026-01-01T10:00:00Z', isCurrent: false },
      to: { id: 12, number: 3, createdAt: '2026-02-01T10:00:00Z', isCurrent: true },
      comparable: true,
      reason: null,
      stats: { added: 1, removed: 0, changed: 1, unchanged: 2, identical: false },
      notice: 'This compares the extracted text only. It does not detect visual or layout changes.',
      blocks: [
        { type: 'equal', old: [{ page: 1, text: 'Same sentence.' }], new: [{ page: 1, text: 'Same sentence.' }] },
        { type: 'changed', old: [{ page: 1, text: 'We offer sixteen weeks.' }], new: [{ page: 1, text: 'We offer eighteen weeks.' }], inline: [{ op: 'equal', text: 'We offer ' }, { op: 'del', text: 'sixteen' }, { op: 'ins', text: 'eighteen' }, { op: 'equal', text: ' weeks.' }] },
        { type: 'added', old: [], new: [{ page: 2, text: 'Adoption leave is covered.' }] },
        { type: 'skipped', count: 5 },
      ],
    })
    show()
    await userEvent.click(await screen.findByLabelText('Select version 3 for comparison'))
    await userEvent.click(screen.getByLabelText('Select version 1 for comparison'))
    await userEvent.click(screen.getByRole('button', { name: 'Compare selected' }))
    await waitFor(() => expect(documentService.compareVersions).toHaveBeenCalledWith(1, 10, 12))
    expect(await screen.findByText('Comparing version 1 → version 3')).toBeInTheDocument()
    expect(screen.getByText('1 added')).toBeInTheDocument()
    expect(screen.getByText('sixteen', { selector: 'del' })).toBeInTheDocument()
    expect(screen.getByText('eighteen', { selector: 'ins' })).toBeInTheDocument()
    expect(screen.getByText(/Adoption leave is covered/)).toBeInTheDocument()
    expect(screen.getByText(/5 unchanged passages/)).toBeInTheDocument()
    expect(screen.getByText(/does not detect visual or layout changes/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /back to version history/i }))
    expect(await screen.findByRole('list', { name: /versions, newest first/i })).toBeInTheDocument()
  })

  it('explains when versions cannot be compared', async () => {
    documentService.compareVersions.mockResolvedValue({
      documentId: 1, from: { id: 10, number: 1 }, to: { id: 11, number: 2 }, comparable: false, reason: 'Version 1 failed processing, so its text is not available.',
      stats: { added: 0, removed: 0, changed: 0, unchanged: 0, identical: false }, blocks: [], notice: 'Text only.',
    })
    show()
    await userEvent.click(await screen.findByLabelText('Select version 2 for comparison'))
    await userEvent.click(screen.getByLabelText('Select version 1 for comparison'))
    await userEvent.click(screen.getByRole('button', { name: 'Compare selected' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be compared reliably')
    expect(screen.getByRole('alert')).toHaveTextContent('failed processing')
  })

  it('shows loading then an error state with retry', async () => {
    documentService.listVersions.mockRejectedValueOnce(new Error('Server unavailable')).mockResolvedValue(history)
    show()
    expect(await screen.findByText(/Server unavailable/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again|retry/i }))
    expect(await screen.findByRole('list', { name: /versions, newest first/i })).toBeInTheDocument()
  })

  it('downloads a specific version', async () => {
    documentService.downloadVersion.mockResolvedValue()
    show()
    await userEvent.click(await screen.findByRole('button', { name: 'Download version 2' }))
    await waitFor(() => expect(documentService.downloadVersion).toHaveBeenCalledWith(1, expect.objectContaining({ id: 11, number: 2 })))
  })
})

describe('CitationViewer with versions', () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:page')
    URL.revokeObjectURL = vi.fn()
    documentService.getDocument.mockResolvedValue({ id: 7, pages: 2 })
    documentService.getPageImage.mockResolvedValue('blob:page')
    documentService.getCitationHighlights.mockResolvedValue({ page: 1, reliable: true, coverage: 1, rects: [] })
  })

  it('loads the historical file for an older citation and says so', async () => {
    const c = [{ documentId: 7, documentName: 'policy.pdf', page: 1, chunkId: 'chunk-3', versionId: 55, versionNumber: 1, versionIsCurrent: false }]
    renderWithProviders(<CitationViewer open onClose={() => {}} citations={c} index={0} />, { withAuth: false })
    await waitFor(() => expect(documentService.getPageImage).toHaveBeenCalledWith(7, 1, expect.objectContaining({ versionId: 55 })))
    expect(await screen.findByText(/viewing version 1, an earlier version/)).toBeInTheDocument()
  })

  it('does not warn for a citation of the current version', async () => {
    const c = [{ documentId: 7, documentName: 'policy.pdf', page: 1, chunkId: 'chunk-3', versionId: 56, versionNumber: 2, versionIsCurrent: true }]
    renderWithProviders(<CitationViewer open onClose={() => {}} citations={c} index={0} />, { withAuth: false })
    expect(await screen.findByText('Version 2 (current).')).toBeInTheDocument()
    expect(screen.queryByText(/earlier version of this document/)).not.toBeInTheDocument()
  })
})
