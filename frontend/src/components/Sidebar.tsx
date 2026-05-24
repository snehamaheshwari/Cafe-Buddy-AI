import { NavLink, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { LayoutDashboard, Database, BarChart2, TrendingUp, Lightbulb, Rocket, MessageCircle, Coffee, ChevronRight, X, Bell, Target } from 'lucide-react'
import { useSidebar } from '../context/SidebarContext'

const NAV_ITEMS = [
  { to: '/',                label: 'Home',                   icon: LayoutDashboard, desc: 'Overview & KPIs'          },
  { to: '/data-collection', label: 'Upload My Data',         icon: Database,        desc: 'Excel & API import'       },
  { to: '/data-engineering',label: 'Reports & Insights',     icon: BarChart2,       desc: 'Trends & summaries'       },
  { to: '/ai-intelligence', label: 'Smart Analytics',        icon: TrendingUp,      desc: 'AI-powered predictions'   },
  { to: '/decision-engine', label: 'What To Do Next',        icon: Lightbulb,       desc: 'Action recommendations'   },
  { to: '/cafe-os',         label: 'Auto-Pilot Mode',        icon: Rocket,          desc: 'Automated operations'     },
  { to: '/chatbot',         label: 'Ask Cafe Buddy',         icon: MessageCircle,   desc: 'Chat with your AI helper' },
  { to: '/notifications',   label: 'WhatsApp Alerts',        icon: Bell,            desc: 'Free daily summaries'     },
  { to: '/peer-comparison', label: 'Market Radar',            icon: Target,          desc: 'Benchmark vs nearby cafés' },
]

export default function Sidebar() {
  const location = useLocation()
  const { isOpen, close } = useSidebar()

  useEffect(() => { close() }, [location.pathname, close])

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-20 md:hidden" onClick={close} />
      )}

      <aside className={`
        fixed top-0 left-0 h-screen w-64 bg-slate-900 border-r border-slate-800 flex flex-col z-30
        transition-transform duration-200
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="px-4 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-500 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
              <Coffee size={18} className="text-white" />
            </div>
            <div>
              <div className="text-white font-bold text-base leading-tight">Cafe Buddy</div>
              <div className="text-slate-400 text-xs">Your AI Café Manager</div>
            </div>
          </div>
          <button className="md:hidden text-slate-400 hover:text-white p-1 rounded" onClick={close} aria-label="Close menu">
            <X size={20} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          <p className="text-slate-600 text-xs font-semibold uppercase tracking-wider px-2 mb-2">Menu</p>
          <ul className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive = item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
              const isWhatsApp = item.to === '/notifications'

              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group ${
                      isActive ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                    }`}
                  >
                    <Icon
                      size={16}
                      className={`flex-shrink-0 ${
                        isActive ? 'text-brand-400'
                        : isWhatsApp ? 'text-green-500 group-hover:text-green-400'
                        : 'text-slate-500 group-hover:text-slate-300'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium leading-tight truncate">{item.label}</div>
                      <div className={`text-xs leading-tight truncate mt-0.5 ${
                        isActive ? 'text-slate-400' : 'text-slate-600 group-hover:text-slate-500'
                      }`}>{item.desc}</div>
                    </div>
                    {isActive && <ChevronRight size={13} className="text-brand-400 flex-shrink-0" />}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-400 text-xs">All systems live</span>
          </div>
          <div className="text-slate-600 text-xs mt-0.5">Cafe Buddy v2.1</div>
        </div>
      </aside>
    </>
  )
}
