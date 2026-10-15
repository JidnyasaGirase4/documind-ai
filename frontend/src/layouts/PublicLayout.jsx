import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { PublicNavbar } from '../components/layout/PublicNavbar'
import { PublicFooter } from '../components/layout/PublicFooter'

export default function PublicLayout() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only z-[70] rounded-md bg-surface px-3 py-2 text-sm font-medium focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>
      <PublicNavbar />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <PublicFooter />
    </div>
  )
}
