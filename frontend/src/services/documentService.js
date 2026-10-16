import { http } from './http'
import { normalizeComparison, normalizeDocument, normalizePage, normalizeVersion } from './normalize'

export async function listDocuments({ page = 1, pageSize = 10, search, status, sortBy, sortOrder, collectionId, categoryId, tagId, scope } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  if (status) params.status = status
  if (sortBy) params.sort_by = sortBy
  if (sortOrder) params.sort_order = sortOrder
  if (collectionId) params.collection_id = collectionId
  if (categoryId !== undefined && categoryId !== '' && categoryId !== null) params.category_id = categoryId
  if (tagId) params.tag_id = tagId
  if (scope) params.scope = scope // 'owned' (default) | 'shared' | 'all'
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
export async function getPreviewUrl(id, page, versionId) {
  const res = await http.get(`/documents/${id}/preview`, { params: versionId ? { version_id: versionId } : undefined, responseType: 'blob' })
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

// One rendered page of an owned document as an object URL (the caller revokes it). It needs the Authorization
// header, so it is fetched as a blob instead of being used as an <img src> directly.
export async function getPageImage(id, page, { scale = 1.5, signal, versionId } = {}) {
  const params = { scale }
  if (versionId) params.version_id = versionId // a historical version; omitted = the current one
  const res = await http.get(`/documents/${id}/pages/${page}/image`, { params, responseType: 'blob', signal })
  return URL.createObjectURL(res.data)
}

// Where a cited passage is on its page. `reliable: false` means "open the page, but do not draw a highlight".
export async function getCitationHighlights(id, chunkId, { signal } = {}) {
  const { data } = await http.get(`/documents/${id}/highlights`, { params: { chunk_id: chunkId }, signal })
  return {
    page: data.page_number,
    reliable: Boolean(data.reliable),
    coverage: data.coverage ?? 0,
    rects: Array.isArray(data.rects) ? data.rects : [],
  }
}

// Change category / tags / collections without re-uploading. Only the sent fields change.
export async function updateMetadata(id, { categoryId, tags, collectionIds }) {
  const body = {}
  if (categoryId !== undefined) body.category_id = categoryId
  if (tags !== undefined) body.tags = tags
  if (collectionIds !== undefined) body.collection_ids = collectionIds
  const { data } = await http.patch(`/documents/${id}/metadata`, body)
  return normalizeDocument(data)
}

// ---- version history
export async function listVersions(id) {
  const { data } = await http.get(`/documents/${id}/versions`)
  return data.map(normalizeVersion)
}

export async function uploadVersion(id, file, note, onProgress) {
  const form = new FormData()
  form.append('file', file)
  if (note) form.append('change_note', note)
  const { data } = await http.post(`/documents/${id}/versions`, form, {
    timeout: 0,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return normalizeVersion(data)
}

// Copies an old version into a NEW latest version; nothing is deleted.
export async function restoreVersion(id, versionId, note) {
  const { data } = await http.post(`/documents/${id}/versions/${versionId}/restore`, { change_note: note || null })
  return normalizeVersion(data)
}

export async function retryVersion(id, versionId) {
  const { data } = await http.post(`/documents/${id}/versions/${versionId}/retry`)
  return normalizeVersion(data)
}

export async function compareVersions(id, fromId, toId) {
  const { data } = await http.get(`/documents/${id}/versions/compare`, { params: { from: fromId, to: toId } })
  return normalizeComparison(data)
}

// The stored PDF of one version, fetched with the auth header and handed to the browser as a download.
export async function downloadVersion(id, version) {
  const res = await http.get(`/documents/${id}/versions/${version.id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(version.filename || 'document').replace(/\.pdf$/i, '')}-v${version.number}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60 * 1000)
}
