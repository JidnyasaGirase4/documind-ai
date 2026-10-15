import { http } from './http'
import { normalizeDocument, normalizePage } from './normalize'

export async function listDocuments({ page = 1, pageSize = 10, search, status, sortBy, sortOrder } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  if (status) params.status = status
  if (sortBy) params.sort_by = sortBy
  if (sortOrder) params.sort_order = sortOrder
  const { data } = await http.get('/documents', { params })
  return normalizePage(data, normalizeDocument, { page, pageSize })
}

export async function getDocument(id) {
  const { data } = await http.get(`/documents/${id}`)
  return normalizeDocument(data)
}

export async function uploadDocument(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post('/documents/upload', form, {
    timeout: 0,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return normalizeDocument(data)
}

export async function deleteDocument(id) {
  await http.delete(`/documents/${id}`)
}

export async function retryDocument(id) {
  const { data } = await http.post(`/documents/${id}/retry`)
  return data?.id ? normalizeDocument(data) : null
}

// Fetches the authorized preview. The backend may stream the PDF or return
// { url } for a short-lived link; both are handled. Internal server paths are never used.
export async function getPreviewUrl(id, page) {
  const res = await http.get(`/documents/${id}/preview`, { responseType: 'blob' })
  const blob = res.data
  let url
  let owned = false
  if (blob.type.includes('json')) {
    const json = JSON.parse(await blob.text())
    if (!json?.url) throw new Error('Preview unavailable.')
    url = json.url
  } else {
    url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
    owned = true
  }
  return {
    url: page ? `${url}#page=${page}` : url,
    revoke: () => {
      if (owned) URL.revokeObjectURL(url)
    },
  }
}
