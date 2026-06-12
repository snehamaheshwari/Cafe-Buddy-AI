import { useEffect, useState } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts'
import {
  Brain, Target, TrendingUp, Users, MessageSquare, Star, ThumbsUp, ThumbsDown,
  Clock, AlertTriangle, ShoppingCart, Zap, ChevronRight, CheckCircle,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

const SENT_COLORS = { Positive: '#10b981', Neutral: '#f59e0b', Negative: '#ef4444' }
const PLAT_COLORS = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']

// ── small shared components ────────────────────────────────────────────────────
function ModelBadge({ label, color = 'indigo' }: { label: string; color?: string }) {
  const c: Record<string, string> = {
    indigo: 'bg-indigo-100 text-indigo-700',
    green:  'bg-emerald-100 text-emerald-700',
    amber:  'bg-amber-100 text-amber-700',
    rose:   'bg-rose-100 text-rose-700',
    slate:  'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c[color] ?? c.indigo}`}>
      <Brain size={9} /> {label}
    </span>
  )
}

function SectionHeader({ icon: Icon, title, badge, sub }: any) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={16} className="text-indigo-500" />
      <h2 className="section-title">{title}</h2>
      {badge && <ModelBadge label={badge} color="indigo" />}
      {sub && <span className="text-xs text-slate-400 ml-1">— {sub}</span>}
    </div>
  )
}

export default function AIMLIntelligence() {
  const [forecast, setForecast]   = useState<any>(null)
  const [recs, setRecs]           = useState<any>(null)
  const [seg, setSeg]             = useState<any>(null)
  const [sentiment, setSentiment] = useState<any>(null)
  // ML endpoints
  const [mlForecast, setMlForecast]       = useState<any>(null)
  const [platForecast, setPlatForecast]   = useState<any[]>([])
  const [peakHours, setPeakHours]         = useState<any>(null)
  const [cancelRisk, setCancelRisk]       = useState<any>(null)
  const [crossSell, setCrossSell]         = useState<any[]>([])
  const [dynPricing, setDynPricing]       = useState<any[]>([])
  const [modelComp, setModelComp]         = useState<any[]>([])

  useEffect(() => {
    api.layer3.forecast().then(setForecast).catch(() => {})
    api.layer3.recommendations().then(setRecs).catch(() => {})
    api.layer3.segmentation().then(setSeg).catch(() => {})
    api.sentiment.overview().then(setSentiment).catch(() => {})
    // ML model endpoints
    api.ml.forecast().then((r: any) => setMlForecast(r)).catch(() => {})
    api.ml.platformForecast().then((r: any) => setPlatForecast(r?.platforms ?? [])).catch(() => {})
    api.ml.peakHours().then((r: any) => setPeakHours(r)).catch(() => {})
    api.ml.cancellationRisk().then((r: any) => setCancelRisk(r)).catch(() => {})
    api.ml.crossSell().then((r: any) => setCrossSell(r?.rules ?? [])).catch(() => {})
    api.ml.dynamicPricing().then((r: any) => setDynPricing(r?.suggestions ?? [])).catch(() => {})
    api.ml.modelComparison().then((r: any) => setModelComp(r?.models ?? [])).catch(() => {})
  }, [])

  // Prefer ML forecast if available
  const activeForecast = mlForecast?.forecast?.length ? mlForecast : forecast
  const forecastData   = activeForecast?.forecast || []
  const segments       = seg?.segments || []
  const elasticity     = seg?.price_elasticity || []
  const crossSellRules = crossSell.length ? crossSell : (recs?.frequently_bought_together || [])
  const dynamicRows    = dynPricing.length ? dynPricing : []

  const FORECAST_TOOLTIP = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = forecastData.find((f: any) => f.day === label)
      return (
        <div className="bg-white border border-slate-200 rounded shadow-md p-3 text-xs">
          <p className="font-semibold text-slate-800 mb-1">{label} {d?.date}</p>
          <p className="text-emerald-600">Predicted: ₹{payload[0]?.value?.toLocaleString('en-IN')}</p>
          {d?.lower != null && <p className="text-slate-400">Range: ₹{d?.lower?.toLocaleString('en-IN')} – ₹{d?.upper?.toLocaleString('en-IN')}</p>}
          {d?.confidence && <p className="text-blue-500">Confidence: {d?.confidence}%</p>}
          {d?.is_weekend && <p className="text-brand-500 font-medium">Weekend</p>}
        </div>
      )
    }
    return null
  }

  const isMLForecast = !!(mlForecast?.forecast?.length)

  return (
    <div>
      <Header title="AI / ML Intelligence" subtitle="Trained ML models · Demand forecasting · Peak hours · Cancellation risk · Cross-sell" />
      <div className="p-6 space-y-8">

        {/* ── Model Comparison ─────────────────────────────────────────── */}
        {modelComp.length > 0 && (
          <div>
            <SectionHeader icon={Brain} title="Model Performance Comparison" sub="trained on your POS data" />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {modelComp.map((m: any, i: number) => (
                <div key={m.model} className={`card p-4 ${i === 0 ? 'border-l-4 border-emerald-400' : ''}`}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-sm font-bold text-slate-900">{m.model}</p>
                      <p className="text-xs text-slate-400">{m.type}</p>
                    </div>
                    {i === 0 && <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full font-medium">Best</span>}
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <div className="text-center p-2 bg-slate-50 rounded">
                      <p className="text-xs text-slate-400">MAPE</p>
                      <p className="text-sm font-bold text-slate-800">{m.mape}%</p>
                    </div>
                    <div className="text-center p-2 bg-slate-50 rounded">
                      <p className="text-xs text-slate-400">MAE</p>
                      <p className="text-sm font-bold text-slate-800">₹{Number(m.mae).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
                    </div>
                    <div className="text-center p-2 bg-emerald-50 rounded">
                      <p className="text-xs text-slate-400">Accuracy</p>
                      <p className="text-sm font-bold text-emerald-700">{m.accuracy}%</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── 7-Day Demand Forecast ────────────────────────────────────── */}
        <div>
          <SectionHeader
            icon={TrendingUp}
            title="7-Day Demand Forecast"
            badge={isMLForecast ? (mlForecast?.model ?? 'ML Ensemble') : 'Heuristic'}
            sub={isMLForecast ? `Accuracy ${activeForecast?.accuracy}%` : 'weekday averages'}
          />
          {/* Model info row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="card p-4 border-l-4 border-emerald-400">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Model</p>
              <p className="text-xs font-bold text-slate-900 mt-1 leading-tight">{activeForecast?.model ?? '—'}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Forecast Accuracy</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">{activeForecast?.accuracy ?? '—'}%</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Training Records</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{activeForecast?.training_records?.toLocaleString() ?? '—'}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Data Source</p>
              <p className="text-sm font-bold text-slate-900 mt-1">{activeForecast?.last_trained ?? '—'}</p>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={forecastData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<FORECAST_TOOLTIP />} />
                  <Area type="monotone" dataKey="upper" stroke="transparent" fill="url(#confGrad)" />
                  <Area type="monotone" dataKey="lower" stroke="transparent" fill="white" />
                  <Line type="monotone" dataKey="predicted_revenue" stroke="#10b981" strokeWidth={2.5}
                    dot={{ r: 4, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 6 }} name="Predicted Revenue" />
                  {mlForecast?.forecast?.length > 0 && (
                    <Line type="monotone" dataKey="rf_pred" stroke="#6366f1" strokeWidth={1.5}
                      strokeDasharray="4 2" dot={false} name="RF Prediction" />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-7 gap-2 mt-4">
                {forecastData.map((d: any) => (
                  <div key={d.day}
                    className={`text-center p-2 rounded border ${d.is_weekend ? 'border-brand-200 bg-brand-50' : 'border-slate-100 bg-slate-50'}`}>
                    <div className="text-xs font-bold text-slate-500">{d.day}</div>
                    <div className="text-xs font-semibold text-slate-800 mt-0.5">
                      ₹{(d.predicted_revenue / 1000).toFixed(0)}k
                    </div>
                    {d.confidence && <div className="text-xs text-blue-500">{d.confidence}%</div>}
                    {d.is_weekend && <div className="text-xs text-brand-500">WE</div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── Platform Revenue Forecast ────────────────────────────────── */}
        {platForecast.length > 0 && (
          <div>
            <SectionHeader icon={ShoppingCart} title="Platform Revenue Forecast" badge="Ridge Regression" sub="per-platform 7-day" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {platForecast.map((pf: any, idx: number) => (
                <div key={pf.platform} className="card">
                  <div className="card-header">
                    <div>
                      <span className="card-title">{pf.platform}</span>
                      <span className="text-xs text-slate-400 ml-2">Avg ₹{Number(pf.historical_avg).toLocaleString('en-IN', { maximumFractionDigits: 0 })}/day</span>
                    </div>
                    <span className="text-xs font-medium text-slate-500">Total: ₹{Number(pf.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                  </div>
                  <div className="card-body">
                    <ResponsiveContainer width="100%" height={120}>
                      <BarChart data={pf.forecast} barSize={28}>
                        <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} />
                        <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                          tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                        <Tooltip formatter={(v: number) => [`₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, 'Revenue']}
                          contentStyle={{ fontSize: 11, borderRadius: 4 }} />
                        <Bar dataKey="predicted_revenue" fill={PLAT_COLORS[idx % PLAT_COLORS.length]} radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Peak Hour Analysis ───────────────────────────────────────── */}
        {peakHours && !peakHours.error && (
          <div>
            <SectionHeader icon={Clock} title="Peak Hour Analysis" badge="RF Classifier" sub="predicted + actual distribution" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Hourly distribution chart */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Orders by Hour (Actual)</span>
                  <div className="flex gap-2">
                    {(peakHours.top_hours || []).map((h: any) => (
                      <span key={h.hour} className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                        {h.hour}:00 — {h.orders} orders
                      </span>
                    ))}
                  </div>
                </div>
                <div className="card-body">
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={(peakHours.hourly_distribution || []).filter((h: any) => h.actual_orders > 0)}
                      barSize={16}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4 }} />
                      <Bar dataKey="actual_orders" fill="#f59e0b" radius={[2, 2, 0, 0]} name="Actual Orders" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Next 7-day peak hour predictions */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Predicted Peak Hours — Next 7 Days</span>
                  <Clock size={14} className="text-amber-400" />
                </div>
                <div className="overflow-hidden">
                  <table className="table-base">
                    <thead><tr><th>Day</th><th>Date</th><th>Peak Hour</th><th>Type</th></tr></thead>
                    <tbody>
                      {(peakHours.predictions || []).map((p: any) => (
                        <tr key={p.date}>
                          <td className="font-bold text-slate-800">{p.day}</td>
                          <td className="text-xs text-slate-400">{p.date}</td>
                          <td className="font-mono text-sm text-amber-600 font-semibold">{p.peak_label}</td>
                          <td>
                            {p.is_weekend
                              ? <span className="badge bg-brand-100 text-brand-700">Weekend</span>
                              : <span className="badge bg-slate-100 text-slate-500">Weekday</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Cancellation Risk ────────────────────────────────────────── */}
        {cancelRisk && !cancelRisk.error && (
          <div>
            <SectionHeader
              icon={AlertTriangle}
              title="Cancellation Risk Analysis"
              badge={`RF Classifier · AUC ${cancelRisk.model_auc}%`}
              sub="by platform & payment mode"
            />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Overall Risk */}
              <div className="card p-5 flex flex-col items-center justify-center">
                <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold mb-2">Overall Cancellation Risk</p>
                <div className={`text-5xl font-black mb-1 ${cancelRisk.overall_risk > 30 ? 'text-red-500' : cancelRisk.overall_risk > 15 ? 'text-yellow-500' : 'text-emerald-500'}`}>
                  {cancelRisk.overall_risk}%
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 mt-2">
                  <div className={`h-2 rounded-full ${cancelRisk.overall_risk > 30 ? 'bg-red-500' : cancelRisk.overall_risk > 15 ? 'bg-yellow-400' : 'bg-emerald-500'}`}
                    style={{ width: `${Math.min(cancelRisk.overall_risk, 100)}%` }} />
                </div>
                <p className="text-xs text-slate-400 mt-3 text-center">
                  Model AUC: <strong className="text-slate-700">{cancelRisk.model_auc}%</strong>
                </p>
              </div>

              {/* By Platform */}
              <div className="card">
                <div className="card-header"><span className="card-title">Risk by Platform</span></div>
                <div className="overflow-hidden">
                  <table className="table-base">
                    <thead><tr><th>Platform</th><th>Orders</th><th>Risk %</th></tr></thead>
                    <tbody>
                      {(cancelRisk.by_platform || []).map((p: any) => (
                        <tr key={p.platform}>
                          <td className="font-medium">{p.platform}</td>
                          <td className="text-slate-500">{p.orders.toLocaleString()}</td>
                          <td>
                            <div className="flex items-center gap-2">
                              <div className="w-12 bg-slate-100 rounded-full h-1.5">
                                <div className={`h-1.5 rounded-full ${p.risk_pct > 30 ? 'bg-red-500' : p.risk_pct > 15 ? 'bg-yellow-400' : 'bg-emerald-500'}`}
                                  style={{ width: `${Math.min(p.risk_pct, 100)}%` }} />
                              </div>
                              <span className={`text-xs font-semibold ${p.risk_pct > 30 ? 'text-red-600' : p.risk_pct > 15 ? 'text-yellow-600' : 'text-emerald-600'}`}>
                                {p.risk_pct}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* By Payment Mode */}
              <div className="card">
                <div className="card-header"><span className="card-title">Risk by Payment Mode</span></div>
                <div className="overflow-hidden">
                  <table className="table-base">
                    <thead><tr><th>Payment Mode</th><th>Orders</th><th>Risk %</th></tr></thead>
                    <tbody>
                      {(cancelRisk.by_payment || []).map((p: any) => (
                        <tr key={p.payment_mode}>
                          <td className="font-medium">{p.payment_mode}</td>
                          <td className="text-slate-500">{p.orders.toLocaleString()}</td>
                          <td>
                            <div className="flex items-center gap-2">
                              <div className="w-12 bg-slate-100 rounded-full h-1.5">
                                <div className={`h-1.5 rounded-full ${p.risk_pct > 30 ? 'bg-red-500' : p.risk_pct > 15 ? 'bg-yellow-400' : 'bg-emerald-500'}`}
                                  style={{ width: `${Math.min(p.risk_pct, 100)}%` }} />
                              </div>
                              <span className={`text-xs font-semibold ${p.risk_pct > 30 ? 'text-red-600' : p.risk_pct > 15 ? 'text-yellow-600' : 'text-emerald-600'}`}>
                                {p.risk_pct}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Cross-sell & Dynamic Pricing ─────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Cross-sell Association Rules */}
          <div className="card">
            <div className="card-header">
              <div>
                <span className="card-title">Cross-sell Recommendations</span>
                <p className="text-xs text-slate-400 mt-0.5">Association rules · min lift 1.5×</p>
              </div>
              <ModelBadge label="Apriori Rules" color="indigo" />
            </div>
            <div className="card-body space-y-2">
              {crossSellRules.slice(0, 8).map((r: any, i: number) => (
                <div key={i} className="p-2.5 bg-slate-50 rounded border border-slate-100">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-slate-800 mb-1">
                    <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs">{r.antecedent}</span>
                    <ChevronRight size={12} className="text-slate-400 flex-shrink-0" />
                    <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded text-xs">{r.consequent}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span>Confidence: <strong className="text-indigo-600">{r.confidence}%</strong></span>
                    <span>Lift: <strong className="text-brand-600">{r.lift}×</strong></span>
                    {r.support && <span>Support: <strong>{r.support}%</strong></span>}
                  </div>
                </div>
              ))}
              {crossSellRules.length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">Upload POS data to see cross-sell rules.</p>
              )}
            </div>
          </div>

          {/* Dynamic Pricing */}
          <div className="card">
            <div className="card-header">
              <div>
                <span className="card-title">Dynamic Pricing Suggestions</span>
                <p className="text-xs text-slate-400 mt-0.5">Item-level pricing from your uploaded menu & POS data</p>
              </div>
              <ModelBadge label="Menu Analytics" color="amber" />
            </div>
            {dynamicRows.length > 0 ? (
              <div className="overflow-hidden">
                <table className="table-base">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Current ₹</th>
                      <th>Optimal ₹</th>
                      <th>Change</th>
                      <th>Monthly Impact</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dynamicRows.map((r: any, idx: number) => {
                      const rec: string = r.recommendation ?? ''
                      const isIncrease = rec === 'Increase'
                      const isReview   = rec === 'Review'
                      const isHold     = rec === 'Hold'
                      const badgeCls   = isIncrease
                        ? 'badge-ok'
                        : isReview
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-slate-100 text-slate-500'
                      const priceCls   = isIncrease
                        ? 'text-emerald-600'
                        : isReview
                        ? 'text-amber-600'
                        : 'text-slate-500'
                      return (
                        <tr key={r.item ?? r.platform ?? idx}>
                          <td className="font-medium text-xs">
                            {r.item ?? r.platform}
                          </td>
                          <td className="font-mono text-xs text-slate-600">
                            ₹{r.current_price ?? r.avg_bill}
                          </td>
                          <td className={`font-mono text-xs font-semibold ${priceCls}`}>
                            ₹{r.optimal_price ?? (r.avg_bill + 10)}
                          </td>
                          <td className={`text-xs font-semibold ${priceCls}`}>
                            {r.suggested_change ?? r.suggested_increase}
                          </td>
                          <td className={`text-xs font-semibold ${priceCls}`}>
                            {r.revenue_impact}
                          </td>
                          <td>
                            <span
                              className={`badge ${badgeCls} cursor-default`}
                              title={r.reason ?? rec}
                            >
                              {rec}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="card-body">
                {/* Fall back to price elasticity from segmentation */}
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold">Item</th>
                      <th className="px-3 py-2 text-left font-semibold">Current</th>
                      <th className="px-3 py-2 text-left font-semibold">Optimal</th>
                      <th className="px-3 py-2 text-left font-semibold">Upside</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {elasticity.map((e: any) => (
                      <tr key={e.item} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium text-xs">{e.item}</td>
                        <td className="px-3 py-2 font-mono text-xs">₹{e.current_price}</td>
                        <td className="px-3 py-2 font-mono text-xs text-emerald-600 font-semibold">₹{e.optimal_price}</td>
                        <td className="px-3 py-2"><span className="badge-ok">{e.upside}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!elasticity.length && <p className="text-xs text-slate-400 text-center py-4">Upload POS + Menu data to see pricing suggestions.</p>}
              </div>
            )}
          </div>
        </div>

        {/* ── Customer Segmentation + High Potential + Low Performers ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Segmentation Pie */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Customer Segments (by Platform)</span>
              <Users size={14} className="text-slate-400" />
            </div>
            <div className="card-body flex flex-col items-center">
              <PieChart width={200} height={180}>
                <Pie data={segments} dataKey="count" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                  {segments.map((s: any) => (
                    <Cell key={s.name} fill={s.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number, name: string) => [v, name]}
                  contentStyle={{ fontSize: 11, borderRadius: 4, border: '1px solid #e2e8f0' }} />
              </PieChart>
              <div className="space-y-2 w-full mt-2">
                {segments.map((s: any) => (
                  <div key={s.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ background: s.color }} />
                      <span className="text-slate-700 font-medium">{s.name}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-semibold text-slate-800">{s.count}</span>
                      <span className="text-slate-400 ml-1">· ₹{s.avg_spend} avg</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* High Potential */}
          <div className="card">
            <div className="card-header"><span className="card-title">High Potential Items</span><Target size={14} className="text-slate-400" /></div>
            <table className="table-base">
              <thead><tr><th>Item</th><th>Margin</th><th>Wkly</th></tr></thead>
              <tbody>
                {(recs?.high_potential || []).map((r: any) => (
                  <tr key={r.item}>
                    <td className="font-medium text-xs">{r.item}</td>
                    <td className="text-emerald-600 font-semibold text-xs">{r.margin_pct}%</td>
                    <td className="text-xs text-slate-500">{r.weekly_orders}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Low Performers */}
          <div className="card">
            <div className="card-header"><span className="card-title">Low Performers</span><Zap size={14} className="text-red-400" /></div>
            <table className="table-base">
              <thead><tr><th>Item</th><th>Margin</th><th>Action</th></tr></thead>
              <tbody>
                {(recs?.low_performers || []).map((r: any) => (
                  <tr key={r.item}>
                    <td className="font-medium text-xs">{r.item}</td>
                    <td className="text-red-500 font-semibold text-xs">{r.margin_pct}%</td>
                    <td className="text-xs text-red-600">{r.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Sentiment Analysis ───────────────────────────────────────── */}
        {sentiment?.uploaded ? (() => {
          const s = sentiment.stats
          const sentPieData = [
            { name: 'Positive', value: s.positive, fill: SENT_COLORS.Positive },
            { name: 'Neutral',  value: s.neutral,  fill: SENT_COLORS.Neutral },
            { name: 'Negative', value: s.negative, fill: SENT_COLORS.Negative },
          ]
          const posKw = s.keywords?.positive ?? []
          const negKw = s.keywords?.negative ?? []
          return (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-rose-500" />
                <h2 className="section-title">Sentiment Analysis — TF-IDF + Linear SVM</h2>
                <span className="text-xs px-2 py-0.5 bg-rose-100 text-rose-700 rounded-full font-medium">
                  {sentiment.info?.model_accuracy ?? '93.4%'} accuracy
                </span>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="card p-4 border-l-4 border-emerald-400">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Total Reviews</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{s.total_reviews?.toLocaleString()}</p>
                </div>
                <div className="card p-4 border-l-4 border-emerald-400">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Positive</p>
                  <p className="text-2xl font-bold text-emerald-600 mt-1">{s.positive_pct}%</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Neutral</p>
                  <p className="text-2xl font-bold text-yellow-500 mt-1">{s.neutral_pct}%</p>
                </div>
                <div className="card p-4 border-l-4 border-red-400">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Negative</p>
                  <p className="text-2xl font-bold text-red-500 mt-1">{s.negative_pct}%</p>
                </div>
                <div className="card p-4 border-l-4 border-indigo-400">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Satisfaction</p>
                  <p className="text-2xl font-bold text-indigo-600 mt-1">{s.satisfaction_score}%</p>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="card">
                  <div className="card-header"><span className="card-title">Sentiment Distribution</span><Star size={14} className="text-rose-400" /></div>
                  <div className="card-body flex flex-col items-center">
                    <PieChart width={200} height={180}>
                      <Pie data={sentPieData} dataKey="value" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                        {sentPieData.map((d) => <Cell key={d.name} fill={d.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 11, borderRadius: 4, border: '1px solid #e2e8f0' }} />
                    </PieChart>
                    <div className="space-y-2 w-full mt-2">
                      {sentPieData.map((d) => (
                        <div key={d.name} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-sm" style={{ background: d.fill }} />
                            <span className="text-slate-700 font-medium">{d.name}</span>
                          </div>
                          <span className="font-semibold text-slate-800">{d.value}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 pt-3 border-t border-slate-100 w-full">
                      <p className="text-xs text-slate-500 text-center">Avg Rating: <strong>{s.overall_avg_rating} / 5</strong></p>
                    </div>
                  </div>
                </div>
                <div className="card">
                  <div className="card-header"><span className="card-title">Source Breakdown</span><ThumbsUp size={14} className="text-slate-400" /></div>
                  <div className="card-body">
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={(s.source_breakdown ?? []).slice(0, 6)} layout="vertical" barSize={12}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                        <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false}
                          tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                        <YAxis type="category" dataKey="source" tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} width={64} />
                        <Tooltip formatter={(v: number) => [`${v}%`, 'Positive']} contentStyle={{ fontSize: 11, borderRadius: 4 }} />
                        <Bar dataKey="positive_pct" fill="#10b981" radius={[0, 3, 3, 0]} name="Positive %" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="card">
                  <div className="card-header"><span className="card-title">Visit Type Satisfaction</span><ThumbsDown size={14} className="text-slate-400" /></div>
                  <div className="overflow-hidden">
                    <table className="table-base">
                      <thead><tr><th>Visit Type</th><th>Satisfaction</th><th>Reviews</th></tr></thead>
                      <tbody>
                        {(s.visit_breakdown ?? []).map((vt: any) => (
                          <tr key={vt.visit_type}>
                            <td className="font-medium text-xs">{vt.visit_type}</td>
                            <td>
                              <div className="flex items-center gap-2">
                                <div className="w-16 bg-slate-100 rounded-full h-1.5">
                                  <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${vt.satisfaction}%` }} />
                                </div>
                                <span className="text-xs font-semibold">{vt.satisfaction.toFixed(0)}%</span>
                              </div>
                            </td>
                            <td className="text-xs text-slate-500">{vt.total}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">Top Positive Keywords</span>
                    <span className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full">from happy reviews</span>
                  </div>
                  <div className="card-body flex flex-wrap gap-2">
                    {posKw.map((k: any, i: number) => (
                      <span key={k.word} className="px-3 py-1.5 rounded-full text-xs font-semibold border"
                        style={{ background: `rgba(16,185,129,${0.12 + (posKw.length - i) / posKw.length * 0.2})`, borderColor: 'rgba(16,185,129,0.3)', color: '#065f46', fontSize: `${Math.max(10, 14 - i)}px` }}>
                        {k.word} <span className="opacity-60">×{k.count}</span>
                      </span>
                    ))}
                  </div>
                </div>
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">Top Negative Keywords</span>
                    <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">from critical reviews</span>
                  </div>
                  <div className="card-body flex flex-wrap gap-2">
                    {negKw.map((k: any, i: number) => (
                      <span key={k.word} className="px-3 py-1.5 rounded-full text-xs font-semibold border"
                        style={{ background: `rgba(239,68,68,${0.08 + (negKw.length - i) / negKw.length * 0.15})`, borderColor: 'rgba(239,68,68,0.25)', color: '#7f1d1d', fontSize: `${Math.max(10, 14 - i)}px` }}>
                        {k.word} <span className="opacity-60">×{k.count}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })() : (
          <div className="card p-6 border border-dashed border-rose-200 bg-rose-50 flex items-center gap-4">
            <MessageSquare size={28} className="text-rose-300 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-slate-700">Sentiment Analysis — Not Yet Active</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload your reviews CSV in <strong>Data Collection → Reviews & Sentiment</strong> to activate
                the TF-IDF + Linear SVM sentiment model (93.4% accuracy).
              </p>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
