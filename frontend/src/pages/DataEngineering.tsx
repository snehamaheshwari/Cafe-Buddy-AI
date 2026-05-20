import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import { Cpu, CheckCircle, Loader, AlertTriangle, TrendingUp, ShoppingCart, Users, Star, UtensilsCrossed, Lightbulb, ChevronRight } from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

const DATASET_ICONS: Record<string, any> = {
  financial: TrendingUp,
  pos: ShoppingCart,
  customer: Users,
  reviews: Star,
  menu: UtensilsCrossed,
}
const DATASET_COLORS: Record<string, string> = {
  financial: 'border-emerald-400 bg-emerald-50',
  pos: 'border-indigo-400 bg-indigo-50',
  customer: 'border-purple-400 bg-purple-50',
  reviews: 'border-rose-400 bg-rose-50',
  menu: 'border-amber-400 bg-amber-50',
}
const ICON_COLORS: Record<string, string> = {
  financial: 'text-emerald-600 bg-emerald-100',
  pos: 'text-indigo-600 bg-indigo-100',
  customer: 'text-purple-600 bg-purple-100',
  reviews: 'text-rose-600 bg-rose-100',
  menu: 'text-amber-600 bg-amber-100',
}

const CAT_COLORS = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']

function QualityMeter({ label, value }: { label: string; value: number }) {
  const color = value >= 98 ? 'bg-emerald-500' : value >= 95 ? 'bg-brand-500' : 'bg-red-500'
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
        <span className="text-lg font-bold text-slate-900">{value}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color} transition-all`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

export default function DataEngineering() {
  const [pipelines, setPipelines] = useState<any>(null)
  const [processed, setProcessed] = useState<any>(null)
  const [insights, setInsights]   = useState<any>(null)

  useEffect(() => {
    api.layer2.pipelineStatus().then(setPipelines).catch(() => {})
    api.layer2.processedData().then(setProcessed).catch(() => {})
    ;(api.layer2 as any).insights().then(setInsights).catch(() => {})
  }, [])

  const statusIcon = (s: string) => {
    if (s === 'running') return <Loader size={14} className="text-blue-500 animate-spin" />
    if (s === 'completed') return <CheckCircle size={14} className="text-emerald-500" />
    return <AlertTriangle size={14} className="text-red-500" />
  }

  const statusBadge = (s: string) =>
    s === 'running' ? 'badge bg-blue-100 text-blue-700' :
    s === 'completed' ? 'badge-ok' : 'badge-critical'

  return (
    <div>
      <Header title="Data Engineering" subtitle="Clean, process, and organize raw data into analytics-ready datasets" />
      <div className="p-6 space-y-6">

        {/* Summary Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Total Records Today</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{pipelines?.total_records_today?.toLocaleString() ?? '—'}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Active Pipelines</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{pipelines?.pipelines?.filter((p: any) => p.status === 'running').length ?? '—'}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">30-Day Revenue</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {processed ? `₹${(processed.total_revenue / 100000).toFixed(1)}L` : '—'}
            </p>
          </div>
          <div className="card p-4 border-l-4 border-yellow-400">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Anomalies Detected</p>
            <p className="text-2xl font-bold text-yellow-600 mt-1">{pipelines?.anomalies_detected ?? '—'}</p>
          </div>
        </div>

        {/* Data Quality */}
        <div>
          <h2 className="section-title mb-3">Data Quality Scores</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {pipelines?.data_quality && Object.entries(pipelines.data_quality).map(([k, v]: [string, any]) => (
              <QualityMeter key={k} label={k} value={v} />
            ))}
          </div>
        </div>

        {/* Pipeline Table */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">ETL Pipeline Status</span>
            <Cpu size={14} className="text-slate-400" />
          </div>
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Status</th>
                  <th>Records Processed</th>
                  <th>Success Rate</th>
                  <th>Duration</th>
                  <th>Last Run</th>
                </tr>
              </thead>
              <tbody>
                {(pipelines?.pipelines || []).map((p: any) => (
                  <tr key={p.name}>
                    <td>
                      <div className="flex items-center gap-2">
                        {statusIcon(p.status)}
                        <span className="font-medium">{p.name}</span>
                      </div>
                    </td>
                    <td><span className={statusBadge(p.status)}>{p.status}</span></td>
                    <td className="font-mono">{p.records.toLocaleString()}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${p.success_rate}%` }} />
                        </div>
                        <span className="text-xs font-mono">{p.success_rate}%</span>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-slate-500">{p.duration}</td>
                    <td className="text-slate-400 text-xs">{p.last_run}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* AI Insights from Your Data */}
        {insights && Object.keys(insights).length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb size={16} className="text-amber-500" />
              <h2 className="section-title">AI Insights from Your Data</h2>
              <span className="text-xs text-slate-400 ml-1">— what each dataset reveals</span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {Object.entries(insights).map(([key, ds]: [string, any]) => {
                const Icon = DATASET_ICONS[key] || Cpu
                const colorCard = DATASET_COLORS[key] || 'border-slate-300 bg-slate-50'
                const iconColor = ICON_COLORS[key] || 'text-slate-600 bg-slate-100'
                const facts: string[] = (ds.key_facts || []).filter(Boolean)
                const enabled: string[] = ds.insights_enabled || []
                return (
                  <div key={key} className={`rounded-xl border-l-4 p-4 ${colorCard}`}>
                    <div className="flex items-center gap-3 mb-3">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${iconColor}`}>
                        <Icon size={16} />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-900">{ds.dataset}</p>
                        <p className="text-xs text-slate-500">{ds.records?.toLocaleString()} records · {ds.filename}</p>
                      </div>
                    </div>

                    {/* Key facts */}
                    <div className="space-y-1 mb-3">
                      {facts.map((f: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-slate-700">
                          <CheckCircle size={11} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span>{f}</span>
                        </div>
                      ))}
                    </div>

                    {/* Insights enabled */}
                    <div className="border-t border-white/60 pt-2.5 space-y-1">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Analysis Unlocked</p>
                      {enabled.map((ins: string, i: number) => (
                        <div key={i} className="flex items-center gap-1.5 text-xs text-slate-600">
                          <ChevronRight size={10} className="text-slate-400 flex-shrink-0" />
                          {ins}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {insights && Object.keys(insights).length === 0 && (
          <div className="p-6 text-center bg-slate-50 rounded-xl border border-slate-200">
            <Lightbulb size={24} className="text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No data uploaded yet — upload datasets in Data Collection to see AI insights here.</p>
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Daily Revenue Line */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Daily Revenue (Processed)</span>
              <span className="text-xs text-slate-400">Last 14 days</span>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={processed?.daily_sales || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false}
                    tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => [`₹${v.toLocaleString('en-IN')}`, 'Revenue']}
                    contentStyle={{ fontSize: 12, borderRadius: 4, border: '1px solid #e2e8f0' }} />
                  <Line type="monotone" dataKey="revenue" stroke="#8b5cf6" strokeWidth={2} dot={false}
                    activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Category Revenue Bar */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Revenue by Category</span>
              <span className="text-xs text-slate-400">30-day aggregation</span>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={processed?.category_breakdown || []} barSize={40}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="category" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => [`₹${v.toLocaleString('en-IN')}`, 'Revenue']}
                    contentStyle={{ fontSize: 12, borderRadius: 4, border: '1px solid #e2e8f0' }} />
                  <Bar dataKey="revenue" radius={[3, 3, 0, 0]}>
                    {(processed?.category_breakdown || []).map((_: any, i: number) => (
                      <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
