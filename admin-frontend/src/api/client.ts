const API_BASE = import.meta.env.DEV ? '/admin-api' : '/admin-api'

class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, message: string, data?: unknown) {
    super(message)
    this.status = status
    this.data = data
  }
}

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const csrf = getCsrfToken()
  if (csrf && options.method && options.method !== 'GET') {
    headers['X-CSRFToken'] = csrf
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const msg = (data as { detail?: string }).detail || `HTTP ${res.status}`
    throw new ApiError(res.status, msg, data)
  }

  return data as T
}

export { ApiError, request }
