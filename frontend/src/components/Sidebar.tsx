import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Database, Cpu, Brain, Zap, Bot, Coffee, ChevronRight, MessageSquare } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/',        label: 'Dashboard',            icon: LayoutDashboard },
  { to: '/data-collection',  label: 'Data Collection',      icon: Database },
  { to: '/data-engineering', label: 'Data Engineering',     icon: Cpu     },
  { to: '/ai-intelligence',  label: 'AI / ML Intelligence', icon: Brain   },
  { to: '/decision-engine',  label: 'Decision Engine',      icon: Zap     },
  { to: '/cafe-os',          label: 'Autonomous Café OS',   icon: Bot     },
  { to: '/chatbot', label: 'AI Chat Assistant',    icon: MessageSquare   },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed top-0 left-0 h-screen w-64 bg-slate-900 border-r border-slate-800 flex flex-col z-30">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-brand-500 rounded flex items-center justify-center">
            <Coffee size={18} className="text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-base leading-tight">Cafe Buddy</div>
            <div className="text-slate-400 text-xs">AI Café Operating System</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider px-3 mb-3">
          Navigation
        </div>
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to)

            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors group ${
                    isActive
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  <Icon
                    size={16}
                    className={isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'}
                  />
                  <span className="flex-1 truncate font-medium">{item.label}</span>
                  {isActive && <ChevronRight size={14} className="text-brand-400 flex-shrink-0" />}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-400 text-xs">All systems operational</span>
        </div>
        <div className="text-slate-600 text-xs mt-1">v2.0.0 Prototype</div>
      </div>
    </aside>
  )
}
