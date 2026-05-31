import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import FluidParticles from '../components/FluidParticles'
import { useAuth } from '../auth/AuthContext'

export default function Landing() {
  const { user } = useAuth()
  return (
    <div className="relative min-h-screen overflow-hidden bg-base text-fg">
      <FluidParticles />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/0 via-black/0 to-black/50" />

      <header className="relative z-10 flex items-center justify-between px-6 py-6 sm:px-10">
        <div className="text-[15px] font-semibold tracking-tight">Patient Care</div>
        <Link
          to={user ? '/app' : '/login'}
          className="inline-flex h-10 items-center gap-1.5 rounded-full bg-white px-5 text-sm font-semibold text-black transition hover:bg-zinc-200"
        >
          {user ? 'Open dashboard' : 'Login'}
          <ArrowRight size={16} />
        </Link>
      </header>

      <main className="relative z-10 flex min-h-[calc(100vh-88px)] flex-col items-center justify-center px-6 pb-20 text-center">
        <h1
          className="animate-fade-up font-extrabold leading-[0.95] tracking-[-0.04em]"
          style={{ fontSize: 'clamp(56px, 9vw, 124px)' }}
        >
          Patient Care
        </h1>
        <div
          className="animate-fade-up mt-1 font-light tracking-[-0.02em] text-white/70"
          style={{ fontSize: 'clamp(30px, 5.5vw, 72px)', animationDelay: '60ms' }}
        >
          Management
        </div>
        <p
          className="animate-fade-up mt-7 max-w-[520px] text-base leading-relaxed text-muted"
          style={{ animationDelay: '140ms' }}
        >
          Manage rooms, beds, and nurse response in real time — every request from a patient's
          connected device routed to the right caregiver.
        </p>
      </main>
    </div>
  )
}
