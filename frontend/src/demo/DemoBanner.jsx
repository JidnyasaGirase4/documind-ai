import { Info } from 'lucide-react'
import { DEMO } from './config'

// Shown on every page of the public demo so nobody mistakes it for the real product.
export function DemoBanner() {
  if (!DEMO) return null
  return (
    <div role="note" className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 bg-brand-900 px-4 py-2 text-center text-sm text-white">
      <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        <strong>Live demo with sample data.</strong> Everything runs in your browser; AI answers are simplified, and uploads and sharing are switched off.
      </span>
      <a className="font-semibold underline underline-offset-2" href="https://github.com/JidnyasaGirase4/documind-ai" target="_blank" rel="noreferrer">
        Get the full app
      </a>
    </div>
  )
}
