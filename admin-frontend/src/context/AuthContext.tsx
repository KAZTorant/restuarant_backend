import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { adminApi } from '../api/admin'
import type { AdminUser, Navigation } from '../types/admin'

interface AuthContextValue {
  user: AdminUser | null
  navigation: Navigation | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshNav: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null)
  const [navigation, setNavigation] = useState<Navigation | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshNav = async () => {
    const nav = await adminApi.navigation()
    setNavigation(nav)
    setUser(nav.user)
  }

  useEffect(() => {
    adminApi.me()
      .then(async (u) => {
        setUser(u)
        await refreshNav()
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (username: string, password: string) => {
    const u = await adminApi.login(username, password)
    setUser(u)
    await refreshNav()
  }

  const logout = async () => {
    await adminApi.logout()
    setUser(null)
    setNavigation(null)
  }

  return (
    <AuthContext.Provider value={{ user, navigation, loading, login, logout, refreshNav }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function useRequireAuth() {
  const auth = useAuth()
  return auth
}
