import { useCallback, useEffect, useRef, useState } from 'react'
import {
  CheckCircle, AlertCircle, Upload, FileSpreadsheet, Trash2,
  Info, TrendingUp, Users, ShoppingCart, AlertTriangle, X,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

// ─── Types ─────────────────────────────────────────────────────────────────────

type DataType = 'financial' | 'pos' | 'customer'

interface UploadStatus {
  uploaded: boolean
  info: any
  summary?: any
}

// ─── Config per dataset ────────────────────────────────────────────────────────

const DATASET_CONFIG = {
  financial: {
    label: 'Financial Data',
    icon: TrendingUp,
    color: 'emerald',
    accent: 'border-emerald-400',
    badge: 'bg-emerald-100 text-emerald-700',
    btnPrimary: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    btnOutline: 'border-emerald-300 text-emerald-700 hover:bg-emerald-50',
    dragActive: 'border-emerald-400 bg-emerald-50',
    iconBg: 'bg-emerald-50 text-emerald-600',
    tabActive: 'border-emerald-500 text-emerald-700 bg-emerald-50',
    statusCard: 'border-emerald-200 bg-emerald-50',
    ai_usecases: [
      'P&L Forecasting', 'Cost Trend Analysis', 'Margin Optimisation',
      'Labor Cost Alerts', 'Budget vs Actual', 'Break-even Analysis',
      'Expense Anomaly Detection', 'ROI on Marketing Spend',
    ],
    required_fields: [
      { name: 'Date', required: true },
      { name: 'Daily Revenue', required: true },
      { name: 'Gross Margin %', required: true },
      { name: 'Net Profit', required: false },
      { name: 'Food Cost %', required: false },
      { name: 'Labor Cost %', required: false },
      { name: 'Electricity', required: false },
      { name: 'Rent', required: false },
      { name: 'Marketing Spend', required: false },
      { name: 'Packaging Cost', required: false },
      { name: 'Platform Commission', required: false },
    ],
    preview_cols: ['date', 'daily_revenue', 'gross_margin_pct', 'net_profit', 'food_cost_pct', 'labor_cost_pct'],
    preview_labels: ['Date', 'Revenue', 'Gross Margin%', 'Net Profit', 'Food Cost%', 'Labor%'],
  },
  pos: {
    label: 'POS Billing Data',
    icon: ShoppingCart,
    color: 'indigo',
    accent: 'border-indigo-400',
    badge: 'bg-indigo-100 text-indigo-700',
    btnPrimary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    btnOutline: 'border-indigo-300 text-indigo-700 hover:bg-indigo-50',
    dragActive: 'border-indigo-400 bg-indigo-50',
    iconBg: 'bg-indigo-50 text-indigo-600',
    tabActive: 'border-indigo-500 text-indigo-700 bg-indigo-50',
    statusCard: 'border-indigo-200 bg-indigo-50',
    ai_usecases: [
      'Menu Performance Analytics', 'Peak Hour Forecasting', 'Platform Revenue Mix',
      'Discount Impact Analysis', 'Cancellation Prediction', 'Item Cross-sell Recommender',
      'GST Reconciliation', 'Dynamic Pricing Engine',
    ],
    required_fields: [
      { name: 'Date', required: true },
      { name: 'Item Name / Product', required: true },
      { name: 'Quantity / Qty', required: true },
      { name: 'Price / Rate', required: false },
      { name: 'Revenue / Total', required: true },
      { name: 'Category / Type', required: false },
      { name: 'Platform / Channel', required: false },
      { name: 'Cost / COGS', required: false },
      { name: 'Order ID / Bill No', required: false },
      { name: 'GST Amount', required: false },
      { name: 'Discount', required: false },
      { name: 'Payment Mode', required: false },
      { name: 'Hour / Time', required: false },
    ],
    preview_cols: ['date', 'item_name', 'category', 'quantity', 'revenue', 'platform'],
    preview_labels: ['Date', 'Item', 'Category', 'Qty', 'Revenue', 'Platform'],
  },
  customer: {
    label: 'Customer Data',
    icon: Users,
    color: 'purple',
    accent: 'border-purple-400',
    badge: 'bg-purple-100 text-purple-700',
    btnPrimary: 'bg-purple-600 hover:bg-purple-700 text-white',
    btnOutline: 'border-purple-300 text-purple-700 hover:bg-purple-50',
    dragActive: 'border-purple-400 bg-purple-50',
    iconBg: 'bg-purple-50 text-purple-600',
    tabActive: 'border-purple-500 text-purple-700 bg-purple-50',
    statusCard: 'border-purple-200 bg-purple-50',
    ai_usecases: [
      'Customer Lifetime Value (CLV)', 'Churn Prediction', 'Birthday & Loyalty Campaigns',
      'Personalised Menu Suggestions', 'Retention Scoring', 'Repeat Visit Prediction',
      'Sentiment Analysis', 'RFM Segmentation',
    ],
    required_fields: [
      { name: 'Customer Name', required: false },
      { name: 'Phone / Contact', required: true },
      { name: 'Birthday / DOB', required: false },
      { name: 'Visit Frequency', required: false },
      { name: 'Favourite Items', required: false },
      { name: 'Avg Order Value', required: false },
      { name: 'Feedback / Rating', required: false },
      { name: 'Preferred Visit Time', required: false },
      { name: 'Platform Source', required: false },
      { name: 'Loyalty Points', required: false },
      { name: 'Gender', required: false },
      { name: 'Age Group', required: false },
    ],
    preview_cols: ['name', 'phone', 'visit_frequency', 'avg_order_value', 'loyalty_points', 'platform_source'],
    preview_labels: ['Name', 'Phone', 'Visit Freq', 'Avg Order', 'Points', 'Platform'],
  },
} as const

// ─── Upload Zone ────────────────────────────────────────────────────────────────

function UploadZone({
  type,
  onUpload,
}: {
  type: DataType
  onUpload: (info: any, summary: any) => void
}) {
  const cfg = DATASET_CONFIG[type]
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const processFile = async (file: File) => {
    if (!file.name.match(/\.(xlsx|xls|csv)$/i)) {
      setError('Only .xlsx, .xls, or .csv files are supported.')
      return
    }
    setError('')
    setUploading(true)
    try {
      const uploadFn = type === 'financial'
        ? api.upload.financial
        : type === 'pos'
        ? api.upload.pos
        : api.upload.customer
      const result: any = await uploadFn(file)
      const summaryFn = type === 'financial'
        ? api.upload.summaryFinancial
        : type === 'pos'
        ? api.upload.summaryPos
        : api.upload.summaryCustomer
      const summary: any = await summaryFn()
      onUpload(result.info, summary)
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }, [type])

  return (
    <div className="space-y-3">
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
          dragging
            ? cfg.dragActive
            : 'border-slate-300 hover:border-slate-400 hover:bg-slate-50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={(e) => { if (e.target.files?.[0]) processFile(e.target.files[0]) }}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3 py-2">
            <div className="w-10 h-10 border-4 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
            <p className="text-sm font-medium text-slate-600">Parsing file…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${cfg.iconBg} mb-1`}>
              <FileSpreadsheet size={28} />
            </div>
            <p className="text-sm font-semibold text-slate-700">
              Drop file here, or <span className="text-blue-500">browse</span>
            </p>
            <p className="text-xs text-slate-400">Supports .xlsx, .xls, .csv</p>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-red-600 text-sm">
          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button className="ml-auto" onClick={() => setError('')}><X size={12} /></button>
        </div>
      )}
    </div>
  )
}

// ─── Uploaded Card ──────────────────────────────────────────────────────────────

function UploadedCard({
  type,
  info,
  summary,
  onReplace,
  onClear,
}: {
  type: DataType
  info: any
  summary: any
  onReplace: (info: any, summary: any) => void
  onClear: () => void
}) {
  const cfg = DATASET_CONFIG[type]
  const inputRef = useRef<HTMLInputElement>(null)
  const [clearing, setClearing] = useState(false)

  const handleClear = async () => {
    setClearing(true)
    try {
      if (type === 'financial') await api.upload.clearFinancial()
      else if (type === 'pos') await api.upload.clearPos()
      else await api.upload.clearCustomer()
      onClear()
    } finally {
      setClearing(false)
    }
  }

  const processFile = async (file: File) => {
    if (!file.name.match(/\.(xlsx|xls|csv)$/i)) return
    const uploadFn = type === 'financial'
      ? api.upload.financial
      : type === 'pos'
      ? api.upload.pos
      : api.upload.customer
    const result: any = await uploadFn(file)
    const summaryFn = type === 'financial'
      ? api.upload.summaryFinancial
      : type === 'pos'
      ? api.upload.summaryPos
      : api.upload.summaryCustomer
    const sum: any = await summaryFn()
    onReplace(result.info, sum)
  }

  return (
    <div className={`rounded-xl border-l-4 ${cfg.accent} bg-white shadow-sm p-5`}>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.iconBg}`}>
            <FileSpreadsheet size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <CheckCircle size={13} className="text-emerald-500" />
              <span className="text-xs font-bold text-emerald-700">Data Loaded</span>
            </div>
            <p className="text-sm font-semibold text-slate-900">{info.filename}</p>
            <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-slate-500">
              <span><strong className="text-slate-700">{info.rows?.toLocaleString?.() ?? info.count?.toLocaleString?.()}</strong> records</span>
              {info.skipped > 0 && <span className="text-yellow-600"><strong>{info.skipped}</strong> skipped</span>}
              {info.date_range?.from && (
                <span><strong className="text-slate-700">{info.date_range.from}</strong> → <strong className="text-slate-700">{info.date_range.to}</strong></span>
              )}
              <span className="text-slate-400">{info.uploaded_at}</span>
            </div>
            {info.columns_detected && Object.keys(info.columns_detected).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {Object.entries(info.columns_detected).map(([field, col]: any) => (
                  <span key={field} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${cfg.badge}`}>
                    <CheckCircle size={9} /> {field}: <strong>{col}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => inputRef.current?.click()}
            className={`text-xs px-3 py-1.5 rounded border flex items-center gap-1.5 transition-colors ${cfg.btnOutline}`}
          >
            <Upload size={11} /> Replace
          </button>
          <button
            onClick={handleClear}
            disabled={clearing}
            className="text-xs px-3 py-1.5 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors flex items-center gap-1.5"
          >
            <Trash2 size={11} /> Clear
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => { if (e.target.files?.[0]) processFile(e.target.files[0]) }}
          />
        </div>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <SummaryStats type={type} summary={summary} />
        </div>
      )}
    </div>
  )
}

// ─── Summary Stats ──────────────────────────────────────────────────────────────
// `summary` is the full API response from /data/{type}/summary
// Shape: { uploaded, info, summary: {...stats}, recent: [...], ... }

function SummaryStats({ type, summary }: { type: DataType; summary: any }) {
  const s = summary?.summary ?? {}
  const info = summary?.info ?? {}

  if (type === 'financial') {
    const rows = (summary?.recent ?? []).slice(0, 5)
    if (!s.total_revenue && !rows.length) return null
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Total Revenue" value={`₹${Number(s.total_revenue ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} />
          <StatChip label="Avg Gross Margin" value={s.avg_gross_margin != null ? `${s.avg_gross_margin}%` : '—'} />
          <StatChip label="Days of Data" value={`${s.days ?? info.unique_dates ?? 0}`} />
        </div>
        {rows.length > 0 && (
          <DataPreviewTable
            rows={rows}
            cols={DATASET_CONFIG.financial.preview_cols}
            labels={DATASET_CONFIG.financial.preview_labels}
            formatters={{
              daily_revenue: (v: any) => v != null ? `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—',
              gross_margin_pct: (v: any) => v != null ? `${Number(v).toFixed(1)}%` : '—',
              net_profit: (v: any) => v != null ? `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—',
              food_cost_pct: (v: any) => v != null ? `${Number(v).toFixed(1)}%` : '—',
              labor_cost_pct: (v: any) => v != null ? `${Number(v).toFixed(1)}%` : '—',
            }}
          />
        )}
      </div>
    )
  }

  if (type === 'pos') {
    const rows = (summary?.recent ?? []).slice(0, 5)
    if (!s.total_revenue && !rows.length) return null
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Total Revenue" value={`₹${Number(s.total_revenue ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} />
          <StatChip label="Total Orders" value={Number(s.total_orders ?? 0).toLocaleString()} />
          <StatChip label="Days of Data" value={`${s.days ?? info.unique_dates ?? 0}`} />
        </div>
        {rows.length > 0 && (
          <DataPreviewTable
            rows={rows}
            cols={DATASET_CONFIG.pos.preview_cols}
            labels={DATASET_CONFIG.pos.preview_labels}
            formatters={{
              revenue: (v: any) => `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
              quantity: (v: any) => Number(v).toFixed(0),
            }}
          />
        )}
      </div>
    )
  }

  if (type === 'customer') {
    const rows = (summary?.recent ?? []).slice(0, 5)
    if (!s.total_customers && !rows.length) return null
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Total Customers" value={Number(s.total_customers ?? 0).toLocaleString()} />
          <StatChip label="Avg Order Value" value={s.avg_order_value != null ? `₹${Number(s.avg_order_value).toFixed(0)}` : '—'} />
          <StatChip label="Avg Visit Freq" value={s.avg_visit_freq != null ? `${s.avg_visit_freq}×` : '—'} />
        </div>
        {rows.length > 0 && (
          <DataPreviewTable
            rows={rows}
            cols={DATASET_CONFIG.customer.preview_cols}
            labels={DATASET_CONFIG.customer.preview_labels}
            formatters={{
              avg_order_value: (v: any) => v != null ? `₹${Number(v).toFixed(0)}` : '—',
              loyalty_points: (v: any) => v != null ? Number(v).toLocaleString() : '—',
            }}
          />
        )}
      </div>
    )
  }

  return null
}

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
      <p className="text-xs text-slate-500 mb-0.5">{label}</p>
      <p className="text-base font-bold text-slate-800">{value}</p>
    </div>
  )
}

function DataPreviewTable({
  rows,
  cols,
  labels,
  formatters = {},
}: {
  rows: any[]
  cols: readonly string[]
  labels: readonly string[]
  formatters?: Record<string, (v: any) => string>
}) {
  if (!rows.length) return null
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-100">
      <table className="w-full text-xs">
        <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
          <tr>
            {labels.map((l) => <th key={l} className="px-3 py-2 text-left font-semibold">{l}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-slate-50">
              {cols.map((col) => (
                <td key={col} className="px-3 py-2 text-slate-700">
                  {formatters[col]
                    ? formatters[col](row[col])
                    : row[col] != null ? String(row[col]) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-3 py-1.5 text-xs text-slate-400 bg-slate-50 border-t border-slate-100">
        Showing first {rows.length} records
      </p>
    </div>
  )
}

// ─── Tab Panel ──────────────────────────────────────────────────────────────────

function DatasetTab({
  type,
  status,
  onStatusChange,
}: {
  type: DataType
  status: UploadStatus
  onStatusChange: (s: UploadStatus) => void
}) {
  const cfg = DATASET_CONFIG[type]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Left col: AI use cases + expected fields */}
      <div className="lg:col-span-2 space-y-5">
        {/* AI Use Cases */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
            AI Use Cases Unlocked
          </p>
          <div className="flex flex-wrap gap-2">
            {cfg.ai_usecases.map((uc) => (
              <span key={uc} className={`px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.badge}`}>
                {uc}
              </span>
            ))}
          </div>
        </div>

        {/* Expected Fields */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Info size={12} />
            Expected Columns
          </p>
          <div className="space-y-1.5">
            {cfg.required_fields.map(({ name, required }) => (
              <div key={name} className="flex items-center gap-2 text-xs">
                <span
                  className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    required ? 'bg-red-400' : 'bg-slate-300'
                  }`}
                />
                <span className={required ? 'text-slate-700 font-medium' : 'text-slate-500'}>
                  {name}
                </span>
                {required && (
                  <span className="ml-auto text-xs text-red-400 font-medium">required</span>
                )}
              </div>
            ))}
          </div>
          <p className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-400">
            Column names are auto-detected — slash / pipe variants accepted.
          </p>
        </div>
      </div>

      {/* Right col: upload zone or uploaded state */}
      <div className="lg:col-span-3">
        {status.uploaded && status.info ? (
          <UploadedCard
            type={type}
            info={status.info}
            summary={status.summary}
            onReplace={(info, summary) => onStatusChange({ uploaded: true, info, summary })}
            onClear={() => onStatusChange({ uploaded: false, info: null })}
          />
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
            <div>
              <p className="text-sm font-semibold text-slate-700 mb-1">
                Upload {cfg.label}
              </p>
              <p className="text-xs text-slate-400">
                Accepts Excel (.xlsx, .xls) and CSV (.csv) files. Columns are auto-detected.
              </p>
            </div>
            <UploadZone
              type={type}
              onUpload={(info, summary) => onStatusChange({ uploaded: true, info, summary })}
            />
            <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
              <AlertTriangle size={13} className="text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-700">
                No data uploaded yet. Upload your {cfg.label.toLowerCase()} to enable AI insights for this category.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

const TABS: DataType[] = ['financial', 'pos', 'customer']

export default function DataCollection() {
  const [activeTab, setActiveTab] = useState<DataType>('financial')
  const [statuses, setStatuses] = useState<Record<DataType, UploadStatus>>({
    financial: { uploaded: false, info: null },
    pos:       { uploaded: false, info: null },
    customer:  { uploaded: false, info: null },
  })

  useEffect(() => {
    api.upload.statusAll().then((all: any) => {
      const next: Record<DataType, UploadStatus> = {
        financial: { uploaded: false, info: null },
        pos:       { uploaded: false, info: null },
        customer:  { uploaded: false, info: null },
      }
      for (const type of TABS) {
        if (all[type]?.uploaded) {
          next[type] = { uploaded: true, info: all[type].info, summary: null }
        }
      }
      setStatuses(next)
      // fetch summaries for uploaded types
      for (const type of TABS) {
        if (all[type]?.uploaded) {
          const summaryFn = type === 'financial'
            ? api.upload.summaryFinancial
            : type === 'pos'
            ? api.upload.summaryPos
            : api.upload.summaryCustomer
          summaryFn().then((sum: any) => {
            setStatuses((prev) => ({ ...prev, [type]: { ...prev[type], summary: sum } }))
          }).catch(() => {})
        }
      }
    }).catch(() => {})
  }, [])

  const uploadedCount = TABS.filter((t) => statuses[t].uploaded).length

  return (
    <div>
      <Header
        title="Data Collection"
        subtitle="Upload and manage your café datasets — Financial, POS Billing, and Customer data"
      />

      <div className="p-6 space-y-6">

        {/* Status overview row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {TABS.map((type) => {
            const cfg = DATASET_CONFIG[type]
            const Icon = cfg.icon
            const s = statuses[type]
            return (
              <button
                key={type}
                onClick={() => setActiveTab(type)}
                className={`text-left rounded-xl border p-4 transition-all shadow-sm hover:shadow-md ${
                  activeTab === type
                    ? `${cfg.statusCard} border-l-4 ${cfg.accent}`
                    : 'bg-white border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cfg.iconBg}`}>
                    <Icon size={16} />
                  </div>
                  {s.uploaded ? (
                    <CheckCircle size={14} className="text-emerald-500" />
                  ) : (
                    <AlertCircle size={14} className="text-slate-300" />
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-800">{cfg.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {s.uploaded
                    ? `${(s.info?.rows ?? s.info?.total_customers ?? 0).toLocaleString()} records loaded`
                    : 'No data uploaded'}
                </p>
              </button>
            )
          })}
        </div>

        {/* Progress hint */}
        {uploadedCount < 3 && (
          <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
            <Info size={13} />
            <span>
              <strong>{uploadedCount}/3</strong> datasets uploaded.{' '}
              {uploadedCount === 0
                ? 'Upload all three to unlock the full AI intelligence suite.'
                : 'Upload remaining datasets to unlock more AI use cases.'}
            </span>
          </div>
        )}
        {uploadedCount === 3 && (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-100 rounded-lg text-xs text-emerald-700">
            <CheckCircle size={13} />
            <span>All 3 datasets uploaded — full AI intelligence suite is active.</span>
          </div>
        )}

        {/* Tab navigation */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="flex border-b border-slate-200 overflow-x-auto">
            {TABS.map((type) => {
              const cfg = DATASET_CONFIG[type]
              const Icon = cfg.icon
              const s = statuses[type]
              return (
                <button
                  key={type}
                  onClick={() => setActiveTab(type)}
                  className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors flex-shrink-0 ${
                    activeTab === type
                      ? cfg.tabActive
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Icon size={15} />
                  {cfg.label}
                  {s.uploaded && (
                    <span className={`w-2 h-2 rounded-full ${
                      type === 'financial' ? 'bg-emerald-400' :
                      type === 'pos' ? 'bg-indigo-400' : 'bg-purple-400'
                    }`} />
                  )}
                </button>
              )
            })}
          </div>

          <div className="p-6">
            <DatasetTab
              key={activeTab}
              type={activeTab}
              status={statuses[activeTab]}
              onStatusChange={(s) => setStatuses((prev) => ({ ...prev, [activeTab]: s }))}
            />
          </div>
        </div>

      </div>
    </div>
  )
}
