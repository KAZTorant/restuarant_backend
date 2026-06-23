import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { ModelListPage, ModelFormPage } from './pages/ModelPages'
import {
  StatisticsPage,
  SummaryPage,
  PaymentCalculationPage,
  WithdrawnListPage,
  TablesPage,
} from './pages/CustomPages'
import { Spinner } from './components/ui'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter basename="/panel">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />

            {/* Custom workflow pages */}
            <Route path="/statistics" element={<ProtectedRoute><StatisticsPage /></ProtectedRoute>} />
            <Route path="/summary" element={<ProtectedRoute><SummaryPage /></ProtectedRoute>} />
            <Route path="/payment-calculation" element={<ProtectedRoute><PaymentCalculationPage /></ProtectedRoute>} />
            <Route path="/withdrawn-list" element={<ProtectedRoute><WithdrawnListPage /></ProtectedRoute>} />
            <Route path="/tables" element={<ProtectedRoute><TablesPage /></ProtectedRoute>} />

            {/* Generic model CRUD */}
            <Route path="/models/:app/:model" element={<ProtectedRoute><ModelListPage /></ProtectedRoute>} />
            <Route path="/models/:app/:model/add" element={<ProtectedRoute><ModelFormPage /></ProtectedRoute>} />
            <Route path="/models/:app/:model/:pk/change" element={<ProtectedRoute><ModelFormPage /></ProtectedRoute>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
