import { documentService } from '../services'

// Opens an authorized document preview in a new tab, optionally at a page.
// The blank tab is opened synchronously (inside the click handler) so popup
// blockers allow it, then pointed at the fetched PDF.
export async function openDocumentPreview(documentId, page, versionId) {
  const tab = window.open('', '_blank')
  try {
    const { url, revoke } = await documentService.getPreviewUrl(documentId, page, versionId)
    if (tab) tab.location.href = url
    else window.open(url, '_blank')
    setTimeout(revoke, 5 * 60 * 1000)
  } catch (err) {
    tab?.close()
    throw err
  }
}
