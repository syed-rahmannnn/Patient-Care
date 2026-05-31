import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Nurses from './pages/Nurses'
import Requests from './pages/Requests'
import RoomDetail from './pages/RoomDetail'
import RoomsBeds from './pages/RoomsBeds'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading)
    return (
      <div className="grid min-h-screen place-items-center bg-app">
        <Spinner className="h-7 w-7" />
      </div>
    )
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="rooms" element={<RoomsBeds />} />
        <Route path="rooms/:roomId" element={<RoomDetail />} />
        <Route path="nurses" element={<Nurses />} />
        <Route path="requests" element={<Requests />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
