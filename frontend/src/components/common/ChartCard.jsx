import { useId } from 'react'
import { Card, CardHeader } from './Card'

// Wraps a chart with a title, a plain-text summary (announced to screen readers)
// and a collapsible data table as an accessible alternative to the graphic.
export function ChartCard({ title, description, summary, columns, rows, children, empty }) {
  const summaryId = useId()
  return (
    <Card>
      <CardHeader title={title} description={description} />
      {empty ? (
        <p className="py-10 text-center text-sm text-muted">{empty}</p>
      ) : (
        <>
          <div role="img" aria-label={`${title} chart`} aria-describedby={summaryId}>
            {children}
          </div>
          <p id={summaryId} className="mt-3 text-sm text-muted">
            {summary}
          </p>
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer rounded font-medium text-brand-700">View data table</summary>
            <div className="mt-2 max-h-56 overflow-auto rounded-md border border-line">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">{title} data</caption>
                <thead className="bg-stone-50 text-xs uppercase text-muted">
                  <tr>
                    {columns.map((c) => (
                      <th key={c} scope="col" className="px-3 py-2 font-medium">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-t border-line">
                      {r.map((cell, j) => (
                        <td key={j} className="px-3 py-1.5 tabular-nums">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </Card>
  )
}
