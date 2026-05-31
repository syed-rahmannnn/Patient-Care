import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, clearTokens, getToken, setTokens } from '../api/client'
import type { User } from '../api/types'

interface AuthCtx {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx>(null!)
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      if (!getToken()) {
        setLoading(false)
        return
      }
      try {
        setUser(await api.get<User>('/auth/me'))
      } catch {
        clearTokens()
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function login(email: string, password: string) {
    const t = await api.post<{ access_token: string; refresh_token: string }>('/auth/login', {
      email,
      password,
    })
    setTokens(t.access_token, t.refresh_token)
    setUser(await api.get<User>('/auth/me'))
  }

  function logout() {
    clearTokens()
    setUser(null)
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}
