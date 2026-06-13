import { useEffect, useState } from 'react'
import { Bot, CheckCircle, Clock, AlertTriangle, TrendingUp, TrendingDown, Activity } from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

const ACTION_STYLE: Record<string, { border: string; badge: string; icon: JSX.Element }> = {
  auto_executed: {
    border: 'border-emerald-200 bg-emerald-50',
    badge: 'badge bg-emerald-100 text-emerald-700',
    icon: <CheckCircle size={16} className="text-emerald-500" />,
  },
  scheduled: {
    border: 'border-blue-200 bg-blue-50',
    badge: 'badge bg-blue-100 text-blue-700',
    icon: <Clock size={16} className="text-blue-500" />,
  },
  alert: {
    border: 'border-red-200 bg-red-50',
    badge: 'badge bg-red-100 text-red-700',
    icon: <AlertTriangle size={16} className="text-red-500" />,
  },
}

const ACTION_LABEL: Record<string, string> = {
  auto_executed: 'Auto-Executed',
  scheduled: 'Scheduled',
  alert: 'Alert → Action',
}

export default function CafeOS() {
  const [autonomous, setAutonomous] = useState<any>(null)
  const [kpiData, setKpiData] = useState<any>(null)

  useEffect(() => {
    api.layer5.autonomousActions().then(setAutonomous)
    api.layer5.kpis().then(setKpiData)
  }, [])

  const health = autonomous?.system_health
  const actions = autonomous?.actions || []
  const kpis = kpiData?.kpis || []

  return (
    <div>
      <Header title="AI-Powered Execution" subtitle="Approved decisions are executed automatically. All actions logged." />
      <div className="p-6 space-y-6">

        {/* System Health */}
        <div className="card border-l-4 border-rose-400">
          <div className="card-body">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded bg-rose-100 flex items-center justify-center">
                <Bot size={16} className="text-rose-500" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">Autonomous System — Health Dashboard</h2>
                <p className="text-xs text-slate-400">Live AI decision engine status</p>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-medium text-emerald-600">Operational · {health?.uptime}</span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded border border-slate-200 p-3 text-center">
                <div className="text-2xl font-bold text-rose-500">{health?.models_active ?? 0}</div>
                <div className="text-xs text-slate-500 mt-0.5">Active AI Models</div>
                <div className="text-xs text-slate-400 mt-1">XGBoost · Apriori · Sentiment · Pricing · Peak · Popularity</div>
              </div>
              <div className="bg-white rounded border border-slate-200 p-3 text-center">
                <div className="text-2xl font-bold text-slate-900">{health?.decisions_automated_today ?? 0}</div>
                <div className="text-xs text-slate-500 mt-0.5">Decisions Approved Today</div>
                <div className="text-xs text-slate-400 mt-1">Approved in What To Do Next</div>
              </div>
              <div className="bg-white rounded border border-slate-200 p-3 text-center">
                <div className="text-2xl font-bold text-amber-500">{health?.alerts_fired ?? 0}</div>
                <div className="text-xs text-slate-500 mt-0.5">Pending Recommendations</div>
                <div className="text-xs text-slate-400 mt-1">Awaiting approval in Decision Engine</div>
              </div>
            </div>
          </div>
        </div>

        {/* KPI Grid */}
        <div>
          <h2 className="section-title mb-3">Live KPI Metrics</h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {kpis.map((kpi: any) => (
              <div key={kpi.name} className="card p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{kpi.name}</p>
                    <p className="text-2xl font-bold text-slate-900 mt-1">{kpi.value}</p>
                  </div>
                  <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded ${
                    kpi.trend === 'up' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
                  }`}>
                    {kpi.trend === 'up' ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                    {kpi.change}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Autonomous Actions Feed */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-rose-500" />
              <span className="card-title">Autonomous Actions Feed</span>
            </div>
            <span className="text-xs text-slate-400">Decisions you approved in <strong>What To Do Next</strong> appear here automatically</span>
          </div>
          <div className="card-body space-y-3">
            {actions.map((action: any) => {
              const style = ACTION_STYLE[action.type] || ACTION_STYLE.alert
              return (
                <div key={action.id} className={`border rounded p-4 ${style.border}`}>
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">{style.icon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className={style.badge}>{ACTION_LABEL[action.type]}</span>
                        <span className="badge bg-slate-100 text-slate-500 font-mono text-xs">{action.trigger}</span>
                        <span className={`badge ${
                          action.status === 'completed' ? 'badge-ok' :
                          action.status === 'scheduled' ? 'badge-pending' : 'badge-high'
                        }`}>{action.status}</span>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-900 leading-snug mb-1">{action.title}</h4>
                      <p className="text-xs text-slate-500 mb-2">{action.detail}</p>
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1 text-slate-400">
                          <Clock size={11} />
                          {action.executed_at}
                        </div>
                        <div className="flex items-center gap-1 text-emerald-600 font-medium">
                          <TrendingUp size={11} />
                          {action.impact}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Autonomous Actions Feed — Logic Explanation */}
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-800 leading-relaxed space-y-1.5">
          <p className="font-semibold text-emerald-900">Where does the Autonomous Actions Feed come from?</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
            <div>
              <p className="font-medium mb-0.5">✅ Source 1 — Your approved decisions</p>
              <p>Every decision you click <strong>Approve</strong> on in <em>What To Do Next</em> is stored in an in-memory override table. The feed reads that table and surfaces each approved item here with status <em>"completed"</em> and trigger <em>"User Approved — Decision Engine"</em>.</p>
            </div>
            <div>
              <p className="font-medium mb-0.5">🤖 Source 2 — ML model actions</p>
              <p>The XGBoost demand-forecast and price-optimisation models (from <code className="bg-emerald-100 px-1 rounded">cafe_os_models.py</code>) independently generate price-rise / daypart / weekend-variance alerts. These appear in the feed automatically when pre-trained model files are present — no approval required.</p>
            </div>
          </div>
          <p className="text-emerald-700">⚠️ <strong>Note:</strong> Approved decisions reset when a new data file is uploaded or the server restarts, because overrides are stored in memory (not persisted to disk). Re-approve decisions after uploading fresh POS data.</p>
        </div>

        {/* How It Works */}
        <div className="card">
          <div className="card-header"><span className="card-title">How AI-Powered Execution Works</span></div>
          <div className="card-body">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center text-sm">
              <div className="space-y-2">
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mx-auto">
                  <Activity size={20} className="text-blue-500" />
                </div>
                <div className="font-semibold text-slate-800">Sense</div>
                <p className="text-xs text-slate-500">AI continuously monitors all data streams — POS, inventory, weather, delivery platforms, customer sentiment.</p>
              </div>
              <div className="space-y-2">
                <div className="w-12 h-12 rounded-full bg-brand-100 flex items-center justify-center mx-auto">
                  <Bot size={20} className="text-brand-500" />
                </div>
                <div className="font-semibold text-slate-800">Decide</div>
                <p className="text-xs text-slate-500">Decision Engine generates AI recommendations. When you approve them in 'What To Do Next', they execute here automatically.</p>
              </div>
              <div className="space-y-2">
                <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto">
                  <CheckCircle size={20} className="text-emerald-500" />
                </div>
                <div className="font-semibold text-slate-800">Act & Learn</div>
                <p className="text-xs text-slate-500">Actions are executed (or queued for approval), outcomes are logged, and models retrain on new data.</p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
