import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../api/admin'
import { DynamicForm } from '../components/admin/DynamicForm'
import { DataTable } from '../components/admin/DataTable'
import { Layout } from '../components/layout/Layout'
import { Alert, Spinner } from '../components/ui'
import type { FormSchema } from '../types/admin'

export function ModelListPage() {
  const { app, model } = useParams<{ app: string; model: string }>()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [message, setMessage] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ['meta', app, model],
    queryFn: () => adminApi.modelMeta(app!, model!),
    enabled: !!app && !!model,
  })

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['list', app, model, page, debouncedSearch],
    queryFn: () => adminApi.list(app!, model!, {
      page: String(page),
      ...(debouncedSearch ? { q: debouncedSearch } : {}),
    }),
    enabled: !!app && !!model,
    placeholderData: (prev) => prev,
  })

  const handleDelete = useCallback(async (id: number) => {
    if (!confirm('Silmək istədiyinizə əminsiniz?')) return
    await adminApi.delete(app!, model!, id)
    queryClient.invalidateQueries({ queryKey: ['list', app, model] })
    setMessage('Qeyd silindi')
  }, [app, model, queryClient])

  const handleAction = useCallback(async (actionName: string) => {
    await adminApi.action(app!, model!, actionName, selectedIds)
    queryClient.invalidateQueries({ queryKey: ['list', app, model] })
    setSelectedIds([])
    setMessage('Əməliyyat tamamlandı')
  }, [app, model, selectedIds, queryClient])

  if (metaLoading) {
    return (
      <Layout>
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </Layout>
    )
  }

  if (!meta) return null

  return (
    <Layout>
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold">{meta.verbose_name_plural}</h1>
          {isFetching && !isLoading && (
            <span className="text-xs text-text-muted">Yenilənir...</span>
          )}
        </div>

        {message && (
          <Alert type="success">
            {message}
            <button onClick={() => setMessage('')} className="ml-2 underline text-xs">Bağla</button>
          </Alert>
        )}

        <DataTable
          meta={meta}
          data={data}
          loading={isLoading}
          page={page}
          search={search}
          onPageChange={setPage}
          onSearchChange={(s) => { setSearch(s); setPage(1) }}
          selectedIds={selectedIds}
          onSelectIds={setSelectedIds}
          onAction={handleAction}
          onDelete={meta.permissions.delete ? handleDelete : undefined}
          addUrl={meta.permissions.add ? `/models/${app}/${model}/add` : undefined}
        />
      </div>
    </Layout>
  )
}

export function ModelFormPage() {
  const { app, model, pk } = useParams<{ app: string; model: string; pk?: string }>()
  const navigate = useNavigate()
  const isAdd = !pk || pk === 'add'
  const [error, setError] = useState('')

  const { data: detail, isLoading } = useQuery({
    queryKey: ['detail', app, model, pk],
    queryFn: () => adminApi.detail(app!, model!, Number(pk)),
    enabled: !isAdd && !!pk,
  })

  const { data: createData, isLoading: createLoading } = useQuery({
    queryKey: ['create-schema', app, model],
    queryFn: () => adminApi.createSchema(app!, model!),
    enabled: isAdd,
  })

  const schema = isAdd ? createData?.schema : detail?.schema
  const initialData = isAdd ? {} : detail?.object

  const handleSubmit = async (data: Record<string, unknown>) => {
    setError('')
    try {
      if (isAdd) {
        const result = await adminApi.create(app!, model!, data) as { id: number }
        navigate(`/models/${app}/${model}/${result.id}/change`)
      } else {
        await adminApi.update(app!, model!, Number(pk), data)
        navigate(`/models/${app}/${model}`)
      }
    } catch (err: unknown) {
      const e = err as { message?: string; data?: { errors?: Record<string, string[]> } }
      if (e.data?.errors) throw err
      setError(e.message || 'Xəta baş verdi')
    }
  }

  if (isLoading || createLoading) {
    return (
      <Layout>
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </Layout>
    )
  }

  if (!schema) return null

  return (
    <Layout>
      <div className="max-w-4xl animate-fade-in space-y-4">
        <h1 className="text-xl font-bold">
          {isAdd ? 'Yeni qeyd' : 'Düzəliş et'}
        </h1>
        {error && <Alert type="error">{error}</Alert>}
        <DynamicFormWrapper
          schema={schema}
          initialData={initialData}
          onSubmit={handleSubmit}
          submitLabel={isAdd ? 'Yarat' : 'Saxla'}
        />
      </div>
    </Layout>
  )
}

function DynamicFormWrapper(props: {
  schema: FormSchema
  initialData?: Record<string, unknown>
  onSubmit: (data: Record<string, unknown>) => Promise<void>
  submitLabel?: string
}) {
  return <DynamicForm {...props} />
}
