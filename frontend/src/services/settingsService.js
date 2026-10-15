import { http } from './http'
import { normalizeUser } from './normalize'

export async function getProfile() {
  const { data } = await http.get('/settings/profile')
  return normalizeUser(data)
}

export async function updateProfile({ name }) {
  const { data } = await http.patch('/settings/profile', { name })
  return normalizeUser(data)
}
