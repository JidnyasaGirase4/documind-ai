import { useEffect } from 'react'
import { X } from 'lucide-react'
import { SidebarContent } from './AppSidebar'

export function MobileNavigation({ open, onClose }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
      <div className="absolute inset-0 animate-fade-in bg-plum-950/60 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div className="relative h-full w-[17rem] max-w-[85vw] animate-slide-in-left">
        <SidebarContent onNavigate={onClose} />
        <button
          type="button"
          onClick={onClose}
          aria-label="Close menu"
          autoFocus
          className="absolute right-3 top-4 rounded-md p-1.5 text-stone-300 hover:bg-sidebar-hover hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
