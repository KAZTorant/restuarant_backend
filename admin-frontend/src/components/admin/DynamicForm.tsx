import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../../api/admin'
import type { FieldSchema, FormSchema } from '../../types/admin'
import { Button, Input, Label, Select, Spinner, Textarea } from '../ui'

interface DynamicFormProps {
  schema: FormSchema
  initialData?: Record<string, unknown>
  onSubmit: (data: Record<string, unknown>) => Promise<void>
  submitLabel?: string
  loading?: boolean
}

function ForeignKeySelect({
  field,
  value,
  onChange,
}: {
  field: FieldSchema
  value: unknown
  onChange: (val: unknown) => void
}) {
  const [options, setOptions] = useState<{ id: number; label: string }[]>([])
  const [search, setSearch] = useState('')
  const related = field.related_model

  const load = useCallback(async (q: string) => {
    if (!related) return
    const res = await adminApi.choices(related.app_label, related.model_name, q)
    setOptions(res.results)
  }, [related])

  useEffect(() => { load('') }, [load])

  const currentId = typeof value === 'object' && value !== null
    ? (value as { id: number }).id
    : value

  return (
    <div className="space-y-1">
      <Select
        value={currentId ? String(currentId) : ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">— Seçin —</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </Select>
      <Input
        placeholder="Axtar..."
        value={search}
        onChange={(e) => { setSearch(e.target.value); load(e.target.value) }}
        className="text-xs"
      />
    </div>
  )
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldSchema
  value: unknown
  onChange: (val: unknown) => void
}) {
  if (field.type === 'readonly' || field.type === 'computed') {
    return <div className="text-sm text-text-muted py-2">{String(value ?? '—')}</div>
  }

  if (field.type === 'foreign_key') {
    return <ForeignKeySelect field={field} value={value} onChange={onChange} />
  }

  if (field.type === 'boolean') {
    return (
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(e) => onChange(e.target.checked)}
        className="rounded w-4 h-4"
      />
    )
  }

  if (field.choices.length > 0) {
    return (
      <Select value={String(value ?? '')} onChange={(e) => onChange(e.target.value)}>
        <option value="">— Seçin —</option>
        {field.choices.map((c) => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </Select>
    )
  }

  if (field.type === 'text' || field.widget === 'textarea') {
    return (
      <Textarea
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  if (field.type === 'datetime') {
    const v = value ? String(value).slice(0, 16) : ''
    return (
      <Input
        type="datetime-local"
        value={v}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  if (field.type === 'date') {
    return (
      <Input
        type="date"
        value={String(value ?? '').slice(0, 10)}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  if (field.type === 'password') {
    return (
      <Input
        type="password"
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  if (field.type === 'decimal' || field.type === 'integer') {
    return (
      <Input
        type="number"
        step={field.type === 'decimal' ? '0.01' : '1'}
        value={value !== null && value !== undefined ? String(value) : ''}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  return (
    <Input
      value={String(value ?? '')}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

export function DynamicForm({
  schema,
  initialData = {},
  onSubmit,
  submitLabel = 'Saxla',
  loading,
}: DynamicFormProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>(initialData)
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setFormData(initialData)
  }, [initialData])

  const setField = (name: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setErrors({})
    try {
      await onSubmit(formData)
    } catch (err: unknown) {
      const apiErr = err as { data?: { errors?: Record<string, string[]> } }
      if (apiErr.data?.errors) setErrors(apiErr.data.errors)
    } finally {
      setSubmitting(false)
    }
  }

  const renderFields = (fieldNames: string[]) =>
    fieldNames.map((name) => {
      const field = schema.fields.find((f) => f.name === name)
      if (!field) return null
      return (
        <div key={name} className="space-y-1">
          <Label required={field.required}>{field.label}</Label>
          <FieldInput
            field={field}
            value={formData[name]}
            onChange={(v) => setField(name, v)}
          />
          {field.help_text && (
            <p className="text-xs text-text-muted">{field.help_text}</p>
          )}
          {errors[name] && (
            <p className="text-xs text-danger">{errors[name].join(', ')}</p>
          )}
        </div>
      )
    })

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {schema.fieldsets.length > 0 ? (
        schema.fieldsets.map((fs, i) => (
          <fieldset key={i} className="bg-surface rounded-xl border border-border p-5 space-y-4">
            {fs.title && (
              <legend className="text-sm font-semibold text-text px-1">{fs.title}</legend>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderFields(fs.fields)}
            </div>
          </fieldset>
        ))
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {renderFields(schema.fields.map((f) => f.name))}
        </div>
      )}

      <div className="flex gap-3">
        <Button type="submit" disabled={submitting || loading}>
          {submitting ? <Spinner size="sm" /> : submitLabel}
        </Button>
      </div>
    </form>
  )
}
