import { BookOpen, Briefcase, Code2, FlaskConical, Folder, Scale, ShieldCheck, Star, Users, Wallet } from 'lucide-react'

// Must match COLORS / ICONS in backend/app/services/knowledge_service.py.
export const COLORS = {
  burgundy: '#8a1c3c',
  charcoal: '#3b3b44',
  rose: '#c2415d',
  amber: '#b7791f',
  emerald: '#2f855a',
  sky: '#2b6cb0',
  violet: '#6b46c1',
  slate: '#64748b',
}

export const ICONS = {
  folder: Folder,
  book: BookOpen,
  briefcase: Briefcase,
  scale: Scale,
  flask: FlaskConical,
  wallet: Wallet,
  users: Users,
  shield: ShieldCheck,
  code: Code2,
  star: Star,
}

export function CollectionIcon({ collection, className = 'h-5 w-5' }) {
  const Icon = ICONS[collection?.icon] || Folder
  return (
    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white" style={{ backgroundColor: COLORS[collection?.color] || COLORS.burgundy }}>
      <Icon className={className} aria-hidden="true" />
    </span>
  )
}
