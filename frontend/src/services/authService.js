import { http } from './http'
import { normalizeUser } from './normalize'

export async function register({ name, email, password }) {
  const { data } = await http.post('/auth/register', { name, email, password })
  return data
}

export async function login({ email, password }) {
  const { data } = await http.post('/auth/login', { email, password })
  return data.access_token
}

export async function getMe() {
  const { data } = await http.get('/auth/me')
  return normalizeUser(data)
}
