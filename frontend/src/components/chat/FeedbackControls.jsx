import { useState } from 'react'
import { Check, Loader2, ThumbsDown, ThumbsUp } from 'lucide-react'
import { Button } from '../common/Button'

const REASONS = [
  ['inaccurate', 'Inaccurate'],
  ['missing_information', 'Missing information'],
  ['wrong_source', 'Wrong source or page'],
  ['unclear', 'Unclear'],
  ['other', 'Other'],
]

// Thumbs up/down on an answer. A thumbs-down opens a small form for a reason and an optional note.
// `onSubmit({ rating, category, comment })` and `onClear()` must return promises.
export function FeedbackControls({ feedback, onSubmit, onClear }) {
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState(null) // { category, comment } while the thumbs-down form is open
  const [error, setError] = useState('')

  const run = async (fn) => {
    setBusy(true)
    setError('')
    try {
      await fn()
      setForm(null)
    } catch (err) {
      setError(err.message || 'Could not save your feedback.')
    } finally {
      setBusy(false)
    }
  }

  const toggle = (rating) => {
    if (busy) return
    if (feedback?.rating === rating && !form) {
      run(onClear)
      return
    }
    if (rating === 'up') {
      run(() => onSubmit({ rating: 'up' }))
      return
    }
    setForm({ category: feedback?.category ?? '', comment: feedback?.comment ?? '' })
  }

  const btn = (active) =>
    `inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs hover:bg-stone-100 disabled:opacity-60 ${active ? 'bg-brand-50 font-medium text-brand-700' : 'text-muted hover:text-ink'}`

  return (
    <div className="inline-flex flex-col" data-testid="feedback-controls">
      <div className="flex items-center gap-1" role="group" aria-label="Rate this answer">
        <button type="button" onClick={() => toggle('up')} disabled={busy} aria-pressed={feedback?.rating === 'up'} aria-label="Good answer" className={btn(feedback?.rating === 'up')}>
          <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button type="button" onClick={() => toggle('down')} disabled={busy} aria-pressed={feedback?.rating === 'down'} aria-label="Bad answer" className={btn(feedback?.rating === 'down')}>
          <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        {busy && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted" aria-label="Saving" />}
        {!busy && feedback && !form && (
          <span className="inline-flex items-center gap-1 text-xs text-muted" role="status">
            <Check className="h-3 w-3" aria-hidden="true" />
            Thanks for the feedback
          </span>
        )}
      </div>
      {form && (
        <form
          className="mt-2 w-full max-w-sm space-y-2 rounded-control border border-line bg-surface p-3 text-sm"
          onSubmit={(e) => {
            e.preventDefault()
            run(() => onSubmit({ rating: 'down', category: form.category || null, comment: form.comment.trim() || null }))
          }}
        >
          <label className="block text-xs font-medium text-ink">
            What was wrong?
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="mt-1 h-9 w-full rounded-control border border-line bg-surface px-2 text-sm"
            >
              <option value="">Choose a reason (optional)</option>
              {REASONS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-ink">
            Add a note (optional)
            <textarea
              value={form.comment}
              maxLength={2000}
              rows={3}
              onChange={(e) => setForm({ ...form, comment: e.target.value })}
              className="mt-1 w-full rounded-control border border-line bg-surface p-2 text-sm"
            />
          </label>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setForm(null)} disabled={busy}>
              Cancel
            </Button>
            <Button size="sm" type="submit" loading={busy}>
              Send feedback
            </Button>
          </div>
        </form>
      )}
      {error && (
        <p role="alert" className="mt-1 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
