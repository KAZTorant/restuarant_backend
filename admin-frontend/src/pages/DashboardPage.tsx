import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Card } from '../components/ui'
import { Layout } from '../components/layout/Layout'
import {
  BarChart3, CreditCard, Receipt, Settings, Table2, Users, UtensilsCrossed,
} from 'lucide-react'

const QUICK_LINKS = [
  { to: '/statistics', label: 'Statistika / Növbə', icon: BarChart3, color: 'bg-blue-500' },
  { to: '/models/orders/order', label: 'Sifarişlər', icon: Receipt, color: 'bg-green-500' },
  { to: '/models/payments/payment', label: 'Ödənişlər', icon: CreditCard, color: 'bg-purple-500' },
  { to: '/models/meals/meal', label: 'Yeməklər', icon: UtensilsCrossed, color: 'bg-orange-500' },
  { to: '/tables', label: 'Masalar', icon: Table2, color: 'bg-teal-500' },
  { to: '/models/users/user', label: 'İstifadəçilər', icon: Users, color: 'bg-indigo-500' },
  { to: '/payment-calculation', label: 'Ödəniş Hesablaması', icon: CreditCard, color: 'bg-pink-500' },
  { to: '/summary', label: 'Hesabatlar', icon: BarChart3, color: 'bg-cyan-500' },
]

export function DashboardPage() {
  const { navigation, user } = useAuth()

  return (
    <Layout>
      <div className="animate-fade-in space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Xoş gəldiniz{user?.full_name ? `, ${user.full_name}` : ''}!</h1>
          <p className="text-text-muted mt-1">KAZZA restoran idarəetmə paneli</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {QUICK_LINKS.map((link) => (
            <Link key={link.to} to={link.to}>
              <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer group">
                <div className={`w-10 h-10 rounded-lg ${link.color} flex items-center justify-center mb-3 group-hover:scale-105 transition-transform`}>
                  <link.icon size={20} className="text-white" />
                </div>
                <p className="text-sm font-medium">{link.label}</p>
              </Card>
            </Link>
          ))}
        </div>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings size={18} /> Modullar
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {navigation?.apps.map((app) => (
              <div key={app.app_label} className="border border-border rounded-lg p-4">
                <h3 className="font-medium text-sm text-text-muted uppercase tracking-wide mb-2">
                  {app.name}
                </h3>
                <ul className="space-y-1">
                  {app.models.map((model) => (
                    <li key={model.model_name}>
                      <Link
                        to={`/models/${model.app_label}/${model.model_name}`}
                        className="text-sm text-primary hover:underline"
                      >
                        {model.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Layout>
  )
}
