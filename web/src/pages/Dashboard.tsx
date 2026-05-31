import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BedDouble, ChevronRight, DoorOpen, Radio, Users } from 'lucide-react'
import { api } from '../api/client'
import type { Alert, DashboardStats, Room } from '../api/types'
import { AlertIcon, RequestChip } from '../components/RequestChip'
import { Card, EmptyState, Loading, Overline, StatusPill } from '../components/ui'
import { timeAgo } from '../lib/format'

function Stat({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  sub?: string
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <Overline>{label}</Overline>
        <span className="text-muted">{icon}</span>
      </div>
      <div className="mt-3 text-[32px] font-bold leading-none">{value}</div>
      {sub && <div className="mt-1.5 text-[13px] text-muted">{sub}</div>}
    </Card>
  )
}

function RequestRow({ a }: { a: Alert }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <AlertIcon type={a.type} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">
            {a.room_name} · {a.bed_label}
          </span>
          <RequestChip type={a.type} />
        </div>
        <div className="mt-0.5 text-[12px] text-muted">{timeAgo(a.created_at)}</div>
      </div>
      {a.acknowledged_by_name ? (
        <StatusPill tone="acked" dot>
          {a.acknowledged_by_name}
        </StatusPill>
      ) : (
        <StatusPill tone="pending" dot pulse>
          Pending
        </StatusPill>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [reqs, setReqs] = useState<Alert[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const [s, r, rm] = await Promise.all([
          api.get<DashboardStats>('/dashboard/stats'),
          api.get<Alert[]>('/dashboard/requests?limit=8'),
          api.get<Room[]>('/rooms'),
        ])
        if (!alive) return
        setStats(s)
        setReqs(r)
        setRooms(rm)
      } catch {
        /* keep last good state */
      } finally {
        if (alive) setLoading(false)
      }
    }
    void load()
    const t = setInterval(load, 8000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  if (loading) return <Loading />

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat icon={<DoorOpen size={18} />} label="Rooms" value={stats?.rooms ?? 0} />
        <Stat icon={<BedDouble size={18} />} label="Beds" value={stats?.beds ?? 0} />
        <Stat
          icon={<Radio size={18} />}
          label="Active Beds"
          value={stats?.active_beds ?? 0}
          sub={`${stats?.connected_devices ?? 0} device${stats?.connected_devices === 1 ? '' : 's'} live`}
        />
        <Stat
          icon={<Users size={18} />}
          label="Nurses"
          value={stats?.nurses_total ?? 0}
          sub={`${stats?.nurses_online ?? 0} online`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Live requests */}
        <Card className="lg:col-span-2">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-base font-semibold">Live Requests</h2>
            {stats && stats.pending_requests > 0 && (
              <StatusPill tone="pending" dot pulse>
                {stats.pending_requests} pending
              </StatusPill>
            )}
          </div>
          {reqs.length === 0 ? (
            <EmptyState
              icon={<Radio size={22} />}
              title="No requests yet"
              hint="Requests from patient devices will appear here."
            />
          ) : (
            <div className="divide-y divide-line">
              {reqs.map((a) => (
                <RequestRow key={a.id} a={a} />
              ))}
            </div>
          )}
          <Link
            to="/app/requests"
            className="mt-3 inline-flex items-center gap-1 text-[13px] text-muted transition hover:text-fg"
          >
            View all requests <ChevronRight size={14} />
          </Link>
        </Card>

        {/* Rooms overview */}
        <Card>
          <h2 className="mb-3 text-base font-semibold">Rooms</h2>
          {rooms.length === 0 ? (
            <EmptyState icon={<DoorOpen size={22} />} title="No rooms" hint="Create one to get started." />
          ) : (
            <div className="space-y-2">
              {rooms.map((r) => (
                <Link
                  key={r.id}
                  to={`/app/rooms/${r.id}`}
                  className="flex items-center gap-3 rounded-[12px] border border-line bg-card px-3 py-2.5 transition hover:border-white/15 hover:bg-cardhover"
                >
                  <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/6 text-fg2">
                    <DoorOpen size={17} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{r.name}</div>
                    <div className="text-[12px] text-muted">
                      {r.bed_count} bed{r.bed_count === 1 ? '' : 's'} · {r.active_bed_count} active
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-muted" />
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
