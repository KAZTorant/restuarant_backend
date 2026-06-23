import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  ChevronDown, ChevronRight, LayoutDashboard, LogOut, Menu, X,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { cn } from '../ui'

const CUSTOM_LIST_MODELS: Record<string, string> = {
  'orders/statistics': '/statistics',
  'orders/summary': '/summary',
  'orders/withdrawnlist': '/withdrawn-list',
  'payments/paymentcalculation': '/payment-calculation',
  'tables/table': '/tables',
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { navigation, logout } = useAuth()
  const location = useLocation()
  const [openApps, setOpenApps] = useState<Record<string, boolean>>({})

  const toggleApp = (label: string) => {
    setOpenApps((prev) => ({ ...prev, [label]: !prev[label] }))
  }

  const modelPath = (app: string, model: string) => {
    const key = `${app}/${model}`
    return CUSTOM_LIST_MODELS[key] || `/models/${app}/${model}`
  }

  return (
    <aside className={cn(
      'fixed left-0 top-0 h-full bg-sidebar text-white flex flex-col transition-all duration-200 z-40',
      collapsed ? 'w-16' : 'w-64',
    )}>
      <div className="flex items-center justify-between px-4 h-14 border-b border-white/10">
        {!collapsed && <span className="font-bold text-lg tracking-tight">KAZZA</span>}
        <button onClick={onToggle} className="p-1.5 rounded-lg hover:bg-sidebar-hover">
          {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        <Link
          to="/"
          className={cn(
            'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
            location.pathname === '/' ? 'bg-primary text-white' : 'text-white/70 hover:bg-sidebar-hover hover:text-white',
          )}
        >
          <LayoutDashboard size={18} />
          {!collapsed && 'İdarə Paneli'}
        </Link>

        {navigation?.apps.map((app) => (
          <div key={app.app_label} className="mt-1">
            <button
              onClick={() => toggleApp(app.app_label)}
              className="flex items-center gap-2 w-full px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white/40 hover:text-white/70"
            >
              {!collapsed && (
                <>
                  {openApps[app.app_label] !== false ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  {app.name}
                </>
              )}
            </button>
            {(openApps[app.app_label] !== false) && app.models.map((model) => {
              const path = modelPath(model.app_label, model.model_name)
              const active = location.pathname.startsWith(path)
              return (
                <Link
                  key={`${model.app_label}.${model.model_name}`}
                  to={path}
                  title={model.name}
                  className={cn(
                    'flex items-center gap-3 py-2 text-sm transition-colors',
                    collapsed ? 'px-4 justify-center' : 'px-6',
                    active ? 'bg-primary/20 text-white border-r-2 border-primary' : 'text-white/60 hover:bg-sidebar-hover hover:text-white',
                  )}
                >
                  {!collapsed && model.name}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-white/10 p-3">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 text-sm text-white/60 hover:text-white hover:bg-sidebar-hover rounded-lg"
        >
          <LogOut size={18} />
          {!collapsed && 'Çıxış'}
        </button>
      </div>
    </aside>
  )
}

export function Header() {
  const { user } = useAuth()
  return (
    <header className="h-14 bg-surface border-b border-border flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-3">
        {user?.restaurant && (
          <span className="text-xs text-text-muted bg-background px-2.5 py-1 rounded-full">
            {user.restaurant.name}
          </span>
        )}
        <span className="text-sm font-medium">{user?.full_name || user?.username}</span>
      </div>
    </header>
  )
}

export function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  return (
    <div className="min-h-full flex">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className={cn('flex-1 flex flex-col transition-all duration-200', collapsed ? 'ml-16' : 'ml-64')}>
        <Header />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
