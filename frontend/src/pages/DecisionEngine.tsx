import { useEffect, useState } from 'react'
import { Zap, CheckCircle, XCircle, Clock, TrendingUp, Filter } from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

const TYPE_ICONS: Record<string, string> = {
  pricing: '💰', inventory: '📦', marketing: '📣', staffing: '👥', menu: '🍽️',
}

const CATEGORY_COLORS: Record<string, string> = {
  'Revenue Optimization': 'bg-brand-50 border-brand-200',
  'Inventory Management': 'bg-red-50 border-red-200',
  'Marketing': 'bg-purple-50 border-purple-200',
  'Operations': 'bg-sky-50 border-sky-200',
  'Menu Optimization': 'bg-emerald-50 border-emerald-200',
}

export default function DecisionEngine() {
  const [data, setData] = useState<any>(null)
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all')
  const [loading, setLoading] = useState<number | null>(null)

  const refresh = () => api.layer4.decisions().then(setData)

  useEffect(() => { refresh() }, [])

  const handleApprove = async (id: number) => {
    setLoading(id)
    await api.layer4.approve(id)
    await refresh()
    setLoading(null)
  }

  const handleReject = async (id: number) => {
    setLoading(id)
    await api.layer4.reject(id)
    await refresh()
    setLoading(null)
  }

  const decisions = (data?.decisions || []).filter((d: any) =>
    filter === 'all' || d.status === filter
  )
  const summary = data?.summary || {}

  const priorityBadge = (p: string) => {
    const map: Record<string, string> = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }
    return map[p] || 'badge-low'
  }

  return (
    <div>
      <Header title="Decision Engine" subtitle="AI-generated actionable recommendations for your café operations" />
      <div className="p-6 space-y-6">

        {/* Summary Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Total Decisions</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{data?.decisions?.length ?? '—'}</p>
          </div>
          <div className="card p-4 border-l-4 border-blue-400">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Pending Approval</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{summary.pending ?? '—'}</p>
          </div>
          <div className="card p-4 border-l-4 border-emerald-400">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Approved</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{summary.approved ?? '—'}</p>
          </div>
          <div className="card p-4 border-l-4 border-slate-300">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Rejected</p>
            <p className="text-2xl font-bold text-slate-500 mt-1">{summary.rejected ?? '—'}</p>
          </div>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-400" />
          <span className="text-sm text-slate-500 mr-2">Filter:</span>
          {(['all', 'pending', 'approved', 'rejected'] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors ${
                filter === f ? 'bg-slate-800 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}>
              {f}
            </button>
          ))}
        </div>

        {/* Decision Cards */}
        <div className="space-y-3">
          {decisions.length === 0 && (
            <div className="card p-8 text-center text-slate-400">No decisions found.</div>
          )}
          {decisions.map((d: any) => (
            <div key={d.id} className={`card border ${CATEGORY_COLORS[d.category] || 'border-slate-200'}`}>
              <div className="p-5">
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className="text-2xl flex-shrink-0 mt-0.5">{TYPE_ICONS[d.type] || '📋'}</div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={priorityBadge(d.priority)}>{d.priority}</span>
                      <span className="badge bg-slate-100 text-slate-600">{d.category}</span>
                      <span className={`badge ${d.status === 'pending' ? 'badge-pending' : d.status === 'approved' ? 'badge-approved' : 'badge-rejected'}`}>
                        {d.status}
                      </span>
                    </div>

                    <h3 className="text-base font-semibold text-slate-900 leading-snug mb-2">{d.title}</h3>
                    <p className="text-sm text-slate-500 mb-3">{d.rationale}</p>

                    {/* Confidence + Impact */}
                    <div className="flex flex-wrap items-center gap-6">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">Confidence</span>
                        <div className="flex items-center gap-1.5">
                          <div className="w-24 bg-slate-200 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${d.confidence}%` }} />
                          </div>
                          <span className="text-xs font-mono font-semibold text-indigo-600">{d.confidence}%</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <TrendingUp size={13} className="text-emerald-500" />
                        <span className="text-sm font-semibold text-emerald-600">{d.impact}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  {d.status === 'pending' && (
                    <div className="flex flex-col gap-2 flex-shrink-0">
                      <button
                        className="btn-success flex items-center gap-1.5"
                        disabled={loading === d.id}
                        onClick={() => handleApprove(d.id)}
                      >
                        <CheckCircle size={12} />
                        {loading === d.id ? '...' : 'Approve'}
                      </button>
                      <button
                        className="btn-danger flex items-center gap-1.5"
                        disabled={loading === d.id}
                        onClick={() => handleReject(d.id)}
                      >
                        <XCircle size={12} />
                        Reject
                      </button>
                    </div>
                  )}

                  {d.status === 'approved' && (
                    <div className="flex items-center gap-1.5 text-emerald-500 flex-shrink-0">
                      <CheckCircle size={18} />
                      <span className="text-xs font-medium">Approved</span>
                    </div>
                  )}

                  {d.status === 'rejected' && (
                    <div className="flex items-center gap-1.5 text-red-400 flex-shrink-0">
                      <XCircle size={18} />
                      <span className="text-xs font-medium">Rejected</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
