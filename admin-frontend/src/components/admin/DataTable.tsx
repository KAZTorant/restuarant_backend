import { useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table'
import { ChevronLeft, ChevronRight, Plus, Search, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ListResponse, ModelMeta } from '../../types/admin'
import { Button, Input, Spinner } from '../ui'

interface DataTableProps {
  meta: ModelMeta
  data: ListResponse | undefined
  loading: boolean
  page: number
  search: string
  onPageChange: (p: number) => void
  onSearchChange: (s: string) => void
  selectedIds: number[]
  onSelectIds: (ids: number[]) => void
  onAction?: (action: string) => void
  onDelete?: (id: number) => void
  addUrl?: string
}

export function DataTable({
  meta,
  data,
  loading,
  page,
  search,
  onPageChange,
  onSearchChange,
  selectedIds,
  onSelectIds,
  onAction,
  onDelete,
  addUrl,
}: DataTableProps) {
  const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
    const cols: ColumnDef<Record<string, unknown>>[] = [
      {
        id: 'select',
        header: ({ table }) => (
          <input
            type="checkbox"
            checked={table.getIsAllRowsSelected()}
            onChange={table.getToggleAllRowsSelectedHandler()}
            className="rounded"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            className="rounded"
          />
        ),
        size: 40,
      },
    ]

    for (const col of meta.list.columns) {
      cols.push({
        accessorKey: col.name,
        header: col.label,
        cell: ({ getValue }) => {
          const val = getValue()
          if (val === true) return '✓'
          if (val === false) return '—'
          if (val === null || val === undefined) return '—'
          return String(val)
        },
      })
    }

    if (meta.permissions.change || meta.permissions.delete) {
      cols.push({
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <div className="flex gap-1 justify-end">
            {meta.permissions.change && (
              <Link
                to={`/models/${meta.app_label}/${meta.model_name}/${row.original.id}/change`}
                className="text-primary text-xs hover:underline px-2 py-1"
              >
                Düzəliş
              </Link>
            )}
            {meta.permissions.delete && onDelete && (
              <button
                onClick={() => onDelete(row.original.id as number)}
                className="text-danger text-xs hover:underline px-2 py-1"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        ),
        size: 100,
      })
    }

    return cols
  }, [meta, onDelete])

  const table = useReactTable({
    data: data?.results ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => String(row.id),
    state: {
      rowSelection: Object.fromEntries(selectedIds.map((id) => [String(id), true])),
    },
    onRowSelectionChange: (updater) => {
      const current = Object.fromEntries(selectedIds.map((id) => [String(id), true]))
      const next = typeof updater === 'function' ? updater(current) : updater
      onSelectIds(Object.keys(next).filter((k) => next[k]).map(Number))
    },
    enableRowSelection: true,
  })

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Axtar..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {meta.list.actions.map((action) => (
            <Button
              key={action.name}
              variant="secondary"
              size="sm"
              disabled={selectedIds.length === 0}
              onClick={() => onAction?.(action.name)}
            >
              {action.label}
            </Button>
          ))}
          {meta.permissions.add && addUrl && (
            <Link to={addUrl}>
              <Button size="sm"><Plus size={16} /> Əlavə et</Button>
            </Link>
          )}
        </div>
      </div>

      <div className="bg-surface rounded-xl border border-border overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id} className="bg-background border-b border-border">
                    {hg.headers.map((header) => (
                      <th key={header.id} className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-4 py-12 text-center text-text-muted">
                      Məlumat tapılmadı
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-b border-border hover:bg-background/50 transition-colors">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-2.5 whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {data && data.num_pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-background/50">
            <span className="text-sm text-text-muted">
              Cəmi {data.count} qeyd · Səhifə {data.page}/{data.num_pages}
            </span>
            <div className="flex gap-1">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
              >
                <ChevronLeft size={16} />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= data.num_pages}
                onClick={() => onPageChange(page + 1)}
              >
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
