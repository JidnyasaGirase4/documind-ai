const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

export const PASSWORD_RULES = [
  { id: 'length', label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { id: 'letter', label: 'Contains a letter', test: (p) => /[A-Za-z]/.test(p) },
  { id: 'number', label: 'Contains a number', test: (p) => /\d/.test(p) },
]

export function validateEmail(email) {
  if (!email.trim()) return 'Enter your email address.'
  if (!EMAIL_RE.test(email.trim())) return 'Enter a valid email address.'
  return ''
}

export function validateLogin({ email, password }) {
  const errors = {}
  const e = validateEmail(email)
  if (e) errors.email = e
  if (!password) errors.password = 'Enter your password.'
  return errors
}

export function validateRegister({ name, email, password, confirmPassword }) {
  const errors = {}
  if (!name.trim()) errors.name = 'Enter your name.'
  else if (name.trim().length > 100) errors.name = 'Name must be 100 characters or fewer.'
  const e = validateEmail(email)
  if (e) errors.email = e
  if (!password) errors.password = 'Create a password.'
  else if (!PASSWORD_RULES.every((r) => r.test(password))) errors.password = 'Password does not meet the requirements.'
  if (!confirmPassword) errors.confirmPassword = 'Confirm your password.'
  else if (confirmPassword !== password) errors.confirmPassword = 'Passwords do not match.'
  return errors
}

export function validatePdf(file, maxBytes, maxMb) {
  const isPdfName = /\.pdf$/i.test(file.name)
  const isPdfType = !file.type || file.type === 'application/pdf'
  if (!isPdfName || !isPdfType) return `"${file.name}" is not a PDF. Only PDF files are supported.`
  if (file.size === 0) return `"${file.name}" is empty.`
  if (file.size > maxBytes) return `"${file.name}" is larger than the ${maxMb} MB limit.`
  return ''
}
