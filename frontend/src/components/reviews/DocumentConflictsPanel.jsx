import { Card, CardHeader } from '../common/Card'
import { ErrorState } from '../common/ErrorState'
import { ListSkeleton } from '../common/LoadingSkeleton'
import { useAsync } from '../../hooks/useAsync'
import { conflictService } from '../../services'
import { AnalyzeButton } from './AnalyzeButton'
import { FindingList } from './ConflictFindings'

// Potential conflicts involving one document. Only findings whose two sources the viewer can read are ever returned.
export function DocumentConflictsPanel({ documentId, canManage, ready }) {
  const { data, error, loading, reload } = useAsync(() => conflictService.listFindings({ documentId, pageSize: 20 }), [documentId])
  return (
    <Card>
      <CardHeader
        title="Potential conflicts"
        description="AI-assisted: passages that may contradict other documents or earlier versions. Every finding shows its evidence and needs a person to check it."
        action={canManage && ready && <AnalyzeButton documentId={documentId} onDone={() => reload({ silent: true })} />}
      />
      {loading ? (
        <ListSkeleton rows={2} />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : (
        <FindingList findings={data.items} onChanged={() => reload({ silent: true })} emptyText={canManage ? 'Nothing has been flagged for this document. Use "Analyze for conflicts" to check it against your other documents.' : 'Nothing has been flagged for this document.'} />
      )}
    </Card>
  )
}
