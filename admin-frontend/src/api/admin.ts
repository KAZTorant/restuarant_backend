import { request } from './client'
import type {
  AdminUser,
  DetailResponse,
  FormSchema,
  ListResponse,
  ModelMeta,
  Navigation,
} from '../types/admin'

export const adminApi = {
  login: (username: string, password: string) =>
    request<AdminUser>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () => request('/auth/logout/', { method: 'POST' }),

  me: () => request<AdminUser>('/auth/me/'),

  navigation: () => request<Navigation>('/navigation/'),

  modelMeta: (app: string, model: string) =>
    request<ModelMeta>(`/${app}/${model}/meta/`),

  list: (app: string, model: string, params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request<ListResponse>(`/${app}/${model}/${qs ? `?${qs}` : ''}`)
  },

  detail: (app: string, model: string, pk: number) =>
    request<DetailResponse>(`/${app}/${model}/${pk}/`),

  createSchema: (app: string, model: string) =>
    request<{ schema: FormSchema }>(`/${app}/${model}/create/`),

  create: (app: string, model: string, data: Record<string, unknown>) =>
    request(`/${app}/${model}/create/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (app: string, model: string, pk: number, data: Record<string, unknown>) =>
    request(`/${app}/${model}/${pk}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (app: string, model: string, pk: number) =>
    request(`/${app}/${model}/${pk}/`, { method: 'DELETE' }),

  choices: (app: string, model: string, q = '') => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : ''
    return request<{ results: { id: number; label: string }[] }>(
      `/${app}/${model}/choices/${qs}`,
    )
  },

  action: (app: string, model: string, actionName: string, ids: number[]) =>
    request(`/${app}/${model}/actions/${actionName}/`, {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  // Custom workflows
  statistics: {
    get: (action: string) => request(`/custom/statistics/${action}/`),
    post: (action: string, data: Record<string, unknown> = {}) =>
      request(`/custom/statistics/${action}/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  summary: {
    create: (startDate: string, endDate: string) =>
      request('/custom/summary/create-summary/', {
        method: 'POST',
        body: JSON.stringify({ start_date: startDate, end_date: endDate }),
      }),
    preview: (id: number) =>
      request(`/custom/summary/preview-summary/${id}/`),
  },

  paymentCalculation: {
    calculate: (data: Record<string, string>) =>
      request('/custom/payment-calculation/calculate/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  withdrawnList: {
    calculateTotal: (startDate: string, endDate: string) =>
      request('/custom/withdrawn-list/calculate-total/', {
        method: 'POST',
        body: JSON.stringify({ start_date: startDate, end_date: endDate }),
      }),
  },

  printers: {
    scan: () => request<{ printers: unknown[] }>('/custom/printers/scan/'),
  },

  shiftHandover: {
    confirm: (id: number) =>
      request(`/custom/shift-handover/${id}/confirm/`, { method: 'POST' }),
  },
}
