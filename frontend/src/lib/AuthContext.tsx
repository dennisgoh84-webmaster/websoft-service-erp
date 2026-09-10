import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, clearToken, getToken, login as apiLogin, setToken } from './api'
import type { Company, CurrentUser } from './api'

interface AuthState {
  user: CurrentUser | null
  /** Companies this user may work in. More than one -> the switcher shows. */
  companies: Company[]
  /** The company they are currently working in -- everything is scoped to it. */
  activeCompany: Company | null
  /** module_key -> can this user reach it right now (Group Authority AND Module
   * Control both say yes), re-read on every login/refresh/company switch since
   * both can differ per company. Drives which nav links show at all. */
  moduleAccess: Record<string, boolean>
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  switchCompany: (companyId: string) => Promise<void>
  /** Re-read the current user + companies (e.g. after Company Setup edits). */
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [moduleAccess, setModuleAccess] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)

  async function loadSession() {
    const me = await api.me()
    setUser(me)
    try {
      setCompanies(await api.listMyCompanies())
    } catch {
      // A company list is a nice-to-have for the header; never block sign-in on it.
      setCompanies([])
    }
    try {
      setModuleAccess(await api.myModuleAccess())
    } catch {
      // Same: never block sign-in on it, just hide every gated nav link.
      setModuleAccess({})
    }
  }

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    loadSession()
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const token = await apiLogin(email, password)
    setToken(token)
    await loadSession()
  }

  function logout() {
    clearToken()
    setUser(null)
    setCompanies([])
    setModuleAccess({})
  }

  async function switchCompany(companyId: string) {
    await api.switchCompany(companyId)
    await loadSession()
  }

  const activeCompany = companies.find((c) => c.id === user?.company_id) ?? null

  return (
    <AuthContext.Provider
      value={{
        user,
        companies,
        activeCompany,
        moduleAccess,
        loading,
        login,
        logout,
        switchCompany,
        refresh: loadSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
