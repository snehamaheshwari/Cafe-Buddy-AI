import { useEffect, useState } from 'react'
import {
  Search, Star, TrendingUp, Users, Clock,
  MapPin, Zap, RefreshCw, ChevronDown, Award, AlertTriangle, Target,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────
interface Competitor {
  name: string
  area: string
  city: string
  rating: number
  review_count: number
  avg_order_value: number
  price_band: string
  specialties: string[]
  positive_themes: string[]
  negative_themes: string[]
  delivery_time_min: number
  platforms: string[]
  seating_capacity: number
  years_active: number
  notable: string
  menu_variety_score: number
  value_score: number
  radar_scores?: RadarScores
}

interface RadarScores {
  rating: number
  price_competitiveness: number
  delivery_speed: number
  menu_variety: number
  popularity: number
  value_for_money: number
}

// ─────────────────────────────────────────────
// RADAR CHART — pure SVG, no external lib
// ─────────────────────────────────────────────
const RADAR_AXES = [
  { key: 'rating',                label: 'Rating' },
  { key: 'price_competitiveness', label: 'Price' },
  { key: 'delivery_speed',        label: 'Delivery' },
  { key: 'menu_variety',          label: 'Menu' },
  { key: 'popularity',            label: 'Popularity' },
  { key: 'value_for_money',       label: 'Value' },
]

const RADAR_COLORS = [
  { stroke: '#6366f1', fill: 'rgba(99,102,241,0.15)' },   // indigo
  { stroke: '#f59e0b', fill: 'rgba(245,158,11,0.15)' },   // amber
  { stroke: '#10b981', fill: 'rgba(16,185,129,0.15)' },   // emerald
  { stroke: '#ef4444', fill: 'rgba(239,68,68,0.15)' },    // red
]

const OUR_COLOR = { stroke: '#8b5cf6', fill: 'rgba(139,92,246,0.20)' }

function polarToXY(angle: number, r: number, cx: number, cy: number) {
  const rad = (angle - 90) * (Math.PI / 180)
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function scoreToPath(scores: RadarScores | undefined, cx: number, cy: number, maxR: number): string {
  if (!scores) return ''
  const values = RADAR_AXES.map(a => (scores[a.key as keyof RadarScores] ?? 0) / 100)
  const n = values.length
  return values
    .map((v, i) => {
      const angle = (360 / n) * i
      const { x, y } = polarToXY(angle, v * maxR, cx, cy)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ') + ' Z'
}

interface RadarChartProps {
  competitors: Competitor[]
  ourScores?: RadarScores
}

function RadarChart({ competitors, ourScores }: RadarChartProps) {
  const size = 300
  const cx = size / 2
  const cy = size / 2
  const maxR = 110
  const n = RADAR_AXES.length
  const rings = [0.25, 0.5, 0.75, 1.0]
  const topComps = competitors.slice(0, 3)

  // Axis endpoints
  const axisPoints = RADAR_AXES.map((_, i) => polarToXY((360 / n) * i, maxR, cx, cy))

  if (competitors.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        Select a city &amp; area to view the radar chart
      </div>
    )
  }

  return (
    <div>
      <svg width={size} height={size} className="mx-auto">
        {/* Ring grid */}
        {rings.map(r => {
          const pts = RADAR_AXES
            .map((_, i) => polarToXY((360 / n) * i, r * maxR, cx, cy))
            .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
            .join(' ') + ' Z'
          return (
            <path
              key={r}
              d={pts}
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="1"
            />
          )
        })}

        {/* Axis spokes */}
        {axisPoints.map((pt, i) => (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={pt.x}
            y2={pt.y}
            stroke="#e2e8f0"
            strokeWidth="1"
          />
        ))}

        {/* Competitor polygons */}
        {topComps.map((comp, ci) => {
          const path = scoreToPath(comp.radar_scores, cx, cy, maxR)
          const col = RADAR_COLORS[ci]
          return (
            <g key={comp.name}>
              <path d={path} fill={col.fill} stroke={col.stroke} strokeWidth="2" strokeLinejoin="round" />
            </g>
          )
        })}

        {/* Our café polygon */}
        {ourScores && (
          <path
            d={scoreToPath(ourScores, cx, cy, maxR)}
            fill={OUR_COLOR.fill}
            stroke={OUR_COLOR.stroke}
            strokeWidth="2.5"
            strokeDasharray="6 3"
            strokeLinejoin="round"
          />
        )}

        {/* Axis labels */}
        {RADAR_AXES.map((axis, i) => {
          const labelR = maxR + 18
          const { x, y } = polarToXY((360 / n) * i, labelR, cx, cy)
          const anchor =
            x < cx - 5 ? 'end' :
            x > cx + 5 ? 'start' : 'middle'
          return (
            <text
              key={axis.key}
              x={x}
              y={y + 4}
              textAnchor={anchor}
              fontSize="10"
              fill="#64748b"
              fontWeight="600"
            >
              {axis.label}
            </text>
          )
        })}

        {/* Ring % labels */}
        {rings.map(r => {
          const { x, y } = polarToXY(0, r * maxR, cx, cy)
          return (
            <text key={r} x={x + 3} y={y} fontSize="8" fill="#94a3b8">
              {Math.round(r * 100)}
            </text>
          )
        })}
      </svg>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 justify-center">
        {topComps.map((comp, ci) => (
          <div key={comp.name} className="flex items-center gap-1.5 text-xs text-slate-600">
            <span
              className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: RADAR_COLORS[ci].stroke }}
            />
            <span className="truncate max-w-[120px]" title={comp.name}>{comp.name}</span>
          </div>
        ))}
        {ourScores && (
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <span
              className="inline-block w-3 h-3 rounded-sm flex-shrink-0 border-2"
              style={{ borderColor: OUR_COLOR.stroke, borderStyle: 'dashed' }}
            />
            <span className="font-semibold text-purple-600">Our Café</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// STAR RATING DISPLAY
// ─────────────────────────────────────────────
function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(s => (
        <Star
          key={s}
          size={12}
          className={
            s <= Math.floor(rating)
              ? 'text-amber-400 fill-amber-400'
              : s - 0.5 <= rating
              ? 'text-amber-400 fill-amber-200'
              : 'text-slate-300 fill-slate-100'
          }
        />
      ))}
      <span className="text-xs font-semibold text-slate-700 ml-1">{rating.toFixed(1)}</span>
    </div>
  )
}

// ─────────────────────────────────────────────
// PRICE BAND BADGE
// ─────────────────────────────────────────────
function PriceBadge({ band }: { band: string }) {
  const cls =
    band === '₹'
      ? 'bg-green-100 text-green-700 border border-green-200'
      : band === '₹₹'
      ? 'bg-yellow-100 text-yellow-700 border border-yellow-200'
      : 'bg-orange-100 text-orange-700 border border-orange-200'
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${cls}`}>{band}</span>
  )
}

// ─────────────────────────────────────────────
// AI ANALYSIS — markdown-style rendering
// ─────────────────────────────────────────────
function AnalysisText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-1 text-sm text-slate-700 leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return (
            <h3 key={i} className="text-slate-900 font-bold text-base mt-4 mb-1 first:mt-0">
              {line.replace('## ', '')}
            </h3>
          )
        }
        if (line.match(/^\d+\. /)) {
          return (
            <p key={i} className="pl-2 flex gap-2">
              <span className="text-brand-500 font-bold flex-shrink-0">
                {line.match(/^\d+/)?.[0]}.
              </span>
              <span>{line.replace(/^\d+\. /, '')}</span>
            </p>
          )
        }
        if (line.startsWith('- ') || line.startsWith('• ')) {
          return (
            <p key={i} className="pl-2 flex gap-2">
              <span className="text-slate-400 flex-shrink-0">•</span>
              <span>{line.replace(/^[-•] /, '')}</span>
            </p>
          )
        }
        if (line.trim() === '') return <div key={i} className="h-1" />
        return <p key={i}>{line}</p>
      })}
    </div>
  )
}

// ─────────────────────────────────────────────
// COMPETITOR CARD
// ─────────────────────────────────────────────
function CompetitorCard({ comp }: { comp: Competitor }) {
  return (
    <div className="card p-5 flex flex-col gap-3 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-slate-900 font-bold text-base leading-tight truncate" title={comp.name}>
            {comp.name}
          </h3>
          <div className="flex items-center gap-1 mt-0.5">
            <MapPin size={11} className="text-slate-400 flex-shrink-0" />
            <span className="text-xs text-slate-500 truncate">{comp.area}, {comp.city}</span>
          </div>
        </div>
        <PriceBadge band={comp.price_band} />
      </div>

      {/* Rating */}
      <div className="flex items-center justify-between">
        <StarRating rating={comp.rating} />
        <span className="text-xs text-slate-500">{comp.review_count.toLocaleString('en-IN')} reviews</span>
      </div>

      {/* Specialties */}
      {comp.specialties.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {comp.specialties.map(s => (
            <span
              key={s}
              className="inline-block px-2 py-0.5 rounded-full text-xs bg-brand-50 text-brand-700 border border-brand-100"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-2 bg-slate-50 rounded-lg p-2.5">
        <div className="text-center">
          <div className="text-slate-900 font-bold text-sm">₹{comp.avg_order_value}</div>
          <div className="text-slate-500 text-xs mt-0.5">Avg Order</div>
        </div>
        <div className="text-center border-x border-slate-200">
          <div className="text-slate-900 font-bold text-sm flex items-center justify-center gap-0.5">
            <Clock size={11} className="text-slate-400" />
            {comp.delivery_time_min === 0 ? '—' : `${comp.delivery_time_min}m`}
          </div>
          <div className="text-slate-500 text-xs mt-0.5">Delivery</div>
        </div>
        <div className="text-center">
          <div className="text-slate-900 font-bold text-sm flex items-center justify-center gap-0.5">
            <Users size={11} className="text-slate-400" />
            {comp.seating_capacity}
          </div>
          <div className="text-slate-500 text-xs mt-0.5">Seats</div>
        </div>
      </div>

      {/* Themes */}
      <div className="space-y-1.5">
        <div className="flex flex-wrap gap-1">
          {comp.positive_themes.slice(0, 2).map(t => (
            <span key={t} className="inline-block px-2 py-0.5 rounded-full text-xs bg-green-50 text-green-700 border border-green-100">
              + {t}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {comp.negative_themes.slice(0, 2).map(t => (
            <span key={t} className="inline-block px-2 py-0.5 rounded-full text-xs bg-red-50 text-red-700 border border-red-100">
              − {t}
            </span>
          ))}
        </div>
      </div>

      {/* Notable */}
      {comp.notable && (
        <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
          <p className="text-xs text-amber-800 leading-snug">{comp.notable}</p>
        </div>
      )}

      {/* Platforms */}
      <div className="flex flex-wrap gap-1 pt-0.5">
        {comp.platforms.map(p => (
          <span
            key={p}
            className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
              p === 'Zomato'
                ? 'bg-red-100 text-red-600'
                : p === 'Swiggy'
                ? 'bg-orange-100 text-orange-600'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {p}
          </span>
        ))}
        <span className="text-xs text-slate-400 ml-auto">{comp.years_active}y active</span>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────
export default function PeerComparison() {
  const [cities, setCities] = useState<string[]>([])
  const [areas, setAreas] = useState<string[]>([])
  const [selectedCity, setSelectedCity] = useState('Delhi NCR')
  const [selectedArea, setSelectedArea] = useState('Connaught Place')
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [analysis, setAnalysis] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  // ── Fetch cities on mount ──
  useEffect(() => {
    api.peers.cities().then((res: any) => {
      setCities(res.cities ?? [])
    }).catch(() => {})
  }, [])

  // ── Fetch areas when city changes ──
  useEffect(() => {
    if (!selectedCity) return
    api.peers.areas(selectedCity).then((res: any) => {
      const newAreas: string[] = res.areas ?? []
      setAreas(newAreas)
      if (newAreas.length > 0) {
        setSelectedArea(newAreas[0])
      }
    }).catch(() => {})
  }, [selectedCity])

  // ── Fetch competitors when area changes ──
  useEffect(() => {
    if (!selectedCity || !selectedArea) return
    fetchCompetitors()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedArea])

  async function fetchCompetitors() {
    setLoading(true)
    try {
      const res: any = await api.peers.competitors(selectedCity, selectedArea)
      setCompetitors(res.competitors ?? [])
    } catch {
      setCompetitors([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAnalyze() {
    setAnalyzing(true)
    setAnalysis(null)
    try {
      const res: any = await api.peers.analyze(selectedCity, selectedArea)
      setAnalysis(res)
    } catch {
      setAnalysis({ status: 'error', analysis: 'Failed to fetch AI analysis. Please try again.' })
    } finally {
      setAnalyzing(false)
    }
  }

  // ── Market Overview stats ──
  const avgRating =
    competitors.length > 0
      ? (competitors.reduce((s, c) => s + c.rating, 0) / competitors.length).toFixed(2)
      : '—'
  const avgOrderValue =
    competitors.length > 0
      ? Math.round(competitors.reduce((s, c) => s + c.avg_order_value, 0) / competitors.length)
      : 0
  const priceBands = [...new Set(competitors.map(c => c.price_band))]
  const priceBandRange =
    priceBands.length === 0
      ? '—'
      : priceBands.sort().join(' – ')

  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <Header
        title="Market Radar"
        subtitle="Benchmark your café against nearby competitors"
      />

      <div className="p-4 md:p-6 space-y-6 flex-1">

        {/* ── ROW 1: Controls ── */}
        <div className="card p-5">
          <div className="flex flex-wrap items-end gap-4">
            {/* City selector */}
            <div className="flex flex-col gap-1 min-w-[160px]">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">City</label>
              <div className="relative">
                <select
                  value={selectedCity}
                  onChange={e => setSelectedCity(e.target.value)}
                  className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-3 py-2 pr-8 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-400 cursor-pointer shadow-sm"
                >
                  {cities.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-2.5 text-slate-400 pointer-events-none" />
              </div>
            </div>

            {/* Area selector */}
            <div className="flex flex-col gap-1 min-w-[160px]">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Area</label>
              <div className="relative">
                <select
                  value={selectedArea}
                  onChange={e => setSelectedArea(e.target.value)}
                  className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-3 py-2 pr-8 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-400 cursor-pointer shadow-sm"
                >
                  {areas.map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-2.5 text-slate-400 pointer-events-none" />
              </div>
            </div>

            {/* Search button */}
            <button
              onClick={fetchCompetitors}
              disabled={loading}
              className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
              {loading
                ? <RefreshCw size={14} className="animate-spin" />
                : <Search size={14} />}
              {loading ? 'Searching…' : 'Search Competitors'}
            </button>

          </div>
        </div>

        {/* ── ROW 2: Market Overview stats ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center">
                <Star size={16} className="text-amber-500" />
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Avg Market Rating</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{avgRating}</div>
            <div className="text-xs text-slate-400 mt-0.5">out of 5.0</div>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                <TrendingUp size={16} className="text-green-500" />
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Avg Order Value</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">
              {avgOrderValue > 0 ? `₹${avgOrderValue}` : '—'}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">per customer</div>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center">
                <Users size={16} className="text-brand-500" />
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Competitors</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{competitors.length}</div>
            <div className="text-xs text-slate-400 mt-0.5">in {selectedArea}</div>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                <Award size={16} className="text-purple-500" />
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Price Range</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{priceBandRange || '—'}</div>
            <div className="text-xs text-slate-400 mt-0.5">price bands</div>
          </div>
        </div>

        {/* ── ROW 3: Competitor Cards Grid ── */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <RefreshCw size={32} className="animate-spin text-brand-400" />
              <span className="text-sm">Loading competitors…</span>
            </div>
          </div>
        ) : competitors.length === 0 ? (
          <div className="card p-10 text-center">
            <Target size={40} className="mx-auto text-slate-300 mb-3" />
            <p className="text-slate-500 text-sm">No competitor data found. Try a different city or area.</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-slate-900 font-bold text-base">
                Competitors in {selectedArea}, {selectedCity}
              </h2>
              <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">
                {competitors.length} found
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {competitors.map(comp => (
                <CompetitorCard key={comp.name} comp={comp} />
              ))}
            </div>
          </div>
        )}

        {/* ── ROW 4: Radar Chart + AI Analysis ── */}
        {competitors.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Radar Chart */}
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center">
                  <Target size={16} className="text-brand-500" />
                </div>
                <div>
                  <h2 className="text-slate-900 font-bold text-base leading-tight">Competitive Radar</h2>
                  <p className="text-xs text-slate-500">Top 3 competitors across 6 dimensions</p>
                </div>
              </div>
              <RadarChart
                competitors={competitors}
                ourScores={undefined}
              />
            </div>

            {/* AI Insights */}
            <div className="card p-6 flex flex-col">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Zap size={16} className="text-purple-500" />
                </div>
                <div>
                  <h2 className="text-slate-900 font-bold text-base leading-tight">AI Market Insights</h2>
                  <p className="text-xs text-slate-500">Powered by Claude AI</p>
                </div>
              </div>

              {!analysis && !analyzing && (
                <div className="flex-1 flex flex-col items-center justify-center gap-4 py-8 text-center">
                  <div className="w-16 h-16 bg-purple-50 rounded-2xl flex items-center justify-center">
                    <Zap size={28} className="text-purple-400" />
                  </div>
                  <div>
                    <p className="text-slate-700 font-semibold text-sm">Ready for AI Analysis</p>
                    <p className="text-slate-400 text-xs mt-1">
                      Get market positioning, opportunities, and quick wins tailored to {selectedArea}
                    </p>
                  </div>
                  <button
                    onClick={handleAnalyze}
                    className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm"
                  >
                    <Zap size={14} />
                    Run AI Analysis
                  </button>
                </div>
              )}

              {analyzing && (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 py-8">
                  <RefreshCw size={28} className="animate-spin text-purple-500" />
                  <p className="text-slate-500 text-sm">Analysing {competitors.length} competitors with Claude AI…</p>
                </div>
              )}

              {analysis && !analyzing && (
                <div className="flex-1 flex flex-col gap-4">
                  {analysis.status === 'error' && (
                    <div className="flex items-center gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2 text-sm text-red-600">
                      <AlertTriangle size={14} />
                      Analysis encountered an error
                    </div>
                  )}
                  <div className="flex-1 overflow-y-auto max-h-80">
                    <AnalysisText text={analysis.analysis} />
                  </div>
                  <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                    <span className="text-xs text-slate-400 bg-slate-50 px-2 py-1 rounded-full font-mono">
                      {analysis.model}
                    </span>
                    <button
                      onClick={handleAnalyze}
                      className="flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 font-medium"
                    >
                      <RefreshCw size={12} />
                      Re-analyse
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
