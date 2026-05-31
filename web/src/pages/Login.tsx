import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import FluidParticles from '../components/FluidParticles'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { Button, Field, Input, Spinner } from '../components/ui'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@patient.care')
  const [password, setPassword] = useState('Test1234!')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email.trim().toLowerCase(), password)
      navigate('/app')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError('Invalid email or password.')
      else setError('Could not sign in. Make sure the server is running.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-base px-4 text-fg">
      <FluidParticles />
      <div className="pointer-events-none absolute inset-0 bg-black/30" />

      <Link
        to="/"
        className="absolute left-6 top-6 z-10 inline-flex items-center gap-1.5 text-sm text-muted transition hover:text-fg"
      >
        <ArrowLeft size={16} /> Back
      </Link>

      <div className="glass animate-fade-up relative z-10 w-full max-w-[420px] rounded-[20px] border border-white/10 p-7 shadow-2xl">
        <h1 className="text-xl font-semibold tracking-tight">Welcome back</h1>
        <p className="mt-1 text-sm text-muted">Sign in to the admin dashboard.</p>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          <Field label="Email">
            <Input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@patient.care"
              required
            />
          </Field>
          <Field label="Password">
            <div className="relative">
              <Input
                type={show ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-fg"
                aria-label={show ? 'Hide password' : 'Show password'}
              >
                {show ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
          </Field>

          {error && (
            <div className="rounded-[10px] border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-[#fca5a5]">
              {error}
            </div>
          )}

          <Button type="submit" variant="primary" className="h-11 w-full" disabled={busy}>
            {busy ? <Spinner /> : 'Sign In'}
          </Button>
        </form>

        <div className="mt-5 rounded-[10px] border border-line bg-card px-3 py-2.5 text-[12px] text-muted">
          Demo admin — <span className="font-mono text-fg2">admin@patient.care</span> ·{' '}
          <span className="font-mono text-fg2">Test1234!</span>
        </div>
      </div>
    </div>
  )
}
