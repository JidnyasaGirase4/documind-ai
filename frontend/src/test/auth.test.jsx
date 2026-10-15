import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from './utils'
import Login from '../pages/public/Login'
import Register from '../pages/public/Register'
import ProtectedRoute from '../routes/ProtectedRoute'
import { authService, tokenStore } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return { ...actual, authService: { login: vi.fn(), register: vi.fn(), getMe: vi.fn() } }
})

const ME = { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' }

beforeEach(() => {
  vi.clearAllMocks()
})

function LoginRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/app/dashboard" element={<p>Dashboard page</p>} />
    </Routes>
  )
}

describe('Login form', () => {
  it('shows inline validation and does not call the API for empty input', async () => {
    renderWithProviders(<LoginRoutes />, { route: '/login' })
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))
    expect(screen.getAllByText('Enter your email address.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Enter your password.').length).toBeGreaterThan(0)
    expect(authService.login).not.toHaveBeenCalled()
  })

  it('logs in and redirects, storing the token', async () => {
    authService.login.mockResolvedValue('tok123')
    authService.getMe.mockResolvedValue(ME)
    renderWithProviders(<LoginRoutes />, { route: '/login' })
    await userEvent.type(screen.getByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument()
    expect(authService.login).toHaveBeenCalledWith({ email: 'ada@example.com', password: 'secret123' })
    expect(tokenStore.get()).toBe('tok123')
  })

  it('shows the API error message and disables duplicate submits while loading', async () => {
    let reject
    authService.login.mockReturnValue(new Promise((_, r) => (reject = r)))
    renderWithProviders(<LoginRoutes />, { route: '/login' })
    await userEvent.type(screen.getByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /log in/i }))
    expect(screen.getByRole('button', { name: /logging in/i })).toBeDisabled()
    reject(Object.assign(new Error('Invalid email or password.'), { status: 401 }))
    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument()
    expect(authService.login).toHaveBeenCalledTimes(1)
  })

  it('toggles password visibility', async () => {
    renderWithProviders(<LoginRoutes />, { route: '/login' })
    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('type', 'password')
    await userEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(input).toHaveAttribute('type', 'text')
  })
})

describe('Register form', () => {
  it('validates password rules and confirmation', async () => {
    renderWithProviders(<Register />, { route: '/register' })
    await userEvent.type(screen.getByLabelText('Name'), 'Ada')
    await userEvent.type(screen.getByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'short')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'different')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))
    expect(screen.getAllByText('Password does not meet the requirements.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Passwords do not match.').length).toBeGreaterThan(0)
    expect(authService.register).not.toHaveBeenCalled()
  })
})

describe('ProtectedRoute', () => {
  function Tree() {
    return (
      <Routes>
        <Route path="/login" element={<p>Login page</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/app/documents" element={<p>Secret documents</p>} />
        </Route>
      </Routes>
    )
  }

  it('redirects anonymous users to login', async () => {
    renderWithProviders(<Tree />, { route: '/app/documents' })
    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Secret documents')).not.toBeInTheDocument()
  })

  it('renders content for an authenticated user with a valid token', async () => {
    tokenStore.set('tok')
    authService.getMe.mockResolvedValue(ME)
    renderWithProviders(<Tree />, { route: '/app/documents' })
    await waitFor(() => expect(screen.getByText('Secret documents')).toBeInTheDocument())
  })

  it('sends users to login when the token is rejected', async () => {
    tokenStore.set('expired')
    authService.getMe.mockRejectedValue(Object.assign(new Error('expired'), { status: 401 }))
    renderWithProviders(<Tree />, { route: '/app/documents' })
    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })
})
