import { useEffect, useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Logo } from '../common/Logo'
import { Button } from '../common/Button'
import { useAuth } from '../../context/AuthContext'

const LINKS = [
  { to: '/features', label: 'Features' },
  { to: '/how-it-works', label: 'How It Works' },
  { to: '/about', label: 'About' },
]

const linkCls = ({ isActive }) =>
  `rounded-full px-4 py-1.5 text-[15px] font-semibold transition-colors ${
    isActive ? 'bg-brand-50 text-brand-700' : 'text-stone-600 hover:bg-stone-100 hover:text-ink'
  }`

// Floating pill-shaped header.
export function PublicNavbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6 lg:px-8">
      <div
        className={`mx-auto max-w-[1440px] overflow-hidden rounded-2xl border bg-surface/90 backdrop-blur-md transition-shadow duration-300 ${
          scrolled ? 'border-line shadow-lift' : 'border-line/70 shadow-card'
        }`}
      >
        <div className="flex h-14 items-center justify-between gap-3 px-3 sm:px-4">
          <Logo />
          <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} className={linkCls}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            {isAuthenticated ? (
              <Button to="/app/dashboard" size="sm">
                Open app
              </Button>
            ) : (
              <>
                <Button to="/login" variant="ghost" size="sm">
                  Log In
                </Button>
                <Button to="/register" size="sm">
                  Get Started
                </Button>
              </>
            )}
          </div>
          <button
            type="button"
            className="rounded-lg p-2 hover:bg-stone-100 md:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            aria-controls="mobile-menu"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {open && (
          <div id="mobile-menu" className="animate-fade-in-up border-t border-line px-3 pb-4 pt-2 md:hidden">
            <nav aria-label="Mobile" className="flex flex-col gap-1 py-1">
              {LINKS.map((l) => (
                <NavLink key={l.to} to={l.to} className={linkCls} onClick={() => setOpen(false)}>
                  {l.label}
                </NavLink>
              ))}
            </nav>
            <div className="mt-2 flex flex-col gap-2">
              {isAuthenticated ? (
                <Link
                  to="/app/dashboard"
                  onClick={() => setOpen(false)}
                  className="inline-flex h-10 items-center justify-center rounded-control bg-brand-600 text-sm font-semibold text-white"
                >
                  Open app
                </Link>
              ) : (
                <>
                  <Button to="/login" variant="secondary" onClick={() => setOpen(false)}>
                    Log In
                  </Button>
                  <Button to="/register" onClick={() => setOpen(false)}>
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
