import { BarChart3, FileText, History, LayoutDashboard, MessageSquareText, Settings } from 'lucide-react'

export const NAV_ITEMS = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/app/documents', label: 'My Documents', icon: FileText },
  { to: '/app/assistant', label: 'AI Assistant', icon: MessageSquareText },
  { to: '/app/history', label: 'Chat History', icon: History },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

export function itemForPath(pathname) {
  return NAV_ITEMS.find((i) => pathname === i.to || pathname.startsWith(`${i.to}/`))
}

export function titleForPath(pathname) {
  return itemForPath(pathname)?.label ?? 'DocuMind AI'
}
