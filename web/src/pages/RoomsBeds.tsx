import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, DoorOpen, Plus, Search } from 'lucide-react'
import { api } from '../api/client'
import type { Room } from '../api/types'
import { Button, EmptyState, Field, Input, Loading, Modal, StatusPill } from '../components/ui'

function RoomCard({ room }: { room: Room }) {
  return (
    <Link
      to={`/app/rooms/${room.id}`}
      className="card group flex flex-col gap-4 p-5 transition hover:border-white/15 hover:bg-cardhover"
    >
      <div className="flex items-start justify-between">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/6 text-fg2">
          <DoorOpen size={20} />
        </div>
        <ChevronRight size={18} className="text-muted transition group-hover:translate-x-0.5" />
      </div>
      <div>
        <div className="text-[17px] font-semibold">{room.name}</div>
        <div className="mt-1 text-[13px] text-muted">
          {room.bed_count} bed{room.bed_count === 1 ? '' : 's'}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {room.active_bed_count > 0 ? (
          <StatusPill tone="active" dot>
            {room.active_bed_count} active
          </StatusPill>
        ) : (
          <StatusPill tone="inactive" dot>
            None active
          </StatusPill>
        )}
        {room.bed_count - room.active_bed_count > 0 && (
          <StatusPill tone="inactive">
            {room.bed_count - room.active_bed_count} inactive
          </StatusPill>
        )}
      </div>
    </Link>
  )
}

export default function RoomsBeds() {
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function load() {
    try {
      setRooms(await api.get<Room[]>('/rooms'))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
  }, [])

  async function addRoom(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setErr('')
    try {
      await api.post<Room>('/rooms', { name: name.trim() })
      setName('')
      setAdding(false)
      await load()
    } catch {
      setErr('Could not create the room.')
    } finally {
      setBusy(false)
    }
  }

  const filtered = rooms.filter((r) => r.name.toLowerCase().includes(q.toLowerCase()))

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search rooms…"
            className="pl-9"
          />
        </div>
        <Button variant="primary" onClick={() => setAdding(true)}>
          <Plus size={16} /> Add Room
        </Button>
      </div>

      {loading ? (
        <Loading />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<DoorOpen size={22} />}
          title={q ? 'No matching rooms' : 'No rooms yet'}
          hint={q ? 'Try a different search.' : 'Create your first room to start adding beds.'}
          action={
            !q && (
              <Button variant="primary" onClick={() => setAdding(true)}>
                <Plus size={16} /> Add Room
              </Button>
            )
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map((r) => (
            <RoomCard key={r.id} room={r} />
          ))}
        </div>
      )}

      <Modal
        open={adding}
        onClose={() => setAdding(false)}
        title="Add Room"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={addRoom} disabled={busy || !name.trim()}>
              Create Room
            </Button>
          </>
        }
      >
        <form onSubmit={addRoom}>
          <Field label="Room name / number">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Room 104"
              autoFocus
            />
          </Field>
          {err && <p className="mt-2 text-sm text-[#fca5a5]">{err}</p>}
        </form>
      </Modal>
    </div>
  )
}
