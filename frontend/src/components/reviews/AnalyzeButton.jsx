import { useEffect, useRef, useState } from 'react'
import { ScanSearch } from 'lucide-react'
import { Button } from '../common/Button'
import { useToast } from '../../context/ToastContext'
import { conflictService } from '../../services'
import { pluralize } from '../../utils/format'

const POLL_MS = 2500

// Starts a conflict analysis for a document or collection and follows it until it finishes.
export function AnalyzeButton({ documentId, collectionId, label = 'Analyze for conflicts', onDone }) {
  const toast = useToast()
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const timer = useRef(null)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
      clearTimeout(timer.current)
    }
  }, [])

  const follow = async (id) => {
    try {
      const r = await conflictService.getReport(id)
      if (!alive.current) return
      setReport(r)
      if (r.status === 'running') {
        timer.current = setTimeout(() => follow(id), POLL_MS)
        return
      }
      if (r.status === 'failed') {
        setError(r.error || 'The analysis failed.')
      } else {
        toast.success(r.created ? `${r.created} potential ${r.created === 1 ? 'conflict' : 'conflicts'} found. Please review them.` : 'Analysis finished. No new potential conflicts were found.')
      }
      onDone?.(r)
    } catch (err) {
      if (alive.current) setError(err.message)
    }
  }

  const start = async () => {
    setError('')
    setReport({ status: 'running' })
    try {
      const r = await conflictService.analyze({ documentId, collectionId })
      if (!alive.current) return
      setReport(r)
      follow(r.id)
    } catch (err) {
      setReport(null)
      setError(err.message)
    }
  }

  const running = report?.status === 'running'
  return (
    <div>
      <Button size="sm" onClick={start} loading={running}>
        <ScanSearch className="h-4 w-4" aria-hidden="true" />
        {running ? 'Analyzing…' : label}
      </Button>
      {running && (
        <p role="status" className="mt-2 text-xs text-muted">
          Comparing passages with an AI model. This can take a few minutes with a local model; you can leave this page open.
        </p>
      )}
      {report && report.status === 'completed' && (
        <p role="status" className="mt-2 text-xs text-muted">
          Examined {pluralize(report.passages, 'passage')} and {pluralize(report.pairs, 'candidate pair')}
          {report.unparsed ? `; ${pluralize(report.unparsed, 'AI answer')} could not be read and ${report.unparsed === 1 ? 'was' : 'were'} ignored` : ''}.
          {report.error ? ` Stopped early: ${report.error}` : ''}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
