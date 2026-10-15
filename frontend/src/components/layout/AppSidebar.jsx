import { NavLink } from 'react-router-dom'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { Logo } from '../common/Logo'
import { Tooltip } from '../common/Tooltip'
import { useAuth } from '../../context/AuthContext'
import { NAV_ITEMS } from './navItems'
import { cx } from '../../utils/format'

function initials(user) {
  return (user?.name || user?.email || '?')
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join('')
}

export function SidebarContent({ collapsed = false, onNavigate }) {
  const { user } = useAuth()
  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-gradient-to-b from-plum-900 to-plum-950 text-stone-300">
      <div className="pointer-events-none absolute -left-16 -top-16 h-48 w-48 rounded-full bg-brand-600/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 -right-10 h-40 w-40 rounded-full bg-gold-400/10 blur-3xl" />
      <div className={cx('relative flex h-14 items-center', collapsed ? 'justify-center' : 'px-4')}>
        {collapsed ? <Logo dark className="[&>span]:hidden" /> : <Logo to="/app/dashboard" dark />}
      </div>
      <nav aria-label="Main" className="relative flex-1 space-y-1 overflow-y-auto px-3 pb-3 pt-2">
        {!collapsed && <p className="px-3 pb-1 text-[12px] font-bold uppercase tracking-[0.16em] text-plum-200/60">Menu</p>}
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
          const link = (
            <NavLink
              key={to}
              to={to}
              onClick={onNavigate}
              aria-label={collapsed ? label : undefined}
              className={({ isActive }) =>
                cx(
                  'group relative flex items-center gap-3 rounded-xl px-3 py-2 text-[15px] font-semibold transition-all duration-200',
                  collapsed && 'justify-center px-0',
                  isActive ? 'bg-white text-plum-900 shadow-lift' : 'text-plum-100/70 hover:bg-white/10 hover:text-white',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cx('h-[18px] w-[18px] shrink-0 transition-transform duration-200 group-hover:scale-110', isActive && 'text-brand-600')}
                    aria-hidden="true"
                  />
                  {!collapsed && <span>{label}</span>}
                  {isActive && !collapsed && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-600" aria-hidden="true" />}
                </>
              )}
            </NavLink>
          )
          return collapsed ? (
            <Tooltip key={to} text={label} side="right">
              {link}
            </Tooltip>
          ) : (
            link
          )
        })}
      </nav>
      {user && !collapsed && (
        <div className="relative m-3 flex items-center gap-3 rounded-xl bg-white/10 p-3 ring-1 ring-inset ring-white/10">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-700 text-xs font-bold text-white">
            {initials(user)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{user.name || user.email}</p>
            {user.name && <p className="truncate text-xs text-plum-100/70">{user.email}</p>}
          </div>
        </div>
      )}
    </div>
  )
}

// Floating, inset sidebar (a rounded card with a margin around it).
export function AppSidebar({ collapsed, onToggle }) {
  const width = collapsed ? 92 : 256
  return (
    <aside className="relative hidden shrink-0 transition-[width] duration-300 ease-out lg:block" style={{ width }} aria-label="Sidebar">
      <div className="fixed inset-y-0 left-0 p-3 transition-[width] duration-300 ease-out" style={{ width }}>
        <div className="relative h-full">
          <div className="h-full overflow-hidden rounded-2xl shadow-pop">
            <SidebarContent collapsed={collapsed} />
          </div>
          <button
            type="button"
            onClick={onToggle}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            className="absolute -right-3 top-[4.25rem] flex h-6 w-6 items-center justify-center rounded-full border border-line bg-surface text-muted shadow-card transition-colors hover:text-brand-600"
          >
            {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </aside>
  )
}
