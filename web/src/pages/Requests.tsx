import { useEffect, useMemo, useState } from 'react'
import { Check, Radio } from 'lucide-react'
import { api } from '../api/client'
import type { Alert, AlertType } from '../api/types'
import { AlertIcon, ALERT_META, RequestChip } from '../components/RequestChip'
import { Button, Card, EmptyState, Loading, StatusPill, cn } from '../components/ui'
import { timeAgo } from '../lib/format'

type TypeFilter = 'ALL' | AlertType
type StatusFilter = 'ALL' | 'PENDING' | 'RESOLVED'

const TYPE_FILTERS: TypeFilter[] = ['ALL', 'WATER', 'MEDICINE', 'HELP', 'BATHROOM', 'EMERGENCY']
const STATUS_FILTERS: StatusFilter[] = ['ALL', 'PENDING', 'RESOLVED']

function Toggle({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'h-8 rounded-full border px-3 text-[13px] font-medium transition',
        active
          ? 'border-white/20 bg-white/10 text-fg'
          : 'border-line bg-card text-muted hover:text-fg2',
      )}
    >
      {children}
    </button>
  )
}

export default function Requests() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [typeF, setTypeF] = useState<TypeFilter>('ALL')
  const [statusF, setStatusF] = useState<StatusFilter>('ALL')

  async function load() {
    try {
      setAlerts(await api.get<Alert[]>('/dashboard/requests?limit=100'))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [])

  async function ack(id: string) {
    await api.post(`/alerts/${id}/ack`)
    await load()
  }

  const filtered = useMemo(
    () =>
      alerts.filter((a) => {
        if (typeF !== 'ALL' && a.type !== typeF) return false
        if (statusF === 'PENDING' && a.acknowledged_by) return false
        if (statusF === 'RESOLVED' && !a.acknowledged_by) return false
        return true
      }),
    [alerts, typeF, statusF],
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {TYPE_FILTERS.map((t) => (
            <Toggle key={t} active={typeF === t} onClick={() => setTypeF(t)}>
              {t === 'ALL' ? 'All types' : ALERT_META[t].label}
            </Toggle>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {STATUS_FILTERS.map((s) => (
            <Toggle key={s} active={statusF === s} onClick={() => setStatusF(s)}>
              {s === 'ALL' ? 'All' : s === 'PENDING' ? 'Pending' : 'Resolved'}
            </Toggle>
          ))}
        </div>
      </div>

      {loading ? (
        <Loading />
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Radio size={22} />}
            title="No requests"
            hint="Nothing matches these filters yet."
          />
        </Card>
      ) : (
        <Card className="p-0">
          <div className="divide-y divide-line">
            {filtered.map((a) => (
              <div key={a.id} className="flex items-center gap-3 px-5 py-3.5">
                <AlertIcon type={a.type} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">
                      {a.room_name} · {a.bed_label}
                    </span>
                    <RequestChip type={a.type} />
                  </div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    {timeAgo(a.created_at)}
                    {a.acknowledged_by_name && ` · acknowledged by ${a.acknowledged_by_name}`}
                  </div>
                </div>
                {a.acknowledged_by ? (
                  <StatusPill tone="acked" dot>
                    Resolved
                  </StatusPill>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => ack(a.id)}>
                    <Check size={14} /> Acknowledge
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
