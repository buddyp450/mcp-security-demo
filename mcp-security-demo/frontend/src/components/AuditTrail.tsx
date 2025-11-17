import type { EventRecord } from '../hooks/useWebSocket'
import type { TestCaseId } from '../types/testCases'

interface Props {
  events: EventRecord[]
  focus?: TestCaseId
  title?: string
  compact?: boolean
  limit?: number
}

const levelStyles: Record<EventRecord['level'], string> = {
  info: 'text-slate-200',
  warning: 'text-yellow-300',
  alert: 'text-orange-400',
  critical: 'text-red-400'
}

export function AuditTrail({ events, focus, title, compact, limit }: Props) {
  const filtered = focus ? events.filter((evt) => evt.test_case === focus) : events
  const visible = limit ? filtered.slice(-limit) : filtered
  const containerClasses = compact
    ? 'rounded-lg border border-slate-700 bg-black/40 p-3'
    : 'rounded-xl border border-slate-700 bg-black/40 p-4'
  const headingClasses = compact ? 'text-base font-semibold' : 'text-lg font-semibold'
  const listClasses = compact ? 'mt-2 space-y-1 text-xs' : 'mt-3 space-y-2 text-sm'
  return (
    <div className={containerClasses}>
      <div className={headingClasses}>{title ?? 'Live Policy Audit Trail'}</div>
      <div className={listClasses}>
        {visible.map((evt) => (
          <div key={`${evt.timestamp}-${evt.phase}-${evt.test_case}`} className={levelStyles[evt.level]}>
            <span className="text-slate-400">[{new Date(evt.timestamp).toLocaleTimeString()}]</span> {evt.message}
          </div>
        ))}
        {visible.length === 0 && <div className="text-slate-500">No events yet.</div>}
      </div>
    </div>
  )
}
