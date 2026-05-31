import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Check,
  Copy,
  Cpu,
  Plus,
  RefreshCw,
  Trash2,
  Unplug,
} from 'lucide-react'
import { api } from '../api/client'
import type { Bed, DeviceToken, RoomDetail as RoomDetailT } from '../api/types'
import {
  Avatar,
  Button,
  Field,
  IconButton,
  Input,
  Loading,
  Modal,
  Overline,
  StatusPill,
} from '../components/ui'

function BedCard({
  bed,
  onRegenerate,
  onPair,
  onUnpair,
  onDelete,
}: {
  bed: Bed
  onRegenerate: (b: Bed) => void
  onPair: (b: Bed) => void
  onUnpair: (b: Bed) => void
  onDelete: (b: Bed) => void
}) {
  const [copied, setCopied] = useState(false)
  const active = bed.status === 'active'

  function copy() {
    void navigator.clipboard.writeText(bed.join_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="card flex flex-col gap-4 p-5">
      <div className="flex items-center justify-between">
        <div className="text-[17px] font-semibold">{bed.label}</div>
        {active ? (
          <StatusPill tone="active" dot pulse={bed.connected}>
            Active
          </StatusPill>
        ) : (
          <StatusPill tone="inactive" dot>
            Inactive
          </StatusPill>
        )}
      </div>

      {/* Join code */}
      <div>
        <Overline>Join code</Overline>
        <div className="mt-1.5 flex items-center gap-2">
          <code className="rounded-lg border border-line bg-black/30 px-3 py-1.5 font-mono text-[15px] tracking-[0.06em] text-fg">
            {bed.join_code}
          </code>
          <IconButton onClick={copy} title="Copy code">
            {copied ? <Check size={16} className="text-active" /> : <Copy size={16} />}
          </IconButton>
          <IconButton onClick={() => onRegenerate(bed)} title="Regenerate code">
            <RefreshCw size={16} />
          </IconButton>
        </div>
      </div>

      {/* Device */}
      <div>
        <Overline>Connected device</Overline>
        {bed.device ? (
          <div className="mt-1.5 flex items-center gap-2.5 rounded-[10px] border border-line bg-card px-3 py-2">
            <Cpu size={16} className="text-fg2" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-medium">{bed.device.name}</div>
              <div className="truncate font-mono text-[11px] text-muted">{bed.device.serial_id}</div>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 text-[12px] font-medium ${bed.connected ? 'text-activefg' : 'text-muted'}`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${bed.connected ? 'animate-pulse-dot bg-active' : 'bg-inactive'}`}
              />
              {bed.connected ? 'Connected' : 'Offline'}
            </span>
            <IconButton onClick={() => onUnpair(bed)} title="Unpair device">
              <Unplug size={15} />
            </IconButton>
          </div>
        ) : (
          <div className="mt-1.5 flex items-center justify-between rounded-[10px] border border-dashed border-line px-3 py-2">
            <span className="text-[13px] text-muted">No device paired</span>
            <Button size="sm" onClick={() => onPair(bed)}>
              <Plus size={14} /> Pair device
            </Button>
          </div>
        )}
      </div>

      {/* Nurses */}
      <div>
        <Overline>Nurses on this bed</Overline>
        {bed.nurses.length === 0 ? (
          <div className="mt-1.5 text-[13px] text-muted">No nurse joined yet</div>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            {bed.nurses.map((n) => (
              <div
                key={n.id}
                className="flex items-center gap-2 rounded-full border border-line bg-card py-1 pl-1 pr-3"
                title={n.email}
              >
                <Avatar name={n.display_name || n.email} size={22} />
                <span className="text-[12px] font-medium">{n.display_name || n.email}</span>
                {n.online && <span className="h-1.5 w-1.5 rounded-full bg-active" />}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-1 flex justify-end border-t border-line pt-3">
        <Button variant="danger" size="sm" onClick={() => onDelete(bed)}>
          <Trash2 size={14} /> Delete bed
        </Button>
      </div>
    </div>
  )
}

export default function RoomDetail() {
  const { roomId } = useParams()
  const [room, setRoom] = useState<RoomDetailT | null>(null)
  const [loading, setLoading] = useState(true)

  const [addingBed, setAddingBed] = useState(false)
  const [bedLabel, setBedLabel] = useState('')
  const [busy, setBusy] = useState(false)

  const [pairBed, setPairBed] = useState<Bed | null>(null)
  const [serial, setSerial] = useState('')
  const [devName, setDevName] = useState('')
  const [token, setToken] = useState<DeviceToken | null>(null)
  const [tokenCopied, setTokenCopied] = useState(false)

  const [deleteBed, setDeleteBed] = useState<Bed | null>(null)

  async function load() {
    try {
      setRoom(await api.get<RoomDetailT>(`/rooms/${roomId}`))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId])

  async function addBed(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.post<Bed>(`/rooms/${roomId}/beds`, { label: bedLabel.trim() })
      setBedLabel('')
      setAddingBed(false)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function regenerate(b: Bed) {
    await api.post<Bed>(`/beds/${b.id}/regenerate-code`)
    await load()
  }

  async function submitPair(e: FormEvent) {
    e.preventDefault()
    if (!pairBed || !serial.trim()) return
    setBusy(true)
    try {
      const result = await api.post<DeviceToken>(`/beds/${pairBed.id}/device`, {
        serial_id: serial.trim(),
        name: devName.trim(),
      })
      setPairBed(null)
      setSerial('')
      setDevName('')
      setToken(result)
      await load()
    } catch {
      /* surfaced inline below if needed */
    } finally {
      setBusy(false)
    }
  }

  async function unpair(b: Bed) {
    await api.del(`/beds/${b.id}/device`)
    await load()
  }

  async function confirmDelete() {
    if (!deleteBed) return
    await api.del(`/beds/${deleteBed.id}`)
    setDeleteBed(null)
    await load()
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-1.5 text-sm">
          <Link to="/app/rooms" className="inline-flex items-center gap-1 text-muted hover:text-fg">
            <ArrowLeft size={15} /> Rooms &amp; Beds
          </Link>
          <span className="text-faint">/</span>
          <span className="font-medium">{room?.name ?? '…'}</span>
        </div>
        <Button variant="primary" onClick={() => setAddingBed(true)}>
          <Plus size={16} /> Add Bed
        </Button>
      </div>

      {loading ? (
        <Loading />
      ) : !room ? (
        <p className="text-muted">Room not found.</p>
      ) : room.beds.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="font-semibold">No beds in {room.name}</p>
          <p className="mt-1 text-sm text-muted">Add a bed — each gets its own join code for nurses.</p>
          <div className="mt-4 flex justify-center">
            <Button variant="primary" onClick={() => setAddingBed(true)}>
              <Plus size={16} /> Add Bed
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {room.beds.map((b) => (
            <BedCard
              key={b.id}
              bed={b}
              onRegenerate={regenerate}
              onPair={setPairBed}
              onUnpair={unpair}
              onDelete={setDeleteBed}
            />
          ))}
        </div>
      )}

      {/* Add bed */}
      <Modal
        open={addingBed}
        onClose={() => setAddingBed(false)}
        title="Add Bed"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAddingBed(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={addBed} disabled={busy}>
              Create Bed
            </Button>
          </>
        }
      >
        <form onSubmit={addBed}>
          <Field label="Bed label (optional)">
            <Input
              value={bedLabel}
              onChange={(e) => setBedLabel(e.target.value)}
              placeholder="Leave blank for the next “Bed N”"
              autoFocus
            />
          </Field>
          <p className="mt-2 text-[12px] text-muted">A unique join code is generated automatically.</p>
        </form>
      </Modal>

      {/* Pair device */}
      <Modal
        open={!!pairBed}
        onClose={() => setPairBed(null)}
        title={`Pair device — ${pairBed?.label ?? ''}`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setPairBed(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={submitPair} disabled={busy || !serial.trim()}>
              Pair Device
            </Button>
          </>
        }
      >
        <form onSubmit={submitPair} className="space-y-4">
          <Field label="Device serial ID">
            <Input
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              placeholder="e.g. PCS-201"
              autoFocus
            />
          </Field>
          <Field label="Display name (optional)">
            <Input
              value={devName}
              onChange={(e) => setDevName(e.target.value)}
              placeholder="e.g. Bed 1 Call Device"
            />
          </Field>
        </form>
      </Modal>

      {/* Device token result */}
      <Modal open={!!token} onClose={() => setToken(null)} title="Device paired">
        <p className="text-sm text-muted">
          Copy this device token into the gateway's <span className="font-mono text-fg2">.env</span> as{' '}
          <span className="font-mono text-fg2">DEVICE_TOKEN</span>. It won't be shown again.
        </p>
        <div className="mt-3 flex items-start gap-2 rounded-[10px] border border-line bg-black/30 p-3">
          <code className="min-w-0 flex-1 break-all font-mono text-[12px] text-fg2">{token?.token}</code>
          <IconButton
            onClick={() => {
              if (token) void navigator.clipboard.writeText(token.token)
              setTokenCopied(true)
              setTimeout(() => setTokenCopied(false), 1500)
            }}
            title="Copy token"
          >
            {tokenCopied ? <Check size={16} className="text-active" /> : <Copy size={16} />}
          </IconButton>
        </div>
        <div className="mt-6 flex justify-end">
          <Button variant="primary" onClick={() => setToken(null)}>
            Done
          </Button>
        </div>
      </Modal>

      {/* Delete bed */}
      <Modal
        open={!!deleteBed}
        onClose={() => setDeleteBed(null)}
        title="Delete bed?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteBed(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              <Trash2 size={15} /> Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">
          This removes <span className="font-medium text-fg">{deleteBed?.label}</span>, its join code,
          paired device and nurse assignments. This cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
