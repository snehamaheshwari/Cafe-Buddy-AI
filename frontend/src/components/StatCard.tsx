import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'

interface Props {
  title: string
  value: string | number
  change?: string
  trend?: 'up' | 'down' | 'neutral'
  icon?: LucideIcon
  iconColor?: string
  iconBg?: string
  subtitle?: string
}

export default function StatCard({ title, value, change, trend, icon: Icon, iconColor, iconBg, subtitle }: Props) {
  const trendUp = trend === 'up'
  const trendDown = trend === 'down'

  return (
    <div className="card">
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {Icon && (
            <div className={`w-10 h-10 rounded flex items-center justify-center flex-shrink-0 ${iconBg || 'bg-slate-100'}`}>
              <Icon size={18} className={iconColor || 'text-slate-600'} />
            </div>
          )}
        </div>
        {change && (
          <div className={`flex items-center gap-1 mt-3 text-xs font-medium ${trendUp ? 'text-emerald-600' : trendDown ? 'text-red-500' : 'text-slate-500'}`}>
            {trendUp && <TrendingUp size={12} />}
            {trendDown && <TrendingDown size={12} />}
            <span>{change}</span>
            <span className="text-slate-400 font-normal">vs yesterday</span>
          </div>
        )}
      </div>
    </div>
  )
}
