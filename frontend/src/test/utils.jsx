import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'

export function renderWithProviders(ui, { route = '/', withAuth = true } = {}) {
  const inner = <ToastProvider>{ui}</ToastProvider>
  return render(
    <MemoryRouter initialEntries={[route]}>{withAuth ? <AuthProvider>{inner}</AuthProvider> : inner}</MemoryRouter>,
  )
}
