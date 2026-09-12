import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type AdminUser } from './api'

interface AuthCtx {
  user: AdminUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('cc_token')
    if (!token) {
      setLoading(false)
      return
    }
    api.me().then(setUser).catch(() => localStorage.removeItem('cc_token')).finally(() => setLoading(false))
  }, [])

  const login = async (username: string, password: string) => {
    const res = await api.login(username, password)
    localStorage.setItem('cc_token', res.access_token)
    const me = await api.me()
    setUser(me)
  }

  const logout = () => {
    localStorage.removeItem('cc_token')
    setUser(null)
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
