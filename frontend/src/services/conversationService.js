import { http } from './http'
import { normalizeConversation, normalizeMessage, normalizePage } from './normalize'

export async function listConversations({ page = 1, pageSize = 10, search } = {}) {
  const params = { page, page_size: pageSize }
  if (search) params.search = search
  const { data } = await http.get('/conversations', { params })
  return normalizePage(data, normalizeConversation, { page, pageSize })
}

export async function createConversation({ title, documentIds } = {}) {
  const body = {}
  if (title) body.title = title
  if (documentIds?.length) body.document_ids = documentIds
  const { data } = await http.post('/conversations', body)
  return normalizeConversation(data)
}

export async function getConversation(id) {
  const { data } = await http.get(`/conversations/${id}`)
  return normalizeConversation(data)
}

export async function renameConversation(id, title) {
  const { data } = await http.patch(`/conversations/${id}`, { title })
  return normalizeConversation(data)
}

export async function deleteConversation(id) {
  await http.delete(`/conversations/${id}`)
}

// Contract: { user_message, assistant_message }. A bare assistant message is also accepted.
export async function sendMessage(conversationId, { content, documentIds }) {
  const body = { content }
  if (documentIds?.length) body.document_ids = documentIds
  // Answers can take a while (a local model on a CPU may need a minute or more), so this call waits up to 5 minutes.
  const { data } = await http.post(`/conversations/${conversationId}/messages`, body, { timeout: 300000 })
  const assistantRaw = data.assistant_message ?? (data.role === 'assistant' ? data : null)
  if (!assistantRaw) throw new Error('The server returned no answer.')
  return {
    userMessage: data.user_message ? normalizeMessage(data.user_message) : null,
    assistantMessage: normalizeMessage(assistantRaw),
  }
}
