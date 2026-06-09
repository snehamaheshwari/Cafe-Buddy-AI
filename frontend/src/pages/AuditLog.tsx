import { useState, useEffect, useCallback } from 'react'
import {
  Shield, Download, RefreshCw, Search, Filter, Activity,
  Users, AlertTriangle, CheckCircle, ChevronLeft, ChevronRight,
  Clock, User, Package,
} from 'lucide-react'
import Header from '../components/Header'
import { apiFetch } from '../utils/apiFetch'

// ─── Types ───────────────────────────────────────────────────────────────────

interface AuditEntry {
  id:          string
  timestamp:   string
  username:    string
  role:        string
  module:      string
  module_label: string
  action:      string
  description: string
  status:      'success' | 'error' | 'warning'
  ip_address:  string
  duration_ms: number | null
}

interface AuditStats {
  total_today:        number
  total_all:          number
  active_users_today: number
  most_active_module: string
  error_count:        number
  success_count:      number
  error_rate_pct:     number
  module_breakdown:   { module: string; count: number }[]
  action_breakdown:   { action: string; count: number }[]
  hourly_activity:    { hour: string; count: number }[]
}

interface Filters {
  username:  string
  module:    string
  action:    string
  status:    string
  date_from: string
  date_to:   string
  search:    string
}

const PAGE_SIZE = 25

const STATUS_STYLES: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  error:   'bg-red-50   text-red-700   border border-red-200',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200',
}

const ACTION_COLORS: Record<string, string> = {
  LOGIN:           'text-blue-600',
  LOGOUT:          'text-slate-500',
  FILE_UPLOAD:     'text-emerald-600',
  FILE_CLEAR:      'text-orange-500',
  DECISION_APPROVE:'text-emerald-600',
  DECISION_REJECT: 'text-red-500',
  ROLE_CREATE:     'text-purple-600',
  ROLE_UPDATE:     'text-purple-500',
  ROLE_DELETE:     'text-red-600',
  USER_CREATE:     'text-blue-600',
  USER_UPDATE:     'text-blue-500',
  USER_DELETE:     'text-red-600',
  PEER_ANALYSIS:   'text-teal-600',
  EXPORT:          'text-slate-600',
  AUDIT_VIEW:      'text-slate-500',
  PERMISSION_DENIED:'text-red-600',
}

const MODULES = [
  'auth', 'upload_data', 'reports', 'analytics', 'decision_engine',
  'auto_pilot', 'chatbot', 'market_radar', 'whatsapp_alerts',
  'role_management', 'audit_logs', 'system',
]

const ACTIONS = [
  'LOGIN', 'LOGOUT', 'FILE_UPLOAD', 'FILE_CLEAR',
  'DECISION_APPROVE', 'DECISION_REJECT',
  'ROLE_CREATE', 'ROLE_UPDATE', 'ROLE_DELETE',
  'USER_CREATE', 'USER_UPDATE', 'USER_DELETE',
  'PEER_ANALYSIS', 'EXPORT', 'AUDIT_VIEW', 'PERMISSION_DENIED',
]

// ─── Component ───────────────────────────────────────────────────────────────

export default function AuditLog() {
  const [entries,    setEntries]    = useState<AuditEntry[]>([])
  const [total,      setTotal]      = useState(0)
  const [page,       setPage]       = useState(0)
  const [stats,      setStats]      = useState<AuditStats | null>(null)
  const [loading,    setLoading]    = useState(false)
  const [showFilters,setShowFilters]= useState(false)
  const [filters, setFilters] = useState<Filters>({
    username: '', module: '', action: '', status: '',
    date_from: '', date_to: '', search: '',
  })

  // ── Data fetching ─────────────────────────────────────────────────────────
  const fetchLogs = useCallback(async (p = page, f = filters) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(p * PAGE_SIZE) })
      if (f.username)  params.set('username',  f.username)
      if (f.module)    params.set('module',    f.module)
      if (f.action)    params.set('action',    f.action)
      if (f.status)    params.set('status',    f.status)
      if (f.date_from) params.set('date_from', f.date_from)
      if (f.date_to)   params.set('date_to',   f.date_to)
      if (f.search)    params.set('search',    f.search)
      const res = await apiFetch(`/api/audit/logs?${params}`)
      if (res.ok) {
        const data = await res.json()
        setEntries(data.logs)
        setTotal(data.total)
      }
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [page, filters])

  const fetchStats = useCallback(async () => {
    try {
      const res = await apiFetch('/api/audit/stats')
      if (res.ok) setStats(await res.json())
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    fetchLogs(0, filters)
    fetchStats()
  }, []) // eslint-disable-line

  const applyFilters = () => {
    setPage(0)
    fetchLogs(0, filters)
  }

  const clearFilters = () => {
    const empty: Filters = { username:'', module:'', action:'', status:'', date_from:'', date_to:'', search:'' }
    setFilters(empty)
    setPage(0)
    fetchLogs(0, empty)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    fetchLogs(newPage, filters)
  }

  const handleExport = async () => {
    const params = new URLSearchParams()
    if (filters.username)  params.set('username',  filters.username)
    if (filters.module)    params.set('module',    filters.module)
    if (filters.action)    params.set('action',    filters.action)
    if (filters.status)    params.set('status',    filters.status)
    if (filters.date_from) params.set('date_from', filters.date_from)
    if (filters.date_to)   params.set('date_to',   filters.date_to)
    const res = await apiFetch(`/api/audit/export?${params}`)
    if (res.ok) {
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = 'audit_logs.csv'; a.click()
      URL.revokeObjectURL(url)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      <Header title="Audit Logs" subtitle="Full activity trail — who did what and when" />

      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-5">

        {/* ── Stats strip ── */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard icon={<Activity size={18} className="text-blue-500" />}
              label="Actions Today" value={stats.total_today} bg="bg-blue-50" />
            <StatCard icon={<Users size={18} className="text-emerald-500" />}
              label="Active Users" value={stats.active_users_today} bg="bg-emerald-50" />
            <StatCard icon={<Package size={18} className="text-purple-500" />}
              label="Most Active Module" value={stats.most_active_module} bg="bg-purple-50" />
            <StatCard icon={<AlertTriangle size={18} className="text-red-500" />}
              label="Error Rate" value={`${stats.error_rate_pct}%`} bg="bg-red-50" />
          </div>
        )}

        {/* ── Controls ── */}
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-3 mb-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search description, user, module…"
                className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
                value={filters.search}
                onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && applyFilters()}
              />
            </div>

            <button
              onClick={() => setShowFilters(v => !v)}
              className="flex items-center gap-1.5 px-3 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600"
            >
              <Filter size={14} /> Filters
              {Object.values(filters).some(Boolean) && (
                <span className="w-2 h-2 rounded-full bg-brand-500 ml-0.5" />
              )}
            </button>

            <button onClick={() => { fetchLogs(page, filters); fetchStats() }}
              className="p-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-500">
              <RefreshCw size={15} />
            </button>

            <button onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-600">
              <Download size={14} /> Export CSV
            </button>
          </div>

          {/* Expanded filters */}
          {showFilters && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 pt-3 border-t border-slate-100">
              <select className="filter-select" value={filters.module}
                onChange={e => setFilters(f => ({ ...f, module: e.target.value }))}>
                <option value="">All Modules</option>
                {MODULES.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
              </select>

              <select className="filter-select" value={filters.action}
                onChange={e => setFilters(f => ({ ...f, action: e.target.value }))}>
                <option value="">All Actions</option>
                {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>

              <select className="filter-select" value={filters.status}
                onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
                <option value="">All Status</option>
                <option value="success">Success</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
              </select>

              <input type="text" placeholder="Username" className="filter-select"
                value={filters.username}
                onChange={e => setFilters(f => ({ ...f, username: e.target.value }))} />

              <input type="date" className="filter-select" value={filters.date_from}
                onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} />

              <input type="date" className="filter-select" value={filters.date_to}
                onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} />

              <div className="col-span-full flex gap-2 justify-end">
                <button onClick={clearFilters}
                  className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600">
                  Clear filters
                </button>
                <button onClick={applyFilters}
                  className="px-3 py-1.5 text-xs bg-brand-500 text-white rounded-lg hover:bg-brand-600">
                  Apply filters
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Table ── */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Timestamp</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Module</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Action</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan={7} className="py-16 text-center text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm">Loading audit trail…</span>
                    </div>
                  </td></tr>
                ) : entries.length === 0 ? (
                  <tr><td colSpan={7} className="py-16 text-center">
                    <Shield size={40} className="text-slate-200 mx-auto mb-2" />
                    <p className="text-slate-400 text-sm">No audit entries match your filters</p>
                  </td></tr>
                ) : entries.map(e => (
                  <tr key={e.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-slate-600">
                        <Clock size={12} className="text-slate-400 flex-shrink-0" />
                        <span className="font-mono text-xs">{e.timestamp}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 text-xs font-bold uppercase">
                          {e.username.slice(0, 1)}
                        </div>
                        <div>
                          <div className="font-medium text-slate-800 text-xs">{e.username}</div>
                          {e.role && <div className="text-xs text-slate-400">{e.role}</div>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs font-medium">
                        {e.module_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`text-xs font-semibold ${ACTION_COLORS[e.action] || 'text-slate-600'}`}>
                        {e.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <p className="text-xs text-slate-600 truncate" title={e.description}>{e.description}</p>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[e.status] || STATUS_STYLES.warning}`}>
                        {e.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-slate-400">{e.ip_address || '—'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="border-t border-slate-100 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of <strong>{total}</strong> entries
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(page - 1)}
                  disabled={page === 0}
                  className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                >
                  <ChevronLeft size={14} />
                </button>
                <span className="text-xs text-slate-600">Page {page + 1} / {totalPages}</span>
                <button
                  onClick={() => handlePageChange(page + 1)}
                  disabled={page >= totalPages - 1}
                  className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Module breakdown ── */}
        {stats && stats.module_breakdown.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Activity by Module (Today)</h3>
            <div className="space-y-2">
              {stats.module_breakdown.map(m => {
                const max = stats.module_breakdown[0].count
                const pct = Math.round(m.count / max * 100)
                return (
                  <div key={m.module} className="flex items-center gap-3">
                    <span className="w-36 text-xs text-slate-600 truncate shrink-0">{m.module}</span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs font-medium text-slate-700 w-6 text-right">{m.count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

// ─── Subcomponents ────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, bg }: {
  icon: React.ReactNode; label: string; value: string | number; bg: string
}) {
  return (
    <div className={`${bg} rounded-xl p-4 flex items-start gap-3`}>
      <div className="mt-0.5 flex-shrink-0">{icon}</div>
      <div>
        <p className="text-xs text-slate-500 mb-0.5">{label}</p>
        <p className="text-lg font-bold text-slate-800">{value}</p>
      </div>
    </div>
  )
}
