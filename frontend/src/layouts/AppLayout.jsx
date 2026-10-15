import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AppSidebar } from '../components/layout/AppSidebar'
import { AppHeader } from '../components/layout/AppHeader'
import { MobileNavigation } from '../components/layout/MobileNavigation'

const COLLAPSE_KEY = 'documind.sidebarCollapsed'

function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1'
  } catch {
    return false
  }
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()
  // Keyed on the section so switching pages replays the entrance animation,
  // but moving between conversations in the assistant does not remount it.
  const section = pathname.split('/').slice(0, 3).join('/')

  const toggle = () => {
    setCollapsed((c) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, c ? '0' : '1')
      } catch {
        /* ignore */
      }
      return !c
    })
  }

  return (
    <div className="flex min-h-screen bg-canvas bg-[radial-gradient(60rem_30rem_at_90%_-10%,rgba(201,80,111,0.14),transparent)]">
      <a
        href="#main"
        className="sr-only z-[70] rounded-md bg-surface px-3 py-2 text-sm font-medium focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>
      <AppSidebar collapsed={collapsed} onToggle={toggle} />
      <MobileNavigation open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onOpenMenu={() => setMenuOpen(true)} />
        <main id="main" className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div key={section} className="animate-fade-in-up">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
