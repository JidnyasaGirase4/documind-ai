import { http } from './http'
import { normalizeCollection, normalizeLabel, normalizeMember, normalizePage } from './normalize'

// scope: 'all' (default), 'owned' or 'shared' (shared with me by others)
export async function listCollections({ page = 1, pageSize = 12, search, sortBy, sortOrder, scope } = {}) {
  const params = { page, page_size: pageSize }
  if (scope) params.scope = scope
  if (search) params.search = search
  if (sortBy) params.sort_by = sortBy
  if (sortOrder) params.sort_order = sortOrder
  const { data } = await http.get('/collections', { params })
  return normalizePage(data, normalizeCollection, { page, pageSize })
}

export async function getCollection(id) {
  const { data } = await http.get(`/collections/${id}`)
  return normalizeCollection(data)
}

export async function createCollection({ name, description, color, icon }) {
  const { data } = await http.post('/collections', { name, description: description || null, color: color || null, icon: icon || null })
  return normalizeCollection(data)
}

export async function updateCollection(id, { name, description, color, icon }) {
  const { data } = await http.patch(`/collections/${id}`, { name, description: description || null, color: color || null, icon: icon || null })
  return normalizeCollection(data)
}

// Deletes the collection only. Its documents are kept.
export async function deleteCollection(id) {
  await http.delete(`/collections/${id}`)
}

export async function addDocuments(collectionId, documentIds, moveFromCollectionId) {
  const body = { document_ids: documentIds }
  if (moveFromCollectionId) body.move_from_collection_id = moveFromCollectionId
  const { data } = await http.post(`/collections/${collectionId}/documents`, body)
  return normalizeCollection(data)
}

export async function removeDocument(collectionId, documentId) {
  await http.delete(`/collections/${collectionId}/documents/${documentId}`)
}

export async function listCategories() {
  const { data } = await http.get('/categories')
  return data.map(normalizeLabel)
}
export async function createCategory({ name, description }) {
  const { data } = await http.post('/categories', { name, description: description || null })
  return normalizeLabel(data)
}
export async function updateCategory(id, { name, description }) {
  const { data } = await http.patch(`/categories/${id}`, { name, description: description || null })
  return normalizeLabel(data)
}
export async function deleteCategory(id) {
  await http.delete(`/categories/${id}`)
}

export async function listTags() {
  const { data } = await http.get('/tags')
  return data.map(normalizeLabel)
}
export async function createTag(name) {
  const { data } = await http.post('/tags', { name })
  return normalizeLabel(data)
}
export async function renameTag(id, name) {
  const { data } = await http.patch(`/tags/${id}`, { name })
  return normalizeLabel(data)
}
export async function deleteTag(id) {
  await http.delete(`/tags/${id}`)
}

export async function listMembers(collectionId) {
  const { data } = await http.get(`/collections/${collectionId}/members`)
  return data.map(normalizeMember)
}
export async function inviteMember(collectionId, { email, role }) {
  const { data } = await http.post(`/collections/${collectionId}/members`, { email, role })
  return normalizeMember(data)
}
export async function changeMemberRole(collectionId, userId, role) {
  const { data } = await http.patch(`/collections/${collectionId}/members/${userId}`, { role })
  return normalizeMember(data)
}
// The owner revokes anyone; a member can remove themselves (leave). Takes effect immediately.
export async function removeMember(collectionId, userId) {
  await http.delete(`/collections/${collectionId}/members/${userId}`)
}
