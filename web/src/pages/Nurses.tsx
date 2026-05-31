import { useEffect, useState, type FormEvent } from 'react'
import { Plus, Search, Trash2, Users } from 'lucide-react'
import { api } from '../api/client'
import type { Nurse } from '../api/types'
import {
  Avatar,
  Button,
  EmptyState,
  Field,
  Input,
  Loading,
  Modal,
  StatusPill,
} from '../components/ui'

function Assignment({ nurse }: { nurse: Nurse }) {
  if (nurse.assignments.length === 0) return <span className="text-faint">—</span>
  const a = nurse.assignments[0]
  return (
    <span>
      {a.room_name}
      {nurse.assignments.length > 1 && (
        <span className="ml-1.5 rounded-full bg-white/8 px-1.5 py-0.5 text-[11px] text-muted">
          +{nurse.assignments.length - 1}
        </span>
      )}
    </span>
  )
}

export default function Nurses() {
  const [nurses, setNurses] = useState<Nurse[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  const [adding, setAdding] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('Test1234!')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const [remove, setRemove] = useState<Nurse | null>(null)

  async function load() {
    try {
      setNurses(await api.get<Nurse[]>('/nurses'))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
  }, [])

  async function addNurse(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setBusy(true)
    setErr('')
    try {
      await api.post<Nurse>('/nurses', {
        email: email.trim().toLowerCase(),
        password,
        display_name: name.trim(),
      })
      setEmail('')
      setName('')
      setPassword('Test1234!')
      setAdding(false)
      await load()
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : 'Could not create nurse.')
    } finally {
      setBusy(false)
    }
  }

  async function confirmRemove() {
    if (!remove) return
    await api.del(`/nurses/${remove.id}`)
    setRemove(null)
    await load()
  }

  const filtered = nurses.filter(
    (n) =>
      n.display_name.toLowerCase().includes(q.toLowerCase()) ||
      n.email.toLowerCase().includes(q.toLowerCase()),
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search nurses…"
            className="pl-9"
          />
        </div>
        <Button variant="primary" onClick={() => setAdding(true)}>
          <Plus size={16} /> Add Nurse
        </Button>
      </div>

      {loading ? (
        <Loading />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Users size={22} />}
          title={q ? 'No matching nurses' : 'No nurses yet'}
          hint={q ? 'Try a different search.' : 'Add nurse logins for the mobile app.'}
        />
      ) : (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-[0.08em] text-muted">
                  <th className="px-5 py-3 font-semibold">Nurse</th>
                  <th className="px-5 py-3 font-semibold">Email</th>
                  <th className="px-5 py-3 font-semibold">Assigned Room</th>
                  <th className="px-5 py-3 font-semibold">Serving Bed</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th className="px-5 py-3 font-semibold"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((n) => (
                  <tr key={n.id} className="border-b border-line/60 transition hover:bg-white/[0.03]">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={n.display_name || n.email} size={28} />
                        <span className="font-medium">{n.display_name || '—'}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-fg2">{n.email}</td>
                    <td className="px-5 py-3 text-fg2">
                      <Assignment nurse={n} />
                    </td>
                    <td className="px-5 py-3 text-fg2">
                      {n.assignments[0]?.bed_label ?? <span className="text-faint">—</span>}
                    </td>
                    <td className="px-5 py-3">
                      {n.online ? (
                        <StatusPill tone="active" dot pulse>
                          Online
                        </StatusPill>
                      ) : (
                        <StatusPill tone="inactive" dot>
                          Offline
                        </StatusPill>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button variant="danger" size="sm" onClick={() => setRemove(n)}>
                        <Trash2 size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add nurse */}
      <Modal
        open={adding}
        onClose={() => setAdding(false)}
        title="Add Nurse"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={addNurse} disabled={busy || !email.trim()}>
              Create Nurse
            </Button>
          </>
        }
      >
        <form onSubmit={addNurse} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nurse6@patient.care"
              autoFocus
            />
          </Field>
          <Field label="Display name (optional)">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Nurse Six" />
          </Field>
          <Field label="Password">
            <Input value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          {err && <p className="text-sm text-[#fca5a5]">{err}</p>}
        </form>
      </Modal>

      {/* Remove nurse */}
      <Modal
        open={!!remove}
        onClose={() => setRemove(null)}
        title="Remove nurse?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRemove(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmRemove}>
              <Trash2 size={15} /> Remove
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">
          Remove <span className="font-medium text-fg">{remove?.display_name || remove?.email}</span> and
          their bed assignments. This cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
