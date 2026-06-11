import { useCallback, useEffect, useRef, useState } from 'react'
import {
  CheckCircle, AlertCircle, Upload, FileSpreadsheet, Trash2,
  Info, TrendingUp, Users, ShoppingCart, AlertTriangle, X, MessageSquare, UtensilsCrossed,
  Database, Search, ChevronLeft, ChevronRight, PlusCircle, Link2, Wifi, Save, TestTube, Download,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

// ─── Types ─────────────────────────────────────────────────────────────────────

type DataType = 'financial' | 'pos' | 'customer' | 'reviews' | 'menu'

interface UploadStatus {
  uploaded: boolean
  info: any
  summary?: any
}

// ─── Config per dataset ────────────────────────────────────────────────────────

const DATASET_CONFIG = {
  financial: {
    label: 'Money & Expenses',
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
      { name: 'Monthly Revenue', required: true },
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
    preview_labels: ['Date', 'Monthly Revenue', 'Gross Margin%', 'Net Profit', 'Food Cost%', 'Labor%'],
  },
  pos: {
    label: 'Sales & Orders',
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
    label: 'Customer Records',
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
  reviews: {
    label: 'Customer Reviews',
    icon: MessageSquare,
    color: 'rose',
    accent: 'border-rose-400',
    badge: 'bg-rose-100 text-rose-700',
    btnPrimary: 'bg-rose-600 hover:bg-rose-700 text-white',
    btnOutline: 'border-rose-300 text-rose-700 hover:bg-rose-50',
    dragActive: 'border-rose-400 bg-rose-50',
    iconBg: 'bg-rose-50 text-rose-600',
    tabActive: 'border-rose-500 text-rose-700 bg-rose-50',
    statusCard: 'border-rose-200 bg-rose-50',
    ai_usecases: [
      'Sentiment Distribution Analysis', 'Source Reputation Tracking',
      'Visit Type Satisfaction Scoring', 'Negative Review Alerts',
      'Positive Keyword Cloud', 'Location Performance Ranking',
      'Review Amplification Campaigns', 'Customer Experience Optimization',
    ],
    required_fields: [
      { name: 'Review_Text', required: true },
      { name: 'Sentiment_Label', required: false },
      { name: 'Review_ID', required: false },
      { name: 'Source', required: false },
      { name: 'Review_Date', required: false },
      { name: 'Cafe_Location', required: false },
      { name: 'Visit_Type', required: false },
      { name: 'Rating', required: false },
    ],
    preview_cols: ['review_date', 'source', 'visit_type', 'rating', 'sentiment'],
    preview_labels: ['Date', 'Source', 'Visit Type', 'Rating', 'Sentiment'],
  },
  menu: {
    label: 'Menu & Pricing',
    icon: UtensilsCrossed,
    color: 'amber',
    accent: 'border-amber-400',
    badge: 'bg-amber-100 text-amber-700',
    btnPrimary: 'bg-amber-600 hover:bg-amber-700 text-white',
    btnOutline: 'border-amber-300 text-amber-700 hover:bg-amber-50',
    dragActive: 'border-amber-400 bg-amber-50',
    iconBg: 'bg-amber-50 text-amber-600',
    tabActive: 'border-amber-500 text-amber-700 bg-amber-50',
    statusCard: 'border-amber-200 bg-amber-50',
    ai_usecases: [
      'Price Optimisation Engine', 'Seasonal Menu Planning',
      'Veg / Non-Veg Mix Analysis', 'Category Margin Calculator',
      'Daypart Performance Mapping', 'SKU Rationalisation',
      'Menu Engineering Matrix', 'Location-wise Pricing Intelligence',
    ],
    required_fields: [
      { name: 'Item / Item Name', required: true },
      { name: 'Category', required: false },
      { name: 'Base Price', required: false },
      { name: 'Season', required: false },
      { name: 'Available Dayparts', required: false },
      { name: 'Veg / Non-Veg', required: false },
      { name: 'SKU', required: false },
      { name: 'Notes', required: false },
    ],
    preview_cols: ['sku', 'category', 'item', 'base_price', 'season', 'veg'],
    preview_labels: ['SKU', 'Category', 'Item', 'Base Price', 'Season', 'Veg/NV'],
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
      const uploadFn =
        type === 'financial' ? api.upload.financial
        : type === 'pos' ? api.upload.pos
        : type === 'customer' ? api.upload.customer
        : type === 'reviews' ? api.upload.reviews
        : api.upload.menu
      const result: any = await uploadFn(file)
      const summaryFn =
        type === 'financial' ? api.upload.summaryFinancial
        : type === 'pos' ? api.upload.summaryPos
        : type === 'customer' ? api.upload.summaryCustomer
        : type === 'reviews' ? api.upload.summaryReviews
        : api.upload.summaryMenu
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
            <p className="text-sm font-medium text-slate-600">
              {type === 'reviews' ? 'Running sentiment model…' : type === 'menu' ? 'Parsing menu catalogue…' : 'Parsing file…'}
            </p>
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
  onViewAll,
}: {
  type: DataType
  info: any
  summary: any
  onReplace: (info: any, summary: any) => void
  onClear: () => void
  onViewAll: () => void
}) {
  const cfg = DATASET_CONFIG[type]
  const replaceRef = useRef<HTMLInputElement>(null)
  const appendRef  = useRef<HTMLInputElement>(null)
  const [clearing, setClearing]       = useState(false)
  const [clearError, setClearError]   = useState<string | null>(null)
  const [appending, setAppending]     = useState(false)
  const [appendResult, setAppendResult] = useState<string | null>(null)
  const supportsAppend = type === 'pos' || type === 'customer'

  const handleClear = async () => {
    setClearing(true)
    setClearError(null)
    try {
      if (type === 'financial') await api.upload.clearFinancial()
      else if (type === 'pos') await api.upload.clearPos()
      else if (type === 'customer') await api.upload.clearCustomer()
      else if (type === 'reviews') await api.upload.clearReviews()
      else await api.upload.clearMenu()
      onClear()
    } catch (e: any) {
      setClearError(e.message || 'Failed to clear data. Please try again.')
    } finally {
      setClearing(false)
    }
  }

  const processFile = async (file: File, mode: 'replace' | 'append' = 'replace') => {
    if (!file.name.match(/\.(xlsx|xls|csv)$/i)) return
    if (mode === 'append') setAppending(true)
    try {
      let result: any
      if (type === 'pos')      result = await api.upload.pos(file, mode)
      else if (type === 'customer') result = await api.upload.customer(file, mode)
      else if (type === 'financial') result = await api.upload.financial(file)
      else if (type === 'reviews')   result = await api.upload.reviews(file)
      else                           result = await api.upload.menu(file)

      const summaryFn =
        type === 'financial' ? api.upload.summaryFinancial
        : type === 'pos' ? api.upload.summaryPos
        : type === 'customer' ? api.upload.summaryCustomer
        : type === 'reviews' ? api.upload.summaryReviews
        : api.upload.summaryMenu
      const sum: any = await summaryFn()
      onReplace(result.info, sum)

      if (mode === 'append') {
        const i = result.info
        if (type === 'pos') {
          setAppendResult(`+${(i.new_records ?? 0).toLocaleString()} new rows · ${(i.duplicates_skipped ?? 0)} duplicates skipped · ${(i.rows ?? 0).toLocaleString()} total`)
        } else {
          setAppendResult(`+${(i.new_records ?? 0).toLocaleString()} new · ${(i.updated_records ?? 0)} updated · ${(i.rows ?? 0).toLocaleString()} total`)
        }
        setTimeout(() => setAppendResult(null), 6000)
      }
    } finally {
      if (mode === 'append') setAppending(false)
    }
  }

  const recordCount = info.rows ?? info.count ?? info.total_reviews ?? info.total_customers ?? 0

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
              {type === 'reviews' && info.model_type && (
                <span className="text-xs px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full font-medium">
                  {info.model_type}
                </span>
              )}
              {info.mode === 'append' && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">
                  Incremental
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-slate-900">{info.filename}</p>
            <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-slate-500">
              <span><strong className="text-slate-700">{recordCount.toLocaleString?.()}</strong> records</span>
              {info.skipped > 0 && <span className="text-yellow-600"><strong>{info.skipped}</strong> skipped</span>}
              {info.date_range?.from && (
                <span><strong className="text-slate-700">{info.date_range.from}</strong> → <strong className="text-slate-700">{info.date_range.to}</strong></span>
              )}
              {info.model_accuracy && (
                <span className="text-emerald-600"><strong>{info.model_accuracy}</strong> model accuracy</span>
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
        <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
          <button
            onClick={onViewAll}
            className={`text-xs px-3 py-1.5 rounded border flex items-center gap-1.5 transition-colors ${cfg.btnPrimary}`}
          >
            <Database size={11} /> View All Data
          </button>
          {supportsAppend && (
            <button
              onClick={() => appendRef.current?.click()}
              disabled={appending}
              className="text-xs px-3 py-1.5 rounded border border-blue-300 text-blue-600 hover:bg-blue-50 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {appending
                ? <><span className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" /> Adding…</>
                : <><PlusCircle size={11} /> Add More Data</>}
            </button>
          )}
          <button
            onClick={() => replaceRef.current?.click()}
            className={`text-xs px-3 py-1.5 rounded border flex items-center gap-1.5 transition-colors ${cfg.btnOutline}`}
          >
            <Upload size={11} /> Replace
          </button>
          <button
            onClick={handleClear}
            disabled={clearing}
            className="text-xs px-3 py-1.5 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            {clearing
              ? <><span className="w-3 h-3 border-2 border-red-300 border-t-red-500 rounded-full animate-spin" /> Clearing…</>
              : <><Trash2 size={11} /> Clear</>}
          </button>
          {clearError && (
            <span className="text-xs text-red-500 flex items-center gap-1">
              <AlertCircle size={11} /> {clearError}
            </span>
          )}
          <input
            ref={replaceRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => { if (e.target.files?.[0]) processFile(e.target.files[0], 'replace') }}
          />
          {supportsAppend && (
            <input
              ref={appendRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => { if (e.target.files?.[0]) processFile(e.target.files[0], 'append') }}
            />
          )}
        </div>
      </div>

      {/* Append result toast */}
      {appendResult && (
        <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
          <CheckCircle size={12} className="text-blue-500 flex-shrink-0" />
          <span>{appendResult}</span>
          <button className="ml-auto" onClick={() => setAppendResult(null)}><X size={11} /></button>
        </div>
      )}

      {/* Summary stats */}
      {summary && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <SummaryStats type={type} summary={summary} onViewAll={onViewAll} />
        </div>
      )}
    </div>
  )
}

// ─── Summary Stats ──────────────────────────────────────────────────────────────

function SummaryStats({ type, summary, onViewAll }: { type: DataType; summary: any; onViewAll?: () => void }) {
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
            totalRecords={s.records ?? info.rows}
            onViewAll={onViewAll}
            formatters={{
              date: (v: any) => fmtFinancialDate(v),
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
            totalRecords={s.total_orders ?? info.rows}
            onViewAll={onViewAll}
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
            totalRecords={s.total_customers ?? info.rows}
            onViewAll={onViewAll}
            formatters={{
              avg_order_value: (v: any) => v != null ? `₹${Number(v).toFixed(0)}` : '—',
              loyalty_points: (v: any) => v != null ? Number(v).toLocaleString() : '—',
            }}
          />
        )}
      </div>
    )
  }

  if (type === 'menu') {
    const s2 = summary?.summary ?? {}
    const cats: any[] = summary?.category_breakdown ?? []
    const items: any[] = (summary?.recent ?? []).slice(0, 5)
    if (!s2.total_skus && !items.length) return null
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Total SKUs" value={Number(s2.total_skus ?? 0).toLocaleString()} />
          <StatChip label="Categories" value={String(s2.total_categories ?? 0)} />
          <StatChip label="Price Range" value={s2.price_min != null ? `₹${s2.price_min} – ₹${s2.price_max}` : '—'} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Avg Base Price" value={s2.price_avg != null ? `₹${s2.price_avg}` : '—'} />
          <StatChip label="Seasonal Items" value={String(s2.seasonal_items ?? 0)} />
          <StatChip label="Year-Round Items" value={String(s2.year_round_items ?? 0)} />
        </div>
        {cats.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {cats.slice(0, 10).map((c: any) => (
              <span key={c.category} className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 border border-amber-200 text-amber-700">
                {c.category} <strong>{c.count}</strong>
              </span>
            ))}
          </div>
        )}
        {items.length > 0 && (
          <DataPreviewTable
            rows={items}
            cols={DATASET_CONFIG.menu.preview_cols}
            labels={DATASET_CONFIG.menu.preview_labels}
            totalRecords={s2.total_skus ?? info.rows}
            onViewAll={onViewAll}
            formatters={{
              base_price: (v: any) => v ? `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—',
            }}
          />
        )}
      </div>
    )
  }

  if (type === 'reviews') {
    // summary shape: { uploaded, info, stats, recent_records }
    const stats = summary?.stats ?? {}
    if (!stats.total_reviews) return null
    const sentColor = (label: string) =>
      label === 'Positive' ? 'text-emerald-600' :
      label === 'Negative' ? 'text-red-500' : 'text-slate-500'
    const recentRows = (summary?.recent_records ?? []).slice(0, 5)
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Total Reviews" value={Number(stats.total_reviews ?? 0).toLocaleString()} />
          <StatChip label="Satisfaction Score" value={`${stats.satisfaction_score ?? 0}%`} />
          <StatChip label="Avg Rating" value={`${stats.overall_avg_rating ?? '—'} / 5`} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <StatChip label="Positive" value={`${stats.positive ?? 0} (${stats.positive_pct ?? 0}%)`} />
          <StatChip label="Neutral" value={`${stats.neutral ?? 0} (${stats.neutral_pct ?? 0}%)`} />
          <StatChip label="Negative" value={`${stats.negative ?? 0} (${stats.negative_pct ?? 0}%)`} />
        </div>
        {recentRows.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-100">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
                <tr>
                  {['Date', 'Source', 'Visit Type', 'Rating', 'Sentiment'].map((l) => (
                    <th key={l} className="px-3 py-2 text-left font-semibold">{l}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentRows.map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-3 py-2 text-slate-600">{row.review_date || '—'}</td>
                    <td className="px-3 py-2 text-slate-700">{row.source || '—'}</td>
                    <td className="px-3 py-2 text-slate-600">{row.visit_type || '—'}</td>
                    <td className="px-3 py-2 font-semibold">{row.rating ?? '—'}</td>
                    <td className={`px-3 py-2 font-semibold ${sentColor(row.sentiment)}`}>{row.sentiment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-3 py-1.5 text-xs text-slate-400 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
              <span>Showing {recentRows.length} of {Number(stats.total_reviews ?? recentRows.length).toLocaleString()} reviews</span>
              {onViewAll && stats.total_reviews > recentRows.length && (
                <button onClick={onViewAll} className="text-blue-500 hover:text-blue-700 font-medium flex items-center gap-1">
                  <Database size={10} /> View all {Number(stats.total_reviews).toLocaleString()} reviews
                </button>
              )}
            </div>
          </div>
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
  totalRecords,
  onViewAll,
}: {
  rows: any[]
  cols: readonly string[]
  labels: readonly string[]
  formatters?: Record<string, (v: any) => string>
  totalRecords?: number
  onViewAll?: () => void
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
      <div className="px-3 py-1.5 text-xs text-slate-400 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
        <span>Showing {rows.length} of {(totalRecords ?? rows.length).toLocaleString()} records</span>
        {onViewAll && totalRecords && totalRecords > rows.length && (
          <button
            onClick={onViewAll}
            className="text-blue-500 hover:text-blue-700 font-medium flex items-center gap-1"
          >
            <Database size={10} /> View all {totalRecords.toLocaleString()} records
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Helpers ────────────────────────────────────────────────────────────────────

/** Display a financial date as "Jan-2023" when it falls on the 1st of a month,
 *  matching the original Excel period format (e.g. Jan-2023 stored as 2023-01-01). */
function fmtFinancialDate(v: any): string {
  if (v == null || v === '') return '—'
  const s = String(v)
  const d = new Date(s + 'T00:00:00')   // force local time to avoid UTC shift
  if (isNaN(d.getTime())) return s
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  if (d.getDate() === 1) return `${MONTHS[d.getMonth()]}-${d.getFullYear()}`
  return s
}

/** Human-friendly column header labels for the Data Viewer. */
const COL_LABELS: Record<string, string> = {
  daily_revenue:     'Monthly Revenue',
  gross_margin_pct:  'Gross Margin %',
  food_cost_pct:     'Food Cost %',
  labor_cost_pct:    'Labor Cost %',
  net_profit:        'Net Profit (₹)',
  electricity:       'Electricity (₹)',
  rent:              'Rent (₹)',
  marketing:         'Marketing (₹)',
  packaging:         'Packaging (₹)',
  commission:        'Commission (₹)',
  avg_order_value:   'Avg Order (₹)',
  bill_amount:       'Bill Amount',
  favorite_items:    'Favourite Items',
  favourite_items:   'Favourite Items',
  review_text:       'Review Text',
  visit_frequency:   'Visit Freq',
  loyalty_points:    'Loyalty Pts',
  platform_source:   'Platform',
}

// ─── Data Viewer Modal ──────────────────────────────────────────────────────────

function DataViewerModal({
  isOpen,
  onClose,
  initialType,
  statuses,
}: {
  isOpen: boolean
  onClose: () => void
  initialType: DataType
  statuses: Record<DataType, UploadStatus>
}) {
  const [activeType, setActiveType] = useState<DataType>(initialType)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // Always sync activeType when the caller changes which section to show.
  // Using only [initialType] (not [isOpen, initialType]) ensures that clicking
  // "View All Records" from a different section always switches to that section,
  // even if the modal was already open or its internal tab had been changed.
  useEffect(() => {
    setActiveType(initialType)
    setPage(1)
    setSearch('')
  }, [initialType])

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350)
    return () => clearTimeout(t)
  }, [search])

  // Reset page on tab/search change
  useEffect(() => { setPage(1) }, [activeType, debouncedSearch])

  // Load records
  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setResult(null)
    ;(api.upload.records as any)(activeType, page, 50, debouncedSearch)
      .then((r: any) => setResult(r))
      .catch(() => setResult(null))
      .finally(() => setLoading(false))
  }, [isOpen, activeType, page, debouncedSearch])

  if (!isOpen) return null

  const uploadedTabs = TABS.filter((t) => statuses[t].uploaded)
  const cfg = DATASET_CONFIG[activeType]
  const records: any[] = result?.records ?? []
  const total: number  = result?.total  ?? 0
  const pages: number  = result?.pages  ?? 1
  const start = total === 0 ? 0 : (page - 1) * 50 + 1
  const end   = Math.min(page * 50, total)

  // Derive column headers from first record
  const allCols: string[] = records.length > 0 ? Object.keys(records[0]) : cfg.preview_cols as unknown as string[]
  const visibleCols = allCols

  const fmtVal = (col: string, val: any) => {
    if (val == null || val === '') return '—'

    // ── Date: show "Jan-2023" for financial month-period dates ────────────────
    if (col === 'date' && activeType === 'financial') return fmtFinancialDate(val)

    if (typeof val === 'number') {
      // ── Currency columns ── ₹ with comma formatting ────────────────────────
      const CURRENCY_COLS = [
        'daily_revenue', 'revenue', 'bill_amount', 'base_price', 'avg_order_value',
        'net_profit', 'electricity', 'rent', 'marketing', 'packaging', 'commission',
      ]
      if (CURRENCY_COLS.includes(col))
        return `₹${Number(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
      // ── Percentage columns ─────────────────────────────────────────────────
      if (col.endsWith('_pct') || col.endsWith('_percent'))
        return `${Number(val).toFixed(1)}%`
      return String(val)
    }

    const s = String(val)
    // Wide columns: review text, notes, and favourite items show full content
    const WIDE_COLS = ['review_text', 'notes', 'rationale', 'feedback', 'favorite_items', 'favourite_items']
    const limit = WIDE_COLS.includes(col) ? 300 : 40
    return s.length > limit ? s.slice(0, limit - 2) + '…' : s
  }

  const dotColor =
    activeType === 'financial' ? 'bg-emerald-400' :
    activeType === 'pos'       ? 'bg-indigo-400'  :
    activeType === 'customer'  ? 'bg-purple-400'  :
    activeType === 'reviews'   ? 'bg-rose-400'    : 'bg-amber-400'

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-stretch p-4" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="flex-1 flex flex-col bg-white rounded-2xl overflow-hidden shadow-2xl max-h-full">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${cfg.iconBg}`}>
              <Database size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Data Viewer</h2>
              <p className="text-xs text-slate-400">Browse all uploaded records</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500">
            <X size={18} />
          </button>
        </div>

        {/* Dataset tabs */}
        <div className="flex border-b border-slate-200 overflow-x-auto flex-shrink-0 px-2">
          {uploadedTabs.map((type) => {
            const Icon = DATASET_CONFIG[type].icon
            const c    = DATASET_CONFIG[type]
            const cnt  = statuses[type].info?.rows ?? statuses[type].info?.total_customers ?? statuses[type].info?.total_reviews ?? 0
            const isActive = activeType === type
            return (
              <button
                key={type}
                onClick={() => { setActiveType(type); setSearch('') }}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors flex-shrink-0 ${
                  isActive ? `${c.tabActive} border-current` : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Icon size={13} />
                {c.label}
                <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${isActive ? c.badge : 'bg-slate-100 text-slate-500'}`}>
                  {Number(cnt).toLocaleString()}
                </span>
              </button>
            )
          })}
        </div>

        {/* Search + pagination controls */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-100 flex-shrink-0">
          <div className="relative flex-1 max-w-sm">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search records…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={12} />
              </button>
            )}
          </div>
          <div className="ml-auto flex items-center gap-3">
            {result && (
              <span className="text-xs text-slate-400">
                {loading ? 'Loading…' : `${start.toLocaleString()}–${end.toLocaleString()} of ${total.toLocaleString()}`}
              </span>
            )}
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="px-3 py-1 text-xs text-slate-600 font-medium border border-slate-200 rounded-lg min-w-[70px] text-center">
                {page} / {pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page >= pages || loading}
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-500 rounded-full animate-spin" />
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-400">
              <Database size={32} className="mb-2 opacity-30" />
              <p className="text-sm">{search ? 'No records match your search' : 'No records found'}</p>
            </div>
          ) : (
            <table className="w-max min-w-full text-xs border-collapse">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr>
                  <th className="px-3 py-2.5 text-left text-slate-400 font-semibold uppercase tracking-wide border-b border-slate-200 w-10">#</th>
                  {visibleCols.map((col) => (
                    <th key={col} className="px-3 py-2.5 text-left text-slate-500 font-semibold uppercase tracking-wide border-b border-slate-200 whitespace-nowrap">
                      {COL_LABELS[col] ?? col.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {records.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-3 py-2 text-slate-400">{start + i}</td>
                    {visibleCols.map((col) => (
                      <td
                        key={col}
                        className={`px-3 py-2 text-slate-700 ${
                          ['review_text', 'notes', 'feedback', 'favorite_items', 'favourite_items'].includes(col)
                            ? 'max-w-sm whitespace-normal break-words leading-relaxed'
                            : 'max-w-[200px] truncate'
                        }`}
                        title={String(row[col] ?? '')}
                      >
                        {fmtVal(col, row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer pagination */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 flex-shrink-0 bg-slate-50">
          <span className="text-xs text-slate-500">
            {total > 0 ? `${total.toLocaleString()} total records` : 'No data'}
            {search && ` matching "${search}"`}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(1)} disabled={page <= 1 || loading} className="px-2 py-1 text-xs rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed">First</button>
            {Array.from({ length: Math.min(5, pages) }, (_, i) => {
              const p = Math.max(1, Math.min(pages - 4, page - 2)) + i
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  disabled={loading}
                  className={`w-7 h-7 text-xs rounded border transition-colors disabled:cursor-not-allowed ${
                    p === page ? `${cfg.badge} border-current font-bold` : 'border-slate-200 hover:bg-slate-100 text-slate-600'
                  }`}
                >
                  {p}
                </button>
              )
            })}
            <button onClick={() => setPage(pages)} disabled={page >= pages || loading} className="px-2 py-1 text-xs rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed">Last</button>
          </div>
        </div>

      </div>
    </div>
  )
}


// ─── API Connect Panel ──────────────────────────────────────────────────────────

const SYNC_OPTIONS = [
  { value: 'manual', label: 'Manual only' },
  { value: 'hourly', label: 'Every hour' },
  { value: 'daily',  label: 'Once a day' },
  { value: 'weekly', label: 'Once a week' },
]

interface ApiConfig {
  url: string
  apiKey: string
  syncInterval: string
  lastTested?: string
  connected?: boolean
}

function ApiConnectPanel({ type }: { type: DataType }) {
  const storageKey = `cafebuddy_api_${type}`
  const [config, setConfig] = useState<ApiConfig>(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) || '{}') } catch { return {} }
  })
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const cfg = DATASET_CONFIG[type]

  const save = () => {
    localStorage.setItem(storageKey, JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const testConnection = async () => {
    if (!config.url) { setTestResult({ ok: false, msg: 'Enter an API endpoint URL first.' }); return }
    setTesting(true); setTestResult(null)
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (config.apiKey) headers['Authorization'] = `Bearer ${config.apiKey}`
      const res = await fetch(config.url, { method: 'GET', headers, signal: AbortSignal.timeout(8000) })
      if (res.ok) {
        setTestResult({ ok: true, msg: `Connected — HTTP ${res.status}. Your POS data can now be pulled automatically.` })
        setConfig((c) => ({ ...c, lastTested: new Date().toLocaleString(), connected: true }))
      } else {
        setTestResult({ ok: false, msg: `Server returned HTTP ${res.status}. Check the URL and API key.` })
        setConfig((c) => ({ ...c, connected: false }))
      }
    } catch (e: any) {
      setTestResult({ ok: false, msg: e.message?.includes('abort') ? 'Request timed out (8s). Check the URL.' : `Connection failed: ${e.message}` })
      setConfig((c) => ({ ...c, connected: false }))
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.iconBg}`}>
          <Link2 size={18} />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800">Connect Your POS System</p>
          <p className="text-xs text-slate-500 mt-0.5">
            Point Cafe Buddy to your POS API and it will pull {cfg.label.toLowerCase()} automatically — no more manual exports.
          </p>
        </div>
      </div>

      {/* Inputs */}
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">API Endpoint URL</label>
          <input
            type="url"
            placeholder="https://your-pos-system.com/api/v1/orders"
            value={config.url || ''}
            onChange={(e) => setConfig((c) => ({ ...c, url: e.target.value }))}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">API Key / Bearer Token</label>
          <input
            type="password"
            placeholder="sk-xxxxxxxxxxxxxx"
            value={config.apiKey || ''}
            onChange={(e) => setConfig((c) => ({ ...c, apiKey: e.target.value }))}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 font-mono"
          />
          <p className="text-xs text-slate-400 mt-1">Sent as <code className="bg-slate-100 px-1 rounded">Authorization: Bearer …</code></p>
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Auto-sync Frequency</label>
          <select
            value={config.syncInterval || 'manual'}
            onChange={(e) => setConfig((c) => ({ ...c, syncInterval: e.target.value }))}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
          >
            {SYNC_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Test result */}
      {testResult && (
        <div className={`flex items-start gap-2 px-3 py-2.5 rounded-lg text-xs border ${
          testResult.ok
            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          {testResult.ok ? <CheckCircle size={13} className="mt-0.5 flex-shrink-0" /> : <AlertCircle size={13} className="mt-0.5 flex-shrink-0" />}
          <span>{testResult.msg}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={testConnection}
          disabled={testing}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          {testing
            ? <><span className="w-3 h-3 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" /> Testing…</>
            : <><TestTube size={12} /> Test Connection</>}
        </button>
        <button
          onClick={save}
          className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg transition-colors ${
            saved
              ? 'bg-emerald-500 text-white border border-emerald-500'
              : `${cfg.btnPrimary} border border-transparent`
          }`}
        >
          {saved ? <><CheckCircle size={12} /> Saved!</> : <><Save size={12} /> Save Settings</>}
        </button>
        {config.lastTested && (
          <span className="text-xs text-slate-400 ml-auto">Last tested: {config.lastTested}</span>
        )}
      </div>

      {/* Status chip */}
      <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
        <div className={`w-2 h-2 rounded-full ${config.connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-300'}`} />
        <span className="text-xs text-slate-500">
          {config.connected ? 'API connected — ready to sync' : 'Not connected yet'}
        </span>
        {config.syncInterval && config.syncInterval !== 'manual' && config.connected && (
          <span className="ml-auto text-xs px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-600 rounded-full flex items-center gap-1">
            <Wifi size={10} /> Auto-sync: {SYNC_OPTIONS.find((o) => o.value === config.syncInterval)?.label}
          </span>
        )}
      </div>
    </div>
  )
}

// ─── Tab Panel ──────────────────────────────────────────────────────────────────

function DatasetTab({
  type,
  status,
  onStatusChange,
  onViewAll,
}: {
  type: DataType
  status: UploadStatus
  onStatusChange: (s: UploadStatus) => void
  onViewAll: () => void
}) {
  const cfg = DATASET_CONFIG[type]
  const [entryMode, setEntryMode] = useState<'excel' | 'api'>('excel')

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

        {/* Expected Fields — only shown in excel mode */}
        {entryMode === 'excel' && (
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
              {type === 'reviews'
                ? 'Upload CSV with Review_Text column. Sentiment_Label used if present; else model predicts.'
                : 'Column names are auto-detected — slash / pipe variants accepted.'}
            </p>
          </div>
        )}
      </div>

      {/* Right col: mode toggle + upload zone / api panel / uploaded state */}
      <div className="lg:col-span-3 space-y-4">

        {/* Entry mode toggle */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg w-fit">
          <button
            onClick={() => setEntryMode('excel')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              entryMode === 'excel'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <FileSpreadsheet size={13} />
            Upload Excel / CSV
          </button>
          <button
            onClick={() => setEntryMode('api')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              entryMode === 'api'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Link2 size={13} />
            Connect API
          </button>
        </div>

        {/* Content */}
        {entryMode === 'api' ? (
          <ApiConnectPanel type={type} />
        ) : status.uploaded && status.info ? (
          <UploadedCard
            type={type}
            info={status.info}
            summary={status.summary}
            onReplace={(info, summary) => onStatusChange({ uploaded: true, info, summary })}
            onClear={() => onStatusChange({ uploaded: false, info: null })}
            onViewAll={onViewAll}
          />
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
            <div>
              <p className="text-sm font-semibold text-slate-700 mb-1">
                Upload {cfg.label}
              </p>
              <p className="text-xs text-slate-400">
                {type === 'reviews'
                  ? 'Accepts CSV files. The sentiment model (TF-IDF + LinearSVC, 93.4% accuracy) processes reviews automatically.'
                  : type === 'menu'
                  ? 'Accepts Excel (.xlsx, .xls) files. Reads the "Master Menu" sheet automatically. Columns are auto-detected.'
                  : 'Accepts Excel (.xlsx, .xls) and CSV (.csv) files. Columns are auto-detected.'}
              </p>
            </div>
            <UploadZone
              type={type}
              onUpload={(info, summary) => onStatusChange({ uploaded: true, info, summary })}
            />

            {/* Download Template */}
            <div className="flex items-center justify-between gap-3 p-3 bg-blue-50 border border-blue-100 rounded-lg">
              <div className="flex items-start gap-2 min-w-0">
                <Download size={13} className="text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-blue-800">Need a template?</p>
                  <p className="text-xs text-blue-600">Download a pre-filled sample CSV with the exact column headers required.</p>
                </div>
              </div>
              <button
                onClick={() => api.templates.download(type)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${cfg.btnPrimary}`}
              >
                <Download size={11} />
                Download Template
              </button>
            </div>

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

const TABS: DataType[] = ['financial', 'pos', 'customer', 'reviews', 'menu']

export default function DataCollection() {
  const [activeTab, setActiveTab] = useState<DataType>('financial')
  const [statuses, setStatuses] = useState<Record<DataType, UploadStatus>>({
    financial: { uploaded: false, info: null },
    pos:       { uploaded: false, info: null },
    customer:  { uploaded: false, info: null },
    reviews:   { uploaded: false, info: null },
    menu:      { uploaded: false, info: null },
  })
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerType, setViewerType] = useState<DataType>('financial')

  const openViewer = (type: DataType) => { setViewerType(type); setViewerOpen(true) }

  useEffect(() => {
    api.upload.statusAll().then((all: any) => {
      const next: Record<DataType, UploadStatus> = {
        financial: { uploaded: false, info: null },
        pos:       { uploaded: false, info: null },
        customer:  { uploaded: false, info: null },
        reviews:   { uploaded: false, info: null },
        menu:      { uploaded: false, info: null },
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
          const summaryFn =
            type === 'financial' ? api.upload.summaryFinancial
            : type === 'pos' ? api.upload.summaryPos
            : type === 'customer' ? api.upload.summaryCustomer
            : type === 'reviews' ? api.upload.summaryReviews
            : api.upload.summaryMenu
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
        title="Upload My Data"
        subtitle="Upload your café data or connect your POS system directly — Money & Expenses, Sales & Orders, Customers, Reviews, and Menu"
      />

      <div className="p-6 space-y-6">

        {/* Status overview row */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {TABS.map((type) => {
            const cfg = DATASET_CONFIG[type]
            const Icon = cfg.icon
            const s = statuses[type]
            const count =
              s.info?.rows ?? s.info?.total_customers ?? s.info?.total_reviews ?? 0
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
                    ? `${Number(count).toLocaleString()} records loaded`
                    : 'No data uploaded'}
                </p>
              </button>
            )
          })}
        </div>

        {/* Progress hint */}
        {uploadedCount < 5 && (
          <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700">
            <Info size={13} />
            <span>
              <strong>{uploadedCount}/5</strong> datasets uploaded.{' '}
              {uploadedCount === 0
                ? 'Upload all five to unlock the full AI intelligence suite.'
                : 'Upload remaining datasets to unlock more AI use cases.'}
            </span>
          </div>
        )}
        {uploadedCount === 5 && (
          <div className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-100 rounded-lg text-xs text-emerald-700">
            <CheckCircle size={13} />
            <span>All 5 datasets uploaded — full AI intelligence suite is active.</span>
          </div>
        )}

        {/* Tab navigation */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="flex border-b border-slate-200 overflow-x-auto">
            {TABS.map((type) => {
              const cfg = DATASET_CONFIG[type]
              const Icon = cfg.icon
              const s = statuses[type]
              const dotColor =
                type === 'financial' ? 'bg-emerald-400' :
                type === 'pos' ? 'bg-indigo-400' :
                type === 'customer' ? 'bg-purple-400' :
                type === 'reviews' ? 'bg-rose-400' : 'bg-amber-400'
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
                    <span className={`w-2 h-2 rounded-full ${dotColor}`} />
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
              onViewAll={() => openViewer(activeTab)}
            />
          </div>
        </div>

      </div>

      <DataViewerModal
        isOpen={viewerOpen}
        onClose={() => setViewerOpen(false)}
        initialType={viewerType}
        statuses={statuses}
      />
    </div>
  )
}
