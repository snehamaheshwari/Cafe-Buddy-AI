import { useEffect, useState } from 'react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { Brain, Target, TrendingUp, Users } from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

export default function AIMLIntelligence() {
  const [forecast, setForecast] = useState<any>(null)
  const [recs, setRecs] = useState<any>(null)
  const [seg, setSeg] = useState<any>(null)

  useEffect(() => {
    api.layer3.forecast().then(setForecast)
    api.layer3.recommendations().then(setRecs)
    api.layer3.segmentation().then(setSeg)
  }, [])

  const forecastData = forecast?.forecast || []
  const segments = seg?.segments || []
  const elasticity = seg?.price_elasticity || []

  const CUSTOM_TOOLTIP = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const d = forecastData.find((f: any) => f.day === label)
      return (
        <div className="bg-white border border-slate-200 rounded shadow-md p-3 text-xs">
          <p className="font-semibold text-slate-800 mb-1">{label} {d?.date}</p>
          <p className="text-emerald-600">Predicted: ₹{payload[0]?.value?.toLocaleString('en-IN')}</p>
          <p className="text-slate-400">Range: ₹{d?.lower?.toLocaleString('en-IN')} – ₹{d?.upper?.toLocaleString('en-IN')}</p>
          <p className="text-blue-500">Confidence: {d?.confidence}%</p>
          {d?.is_weekend && <p className="text-brand-500 font-medium">Weekend</p>}
          {d?.weather === 'Rainy' && <p className="text-sky-500">🌧 Rainy day</p>}
        </div>
      )
    }
    return null
  }

  return (
    <div>
      <Header title="AI / ML Intelligence" subtitle="Demand forecasting, product recommendations, and customer segmentation models" />
      <div className="p-6 space-y-6">

        {/* Model Info Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4 border-l-4 border-emerald-400">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Model</p>
            <p className="text-sm font-bold text-slate-900 mt-1">{forecast?.model ?? '—'}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Forecast Accuracy</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{forecast?.accuracy ?? '—'}%</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Training Records</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{forecast?.training_records?.toLocaleString() ?? '—'}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Last Trained</p>
            <p className="text-lg font-bold text-slate-900 mt-1">{forecast?.last_trained ?? '—'}</p>
          </div>
        </div>

        {/* Demand Forecast Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <span className="card-title">7-Day Demand Forecast</span>
              <p className="text-xs text-slate-400 mt-0.5">Shaded area = 92% confidence interval</p>
            </div>
            <Brain size={16} className="text-emerald-500" />
          </div>
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
                <Tooltip content={<CUSTOM_TOOLTIP />} />
                <Area type="monotone" dataKey="upper" stroke="transparent" fill="url(#confGrad)" />
                <Area type="monotone" dataKey="lower" stroke="transparent" fill="white" />
                <Line type="monotone" dataKey="predicted_revenue" stroke="#10b981" strokeWidth={2.5}
                  dot={{ r: 4, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
                  activeDot={{ r: 6 }} name="Predicted Revenue" />
              </ComposedChart>
            </ResponsiveContainer>

            {/* Day Cards */}
            <div className="grid grid-cols-7 gap-2 mt-4">
              {forecastData.map((d: any) => (
                <div key={d.day}
                  className={`text-center p-2 rounded border ${d.is_weekend ? 'border-brand-200 bg-brand-50' : 'border-slate-100 bg-slate-50'}`}>
                  <div className="text-xs font-bold text-slate-500">{d.day}</div>
                  <div className="text-xs font-semibold text-slate-800 mt-0.5">
                    ₹{(d.predicted_revenue / 1000).toFixed(0)}k
                  </div>
                  <div className="text-xs text-blue-500">{d.confidence}%</div>
                  {d.weather === 'Rainy' && <div className="text-xs">🌧</div>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Segmentation + Elasticity + Affinity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Customer Segmentation Pie */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Customer Segments</span>
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

          {/* Price Elasticity */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Price Elasticity</span>
              <Target size={14} className="text-slate-400" />
            </div>
            <div className="overflow-hidden">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Current</th>
                    <th>Optimal</th>
                    <th>Upside</th>
                  </tr>
                </thead>
                <tbody>
                  {elasticity.map((e: any) => (
                    <tr key={e.item}>
                      <td className="font-medium text-xs">{e.item}</td>
                      <td className="font-mono text-xs">₹{e.current_price}</td>
                      <td className="font-mono text-xs text-emerald-600 font-semibold">₹{e.optimal_price}</td>
                      <td><span className="badge-ok">{e.upside}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Product Affinity */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Product Affinity</span>
              <TrendingUp size={14} className="text-slate-400" />
            </div>
            <div className="card-body space-y-3">
              {(recs?.frequently_bought_together || []).map((r: any, i: number) => (
                <div key={i} className="p-3 bg-slate-50 rounded border border-slate-100">
                  <div className="flex items-center gap-2 text-xs font-medium text-slate-800 mb-1.5">
                    <span>{r.items[0]}</span>
                    <span className="text-slate-400">+</span>
                    <span>{r.items[1]}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <div className="flex items-center gap-3">
                      <span>Conf: <strong className="text-indigo-600">{r.confidence}%</strong></span>
                      <span>Lift: <strong className="text-brand-600">{r.lift}×</strong></span>
                    </div>
                    <span>{r.orders} orders</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* High Potential + Low Performers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card">
            <div className="card-header"><span className="card-title">High Potential Items</span></div>
            <table className="table-base">
              <thead><tr><th>Item</th><th>Margin</th><th>Weekly Orders</th><th>Recommendation</th></tr></thead>
              <tbody>
                {(recs?.high_potential || []).map((r: any) => (
                  <tr key={r.item}>
                    <td className="font-medium">{r.item}</td>
                    <td className="text-emerald-600 font-semibold">{r.margin_pct}%</td>
                    <td>{r.weekly_orders}</td>
                    <td className="text-xs text-emerald-700">{r.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">Low Performers</span></div>
            <table className="table-base">
              <thead><tr><th>Item</th><th>Margin</th><th>Weekly Orders</th><th>Recommendation</th></tr></thead>
              <tbody>
                {(recs?.low_performers || []).map((r: any) => (
                  <tr key={r.item}>
                    <td className="font-medium">{r.item}</td>
                    <td className="text-red-500 font-semibold">{r.margin_pct}%</td>
                    <td>{r.weekly_orders}</td>
                    <td className="text-xs text-red-600">{r.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  )
}
