import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, Menu, Settings } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Dropdown } from '../common/Dropdown'
import { itemForPath } from './navItems'

function initials(user) {
  const src = user?.name || user?.email || '?'
  return src
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join('')
}

// Solid top bar for the signed-in app. It is pinned flush to the top of the page, so scrolled
// content slides cleanly underneath it and never shows above or beside it.
export function AppHeader({ onOpenMenu }) {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const current = itemForPath(pathname)
  const Icon = current?.icon

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="sticky top-0 z-20 border-b border-line bg-surface shadow-card">
      <header className="mx-auto flex h-14 max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-2.5">
          <button
            type="button"
            onClick={onOpenMenu}
            aria-label="Open navigation menu"
            className="rounded-lg p-1.5 text-ink hover:bg-stone-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          {Icon && (
            <span className="icon-tile hidden h-8 w-8 sm:flex">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
          )}
          <p className="truncate text-sm font-bold text-ink">{current?.label ?? 'DocuMind AI'}</p>
        </div>

        <Dropdown
          label="Account menu"
          trigger={(props) => (
            <button
              type="button"
              {...props}
              className="flex items-center gap-2 rounded-full border border-line py-0.5 pl-0.5 pr-2.5 transition-colors hover:bg-stone-50"
            >
              <span
                className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-700 text-[13px] font-bold text-white"
                aria-hidden="true"
              >
                {initials(user)}
              </span>
              <span className="hidden max-w-[10rem] truncate text-[15px] font-medium text-ink sm:inline">{user?.name || user?.email}</span>
              <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
            </button>
          )}
          items={[
            { label: 'Profile & settings', icon: Settings, onClick: () => navigate('/app/settings') },
            { label: 'Log out', icon: LogOut, onClick: handleLogout },
          ]}
        />
      </header>
    </div>
  )
}
