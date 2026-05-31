const ACCESS = 'pc.access'
const REFRESH = 'pc.refresh'

export function getToken(): string | null {
  return localStorage.getItem(ACCESS)
}
export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS, access)
  localStorage.setItem(REFRESH, refresh)
}
export function clearTokens() {
  localStorage.removeItem(ACCESS)
  localStorage.removeItem(REFRESH)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function refresh(): Promise<boolean> {
  const rt = localStorage.getItem(REFRESH)
  if (!rt) return false
  const r = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: rt }),
  })
  if (!r.ok) {
    clearTokens()
    return false
  }
  const d = await r.json()
  setTokens(d.access_token, d.refresh_token)
  return true
}

async function request<T>(method: string, path: string, body?: unknown, retry = true): Promise<T> {
  const headers: Record<string, string> = {}
  const tok = getToken()
  if (tok) headers['Authorization'] = `Bearer ${tok}`
  const opts: RequestInit = { method, headers }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`/api/v1${path}`, opts)
  if (res.status === 401 && retry) {
    if (await refresh()) return request<T>(method, path, body, false)
    clearTokens()
  }
  if (!res.ok) {
    let msg: string = res.statusText
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j)
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, msg)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(p: string) => request<T>('GET', p),
  post: <T>(p: string, b?: unknown) => request<T>('POST', p, b),
  del: <T = void>(p: string) => request<T>('DELETE', p),
}

/** ws(s):// URL on the current origin — Vite proxies /ws in dev, FastAPI serves it in prod. */
export function wsUrl(path: string): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}${path}`
}
