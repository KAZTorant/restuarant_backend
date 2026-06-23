import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { adminApi } from '../api/admin'
import { Play, Square, RefreshCw, Printer, BarChart3 } from 'lucide-react'
import { DataTable } from '../components/admin/DataTable'
import { Layout } from '../components/layout/Layout'
import { Alert, Button, Card, Input, Label, Modal, Spinner } from '../components/ui'

interface ShiftInfo {
  shift_id: number
  cash_total: string
  card_total: string
  other_total: string
  total: string
  cash_in_hand: string
}

export function StatisticsPage() {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [startModal, setStartModal] = useState(false)
  const [endModal, setEndModal] = useState(false)
  const [initialCash, setInitialCash] = useState('0')
  const [initialCard, setInitialCard] = useState('0')
  const [initialOther, setInitialOther] = useState('0')
  const [withdrawnAmount, setWithdrawnAmount] = useState('0')
  const [withdrawnNotes, setWithdrawnNotes] = useState('')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const { data: meta } = useQuery({
    queryKey: ['meta', 'orders', 'statistics'],
    queryFn: () => adminApi.modelMeta('orders', 'statistics'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['list', 'orders', 'statistics', page, search],
    queryFn: () => adminApi.list('orders', 'statistics', {
      page: String(page),
      ...(search ? { q: search } : {}),
    }),
  })

  const { data: activeOrders } = useQuery({
    queryKey: ['statistics', 'active-orders'],
    queryFn: () => adminApi.statistics.get('active-orders') as Promise<{ total_paid: string; total_unpaid: string }>,
    refetchInterval: 30000,
  })

  const { data: shiftInfo, refetch: refetchShift } = useQuery({
    queryKey: ['statistics', 'current-shift'],
    queryFn: () => adminApi.statistics.get('current-shift-info').catch(() => null) as Promise<ShiftInfo | null>,
    retry: false,
  })

  const runAction = async (action: string, data: Record<string, unknown> = {}) => {
    setError('')
    try {
      const result = await adminApi.statistics.post(action, data) as { detail: string }
      setMessage(result.detail)
      queryClient.invalidateQueries({ queryKey: ['list', 'orders', 'statistics'] })
      refetchShift()
    } catch (err: unknown) {
      setError((err as Error).message)
    }
  }

  const openStartModal = async () => {
    try {
      const info = await adminApi.statistics.get('start-shift-info') as {
        initial_cash: string; initial_card: string; initial_other: string
      }
      setInitialCash(info.initial_cash)
      setInitialCard(info.initial_card)
      setInitialOther(info.initial_other)
    } catch { /* use defaults */ }
    setStartModal(true)
  }

  if (!meta) {
    return (
      <Layout>
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-xl font-bold">Statistika / Növbə İdarəetməsi</h1>
          <div className="flex gap-2 flex-wrap">
            {!shiftInfo ? (
              <Button onClick={openStartModal}><Play size={16} /> Növbəni Başlat</Button>
            ) : (
              <Button variant="danger" onClick={() => setEndModal(true)}>
                <Square size={16} /> Növbəni Bağla
              </Button>
            )}
            <Button variant="secondary" onClick={() => runAction('calculate-till-now')}>
              <RefreshCw size={16} /> Yenilə
            </Button>
          </div>
        </div>

        {message && <Alert type="success">{message}</Alert>}
        {error && <Alert type="error">{error}</Alert>}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <p className="text-xs text-text-muted">Ödənilmiş sifarişlər</p>
            <p className="text-xl font-bold text-success">{activeOrders?.total_paid ?? '—'} AZN</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-text-muted">Ödənilməmiş sifarişlər</p>
            <p className="text-xl font-bold text-warning">{activeOrders?.total_unpaid ?? '—'} AZN</p>
          </Card>
          {shiftInfo && (
            <>
              <Card className="p-4">
                <p className="text-xs text-text-muted">Nağd (növbə)</p>
                <p className="text-xl font-bold">{shiftInfo.cash_total} AZN</p>
              </Card>
              <Card className="p-4">
                <p className="text-xs text-text-muted">Cəmi (növbə)</p>
                <p className="text-xl font-bold">{shiftInfo.total} AZN</p>
              </Card>
            </>
          )}
        </div>

        <Card className="p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <BarChart3 size={16} /> Hesablama
          </h3>
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" variant="secondary" onClick={() => runAction('calculate-daily')}>Günlük</Button>
            <Button size="sm" variant="secondary" onClick={() => runAction('calculate-monthly')}>Aylıq</Button>
            <Button size="sm" variant="secondary" onClick={() => runAction('calculate-yearly')}>İllik</Button>
            <Button size="sm" variant="secondary" onClick={() => runAction('calculate-per-waitress')}>Ofisiant</Button>
          </div>
        </Card>

        <DataTable
          meta={meta}
          data={data}
          loading={isLoading}
          page={page}
          search={search}
          onPageChange={setPage}
          onSearchChange={setSearch}
          selectedIds={selectedIds}
          onSelectIds={setSelectedIds}
        />

        <Modal open={startModal} onClose={() => setStartModal(false)} title="Növbəni Başlat">
          <div className="space-y-4">
            <div>
              <Label>Başlanğıc nağd</Label>
              <Input value={initialCash} onChange={(e) => setInitialCash(e.target.value)} type="number" step="0.01" />
            </div>
            <div>
              <Label>Başlanğıc kart</Label>
              <Input value={initialCard} onChange={(e) => setInitialCard(e.target.value)} type="number" step="0.01" />
            </div>
            <div>
              <Label>Başlanğıc digər</Label>
              <Input value={initialOther} onChange={(e) => setInitialOther(e.target.value)} type="number" step="0.01" />
            </div>
            <Button onClick={async () => {
              await runAction('start-shift', {
                initial_cash: initialCash,
                initial_card: initialCard,
                initial_other: initialOther,
              })
              setStartModal(false)
            }}>Başlat</Button>
          </div>
        </Modal>

        <Modal open={endModal} onClose={() => setEndModal(false)} title="Növbəni Bağla">
          <div className="space-y-4">
            {shiftInfo && (
              <Alert type="info">
                Nağd cəmi: {shiftInfo.cash_in_hand} AZN · Kart: {shiftInfo.card_total} AZN
              </Alert>
            )}
            <div>
              <Label>Götürülən məbləğ</Label>
              <Input value={withdrawnAmount} onChange={(e) => setWithdrawnAmount(e.target.value)} type="number" step="0.01" />
            </div>
            <div>
              <Label>Qeydlər</Label>
              <Input value={withdrawnNotes} onChange={(e) => setWithdrawnNotes(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button variant="danger" onClick={async () => {
                await runAction('end-shift', {
                  shift_id: shiftInfo?.shift_id,
                  withdrawn_amount: withdrawnAmount,
                  withdrawn_notes: withdrawnNotes,
                })
                setEndModal(false)
              }}>Növbəni Bağla</Button>
              {shiftInfo && (
                <>
                  <Button variant="secondary" onClick={() => runAction('print-shift-summary', { shift_id: shiftInfo.shift_id })}>
                    <Printer size={16} /> Çap
                  </Button>
                </>
              )}
            </div>
          </div>
        </Modal>
      </div>
    </Layout>
  )
}

export function SummaryPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [createModal, setCreateModal] = useState(false)
  const [previewModal, setPreviewModal] = useState(false)
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [message, setMessage] = useState('')

  const { data: meta } = useQuery({
    queryKey: ['meta', 'orders', 'summary'],
    queryFn: () => adminApi.modelMeta('orders', 'summary'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['list', 'orders', 'summary', page, search],
    queryFn: () => adminApi.list('orders', 'summary', { page: String(page) }),
  })

  const handleCreate = async () => {
    const result = await adminApi.summary.create(startDate, endDate) as { id: number; detail: string }
    setMessage(result.detail)
    setCreateModal(false)
    queryClient.invalidateQueries({ queryKey: ['list', 'orders', 'summary'] })
  }

  const handlePreview = async (id: number) => {
    const data = await adminApi.summary.preview(id)
    setPreviewData(data as Record<string, unknown>)
    setPreviewModal(true)
  }

  if (!meta) return <Layout><Spinner size="lg" /></Layout>

  return (
    <Layout>
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">Hesabatlar (Summary)</h1>
          <Button onClick={() => setCreateModal(true)}>Tarix Aralığı Hesabatı Yarat</Button>
        </div>
        {message && <Alert type="success">{message}</Alert>}

        <DataTable
          meta={meta}
          data={data}
          loading={isLoading}
          page={page}
          search={search}
          onPageChange={setPage}
          onSearchChange={setSearch}
          selectedIds={selectedIds}
          onSelectIds={setSelectedIds}
        />

        {data?.results.map((row) => (
          <button
            key={row.id as number}
            onClick={() => handlePreview(row.id as number)}
            className="hidden"
          />
        ))}

        <Modal open={createModal} onClose={() => setCreateModal(false)} title="Tarix Aralığı Hesabatı">
          <div className="space-y-4">
            <div><Label>Başlanğıc</Label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
            <div><Label>Bitiş</Label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
            <Button onClick={handleCreate}>Yarat</Button>
          </div>
        </Modal>

        <Modal open={previewModal} onClose={() => setPreviewModal(false)} title="Hesabat Önizləmə" wide>
          {previewData && (
            <div className="space-y-3">
              <p><strong>{String(previewData.title)}</strong></p>
              <p>Tarix: {String(previewData.date_range)}</p>
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-3"><p className="text-xs text-text-muted">Cəmi</p><p className="font-bold">{String(previewData.total)} AZN</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Nağd</p><p className="font-bold">{String(previewData.cash_total)} AZN</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Kart</p><p className="font-bold">{String(previewData.card_total)} AZN</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Digər</p><p className="font-bold">{String(previewData.other_total)} AZN</p></Card>
              </div>
              <Link to={`/models/orders/summary/${previewData.id}/change`}>
                <Button variant="secondary" size="sm">Tam bax</Button>
              </Link>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  )
}

export function PaymentCalculationPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [calcModal, setCalcModal] = useState(false)
  const [form, setForm] = useState({
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date().toISOString().slice(0, 10),
    start_time: '12:00',
    end_time: '23:59',
  })
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const { data: meta } = useQuery({
    queryKey: ['meta', 'payments', 'paymentcalculation'],
    queryFn: () => adminApi.modelMeta('payments', 'paymentcalculation'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['list', 'payments', 'paymentcalculation', page],
    queryFn: () => adminApi.list('payments', 'paymentcalculation', { page: String(page) }),
  })

  const handleCalculate = async () => {
    const res = await adminApi.paymentCalculation.calculate(form)
    setResult(res as Record<string, unknown>)
    queryClient.invalidateQueries({ queryKey: ['list', 'payments', 'paymentcalculation'] })
  }

  if (!meta) return <Layout><Spinner size="lg" /></Layout>

  return (
    <Layout>
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">Ödəniş Hesablaması</h1>
          <Button onClick={() => setCalcModal(true)}>Yeni Hesablama</Button>
        </div>

        <DataTable
          meta={meta}
          data={data}
          loading={isLoading}
          page={page}
          search={search}
          onPageChange={setPage}
          onSearchChange={setSearch}
          selectedIds={selectedIds}
          onSelectIds={setSelectedIds}
        />

        <Modal open={calcModal} onClose={() => { setCalcModal(false); setResult(null) }} title="Ödəniş Hesablaması" wide>
          {!result ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><Label>Başlanğıc tarixi</Label><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
                <div><Label>Bitiş tarixi</Label><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
                <div><Label>Başlanğıc saatı</Label><Input value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} placeholder="12:00" /></div>
                <div><Label>Bitiş saatı</Label><Input value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} placeholder="23:59" /></div>
              </div>
              <Button onClick={handleCalculate}>Hesabla</Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert type="success">{String(result.detail)}</Alert>
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-3"><p className="text-xs text-text-muted">Cəmi</p><p className="font-bold text-lg">{String(result.total_amount)} AZN</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Ödəniş sayı</p><p className="font-bold text-lg">{String(result.payment_count)}</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Nağd</p><p className="font-bold">{String(result.cash_amount)} AZN</p></Card>
                <Card className="p-3"><p className="text-xs text-text-muted">Kart</p><p className="font-bold">{String(result.card_amount)} AZN</p></Card>
              </div>
              <Link to={`/models/payments/paymentcalculation/${result.id}/change`}>
                <Button>Detallı bax</Button>
              </Link>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  )
}

export function WithdrawnListPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [total, setTotal] = useState<string | null>(null)

  const { data: meta } = useQuery({
    queryKey: ['meta', 'orders', 'withdrawnlist'],
    queryFn: () => adminApi.modelMeta('orders', 'withdrawnlist'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['list', 'orders', 'withdrawnlist', page],
    queryFn: () => adminApi.list('orders', 'withdrawnlist', { page: String(page) }),
  })

  const calculate = async () => {
    const res = await adminApi.withdrawnList.calculateTotal(startDate, endDate) as { total_withdrawn: string; count: number }
    setTotal(`${res.total_withdrawn} AZN (${res.count} qeyd)`)
  }

  if (!meta) return <Layout><Spinner size="lg" /></Layout>

  return (
    <Layout>
      <div className="space-y-4 animate-fade-in">
        <h1 className="text-xl font-bold">Götürülən Məbləğlər</h1>

        <Card className="p-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div><Label>Başlanğıc</Label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
            <div><Label>Bitiş</Label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
            <Button onClick={calculate}>Hesabla</Button>
            {total && <span className="text-sm font-semibold text-success">{total}</span>}
          </div>
        </Card>

        <DataTable
          meta={meta}
          data={data}
          loading={isLoading}
          page={page}
          search={search}
          onPageChange={setPage}
          onSearchChange={setSearch}
          selectedIds={selectedIds}
          onSelectIds={setSelectedIds}
        />
      </div>
    </Layout>
  )
}

export function TablesPage() {
  const { data: meta, isLoading: metaLoading } = useQuery({
    queryKey: ['meta', 'tables', 'table'],
    queryFn: () => adminApi.modelMeta('tables', 'table'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['list', 'tables', 'table'],
    queryFn: () => adminApi.list('tables', 'table', { page: '1', page_size: '200' }),
  })

  if (metaLoading || !meta) return <Layout><Spinner size="lg" /></Layout>

  const grouped: Record<string, Record<string, unknown>[]> = {}
  for (const row of data?.results ?? []) {
    const room = String(row.room ?? 'Digər')
    if (!grouped[room]) grouped[room] = []
    grouped[room].push(row)
  }

  return (
    <Layout>
      <div className="space-y-4 animate-fade-in">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">Masalar</h1>
          <Link to="/models/tables/table/add">
            <Button size="sm">Masa əlavə et</Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(grouped).map(([room, tables]) => (
            <Card key={room} className="p-4">
              <h3 className="font-semibold mb-3 text-sm text-text-muted uppercase">{room}</h3>
              <div className="grid grid-cols-3 gap-2">
                {tables.map((t) => (
                  <Link
                    key={t.id as number}
                    to={`/models/tables/table/${t.id}/change`}
                    className="border border-border rounded-lg p-3 text-center hover:border-primary hover:bg-primary/5 transition-colors"
                  >
                    <p className="font-bold text-lg">{String(t.name ?? t.id)}</p>
                    {t.is_active !== undefined && (
                      <span className={`text-xs ${t.is_active ? 'text-success' : 'text-text-muted'}`}>
                        {t.is_active ? 'Aktiv' : 'Deaktiv'}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            </Card>
          ))}
        </div>

        {Object.keys(grouped).length === 0 && !isLoading && (
          <p className="text-text-muted text-center py-8">Masa tapılmadı</p>
        )}
      </div>
    </Layout>
  )
}
