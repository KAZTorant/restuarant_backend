import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Alert, Button, Card, Input, Label, Spinner } from '../components/ui'

export function LoginPage() {
  const { user, loading, login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
    } catch (err: unknown) {
      setError((err as Error).message || 'Giriş uğursuz oldu')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center bg-gradient-to-br from-sidebar to-primary/80 p-4">
      <Card className="w-full max-w-md p-8 animate-fade-in">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-text">KAZZA Admin</h1>
          <p className="text-text-muted mt-1">İdarə panelinə daxil olun</p>
        </div>

        {error && <Alert type="error" ><span className="block mb-4">{error}</span></Alert>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label required>İstifadəçi adı</Label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <Label required>Şifrə</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? <Spinner size="sm" /> : 'Daxil ol'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
