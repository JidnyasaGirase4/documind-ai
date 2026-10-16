import { Fragment } from 'react'

const REGEX_SPECIALS = /[\\^$.*+?()[\]{}|]/g

// Splits `text` into plain and highlighted parts. Terms match at the start of a word (like the server); phrases match
// as a whole. Everything is regex-escaped, so user input can never form a pattern.
export function highlightParts(text, terms = [], phrases = []) {
  const units = [...phrases, ...terms].filter(Boolean).sort((a, b) => b.length - a.length)
  if (!text || units.length === 0) return [{ text: text ?? '', hit: false }]
  const body = units
    .map((u) =>
      u
        .trim()
        .split(/\s+/)
        .map((w) => w.replace(REGEX_SPECIALS, '\\$&'))
        .join('\\s+'),
    )
    .join('|')
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${body})[\\p{L}\\p{N}_]*`, 'giu')
  const parts = []
  let last = 0
  for (const m of text.matchAll(re)) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index), hit: false })
    parts.push({ text: m[0], hit: true })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ text: text.slice(last), hit: false })
  return parts
}

export function Highlighted({ text, terms, phrases }) {
  return (
    <>
      {highlightParts(text, terms, phrases).map((p, i) =>
        p.hit ? (
          <mark key={i} className="rounded bg-gold-100 px-0.5 text-ink">
            {p.text}
          </mark>
        ) : (
          <Fragment key={i}>{p.text}</Fragment>
        ),
      )}
    </>
  )
}
