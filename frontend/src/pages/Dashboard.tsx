import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  IndianRupee, ShoppingBag, TrendingUp, AlertTriangle,
  Database, Cpu, Brain, Zap, Bot, ChevronRight, Clock,
} from 'lucide-react'
import Header from '../components/Header'
import StatCard from '../components/StatCard'
import { api } from '../lib/api'

export default function Dashboard() {
  const [overview, setOverview] = useState<any>(null)
  const [chartData, setChartData] = useState<any[]>([])
  const [decisions, setDecisions] = useState<any[]>([])

  useEffect(() => {
    api.dashboard.overview().then((d: any) => setOverview(d))
    api.layer2.processedData().then((d: any) => setChartData(d.daily_sales || []))
    api.layer4.decisions().then((d: any) => setDecisions((d.decisions || []).filter((x: any) => x.status === 'pending').slice(0, 4)))
  }, [])

  const layers = [
    { id: 1, label: 'Data Collection', to: '/layer1', icon: Database, color: 'text-sky-500', bg: 'bg-sky-50', status: 'Live', statusOk: true },
    { id: 2, label: 'Data Engineering', to: '/layer2', icon: Cpu, color: 'text-violet-500', bg: 'bg-violet-50', status: '6 Pipelines', statusOk: true },
    { id: 3, label: 'AI / ML', to: '/layer3', icon: Brain, color: 'text-emerald-500', bg: 'bg-emerald-50', status: '7 Models', statusOk: true },
    { id: 4, label: 'Decision Engine', to: '/layer4', icon: Zap, color: 'text-brand-500', bg: 'bg-brand-50', status: `${overview?.pending_decisions ?? '—'} Pending`, statusOk: (overview?.pending_decisions ?? 0) > 0 },
    { id: 5, label: 'Autonomous OS', to: '/layer5', icon: Bot, color: 'text-rose-500', bg: 'bg-rose-50', status: 'Active', statusOk: true },
  ]

  const priorityBadge = (p: string) => {
    const map: Record<string, string> = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }
    return map[p] || 'badge-low'
  }

  return (
    <div>
      <Header title="Dashboard" subtitle="Cafe Buddy — AI Café Operating System" />
      <div className="p-6 space-y-6">

        {/* KPI Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Today's Revenue"
            value={overview ? `₹${overview.revenue_today.toLocaleString('en-IN')}` : '—'}
            change={overview ? `+${overview.revenue_change}%` : undefined}
            trend="up"
            icon={IndianRupee}
            iconBg="bg-brand-50"
            iconColor="text-brand-500"
          />
          <StatCard
            title="Orders Today"
            value={overview?.orders_today ?? '—'}
            change={overview ? `+${overview.orders_change}%` : undefined}
            trend="up"
            icon={ShoppingBag}
            iconBg="bg-sky-50"
            iconColor="text-sky-500"
          />
          <StatCard
            title="Avg Order Value"
            value={overview ? `₹${overview.avg_order_value}` : '—'}
            change="+4.1%"
            trend="up"
            icon={TrendingUp}
            iconBg="bg-emerald-50"
            iconColor="text-emerald-500"
          />
          <StatCard
            title="Pending Decisions"
            value={overview?.pending_decisions ?? '—'}
            change={overview?.critical_alerts ? `${overview.critical_alerts} critical` : undefined}
            trend="down"
            icon={AlertTriangle}
            iconBg="bg-red-50"
            iconColor="text-red-500"
            subtitle="Require approval"
          />
        </div>

        {/* Chart + Decisions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Revenue Trend */}
          <div className="card lg:col-span-2">
            <div className="card-header">
              <span className="card-title">Revenue Trend — Last 14 Days</span>
              <span className="text-xs text-slate-400">Processed by Data Engineering</span>
            </div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false}
                    tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(v: number) => [`₹${v.toLocaleString('en-IN')}`, 'Revenue']}
                    labelFormatter={(l) => `Date: ${l}`}
                    contentStyle={{ fontSize: 12, borderRadius: 4, border: '1px solid #e2e8f0' }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#f59e0b" strokeWidth={2}
                    fill="url(#revGrad)" dot={false} activeDot={{ r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pending Decisions */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Pending Decisions</span>
              <Link to="/layer4" className="text-xs text-brand-500 hover:underline">View all</Link>
            </div>
            <div className="divide-y divide-slate-100">
              {decisions.length === 0 && (
                <div className="p-5 text-sm text-slate-400 text-center">No pending decisions</div>
              )}
              {decisions.map((d) => (
                <div key={d.id} className="px-4 py-3">
                  <div className="flex items-start gap-2 mb-1">
                    <span className={priorityBadge(d.priority)}>{d.priority}</span>
                  </div>
                  <p className="text-xs font-medium text-slate-800 leading-snug">{d.title}</p>
                  <p className="text-xs text-emerald-600 font-medium mt-1">{d.impact}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Layer Architecture Status */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Architecture Overview — 5 Layers</span>
            <span className="text-xs text-slate-400">All layers operational</span>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-0">
              {layers.map((layer, idx) => {
                const Icon = layer.icon
                return (
                  <div key={layer.id} className="relative">
                    <Link to={layer.to}
                      className="flex flex-col items-center text-center p-4 rounded hover:bg-slate-50 transition-colors group"
                    >
                      <div className={`w-12 h-12 rounded-xl ${layer.bg} flex items-center justify-center mb-3 group-hover:scale-105 transition-transform`}>
                        <Icon size={22} className={layer.color} />
                      </div>
                      <div className="text-xs font-bold text-slate-500 mb-1">Layer {layer.id}</div>
                      <div className="text-sm font-semibold text-slate-800 leading-tight mb-2">{layer.label}</div>
                      <div className={`flex items-center gap-1 text-xs font-medium ${layer.statusOk ? 'text-emerald-600' : 'text-brand-500'}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${layer.statusOk ? 'bg-emerald-400' : 'bg-brand-400'}`} />
                        {layer.status}
                      </div>
                    </Link>
                    {idx < layers.length - 1 && (
                      <div className="hidden sm:flex absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10">
                        <ChevronRight size={16} className="text-slate-300" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* System Info Row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4 flex items-center gap-3">
            <Brain size={18} className="text-emerald-500" />
            <div>
              <div className="text-xs text-slate-500">AI Models Running</div>
              <div className="font-bold text-slate-900">{overview?.models_running ?? '—'}</div>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <Clock size={18} className="text-brand-500" />
            <div>
              <div className="text-xs text-slate-500">Top Selling Item</div>
              <div className="font-bold text-slate-900">{overview?.top_item ?? '—'}</div>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-500" />
            <div>
              <div className="text-xs text-slate-500">Critical Alerts</div>
              <div className="font-bold text-slate-900">{overview?.critical_alerts ?? '—'}</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
