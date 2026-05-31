import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  BedDouble,
  BellRing,
  LayoutDashboard,
  LogOut,
  Menu,
  Users,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { Avatar, cn, IconButton } from './ui'

const NAV = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/rooms', label: 'Rooms & Beds', icon: BedDouble, end: false },
  { to: '/app/nurses', label: 'Nurses', icon: Users, end: false },
  { to: '/app/requests', label: 'Requests', icon: BellRing, end: false },
]

function titleFor(pathname: string): string {
  if (pathname.startsWith('/app/rooms')) return 'Rooms & Beds'
  if (pathname.startsWith('/app/nurses')) return 'Nurses'
  if (pathname.startsWith('/app/requests')) return 'Requests'
  return 'Dashboard'
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-white">
        <Activity size={20} className="text-black" strokeWidth={2.4} />
      </div>
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">Patient Care</div>
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
          Management
        </div>
      </div>
    </div>
  )
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="flex h-full flex-col">
      <div className="px-5 py-5">
        <Brand />
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'relative flex h-10 items-center gap-3 rounded-[10px] px-3 text-sm transition',
                isActive ? 'bg-white/6 text-fg' : 'text-muted hover:bg-white/4 hover:text-fg2',
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-white" />
                )}
                <item.icon size={18} />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 rounded-[12px] border border-line bg-card p-3">
        <div className="flex items-center gap-3">
          <Avatar name={user?.display_name || user?.email || 'A'} size={34} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-medium">{user?.display_name || 'Administrator'}</div>
            <div className="truncate text-[12px] text-muted">{user?.email}</div>
          </div>
          <IconButton
            aria-label="Sign out"
            title="Sign out"
            onClick={() => {
              logout()
              navigate('/')
            }}
          >
            <LogOut size={17} />
          </IconButton>
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-app">
      {/* Sidebar — fixed on desktop */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-line bg-surface lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-line bg-surface">
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        {/* Topbar */}
        <header className="glass sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line px-4 sm:px-6">
          <IconButton className="lg:hidden" aria-label="Menu" onClick={() => setOpen(true)}>
            <Menu size={20} />
          </IconButton>
          <h1 className="text-lg font-semibold tracking-tight sm:text-xl">{titleFor(location.pathname)}</h1>
          <div className="flex-1" />
          <Avatar name={user?.display_name || user?.email || 'A'} size={32} />
        </header>

        <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
