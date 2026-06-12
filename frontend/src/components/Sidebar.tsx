import { NavLink, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import {
  LayoutDashboard, Database, BarChart2, TrendingUp,
  Lightbulb, Rocket, MessageCircle, Coffee, ChevronRight,
  X, Bell, Target, Settings, LogOut, Shield,
} from 'lucide-react'
import { useSidebar } from '../context/SidebarContext'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

// ─── All navigation items with associated permission key ─────────────────────
interface NavItem {
  to: string
  label: string
  icon: React.ElementType
  desc: string
  permission: string | null   // null = always visible (e.g. Dashboard)
  isWhatsApp?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',                label: 'Home',           icon: LayoutDashboard, desc: 'Overview & KPIs',          permission: null },
  { to: '/data-collection', label: 'Upload My Data', icon: Database,        desc: 'Excel & API import',        permission: 'upload_data' },
  { to: '/data-engineering',label: 'Reports & Insights', icon: BarChart2,   desc: 'Trends & summaries',        permission: 'reports' },
  { to: '/ai-intelligence', label: 'Smart Analytics',icon: TrendingUp,      desc: 'AI-powered predictions',    permission: 'analytics' },
  { to: '/decision-engine', label: 'What To Do Next',icon: Lightbulb,       desc: 'Action recommendations',    permission: 'decision_engine' },
  { to: '/cafe-os',         label: 'AI-Powered Execution', icon: Rocket, desc: 'AI takes approved actions',  permission: 'auto_pilot' },
  { to: '/chatbot',         label: 'Ask Cafe Buddy', icon: MessageCircle,   desc: 'Chat with your AI helper',  permission: 'chatbot' },
  { to: '/peer-comparison', label: 'Market Radar',   icon: Target,          desc: 'Benchmark vs nearby cafés', permission: 'market_radar' },
  { to: '/notifications',   label: 'WhatsApp Alerts',icon: Bell,            desc: 'Free daily summaries',      permission: 'whatsapp_alerts', isWhatsApp: true },
]

export default function Sidebar() {
  const location    = useLocation()
  const { isOpen, close } = useSidebar()
  const { user, hasPermission, logout } = useAuth()
  const navigate    = useNavigate()

  useEffect(() => { close() }, [location.pathname, close])

  // Filter nav items the current user is allowed to see
  const visibleItems = NAV_ITEMS.filter(item =>
    item.permission === null || hasPermission(item.permission)
  )

  const handleSignOut = () => {
    logout()
    navigate('/login', { replace: true })
  }

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

        {/* User role badge */}
        {user && (
          <div className="px-4 py-2.5 border-b border-slate-800 flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-white text-xs font-bold uppercase flex-shrink-0">
              {(user.username || 'A').slice(0, 2)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white text-xs font-semibold capitalize truncate">{user.full_name || user.username}</div>
              <div className="text-slate-400 text-xs truncate">{user.role}</div>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          <p className="text-slate-600 text-xs font-semibold uppercase tracking-wider px-2 mb-2">Menu</p>
          <ul className="space-y-0.5">
            {visibleItems.map((item) => {
              const Icon     = item.icon
              const isActive = item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to)

              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group ${
                      isActive
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                    }`}
                  >
                    <Icon
                      size={16}
                      className={`flex-shrink-0 ${
                        isActive          ? 'text-brand-400'
                        : item.isWhatsApp ? 'text-green-500 group-hover:text-green-400'
                        :                  'text-slate-500 group-hover:text-slate-300'
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

            {/* Admin section — Role Management + Audit Logs */}
            {(hasPermission('role_management') || hasPermission('audit_logs')) && (
              <>
                <li className="pt-3 pb-1">
                  <p className="text-slate-600 text-xs font-semibold uppercase tracking-wider px-2">Admin</p>
                </li>

                {hasPermission('role_management') && (
                  <li>
                    <NavLink
                      to="/role-management"
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group ${
                          isActive
                            ? 'bg-slate-800 text-white shadow-sm'
                            : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Settings
                            size={16}
                            className={`flex-shrink-0 ${isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'}`}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium leading-tight truncate">Role Management</div>
                            <div className={`text-xs leading-tight truncate mt-0.5 ${
                              isActive ? 'text-slate-400' : 'text-slate-600 group-hover:text-slate-500'
                            }`}>Users & permissions</div>
                          </div>
                          {isActive && <ChevronRight size={13} className="text-brand-400 flex-shrink-0" />}
                        </>
                      )}
                    </NavLink>
                  </li>
                )}

                {hasPermission('audit_logs') && (
                  <li>
                    <NavLink
                      to="/audit"
                      className={({ isActive }) =>
                        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group ${
                          isActive
                            ? 'bg-slate-800 text-white shadow-sm'
                            : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Shield
                            size={16}
                            className={`flex-shrink-0 ${isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'}`}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium leading-tight truncate">Audit Logs</div>
                            <div className={`text-xs leading-tight truncate mt-0.5 ${
                              isActive ? 'text-slate-400' : 'text-slate-600 group-hover:text-slate-500'
                            }`}>Activity trail</div>
                          </div>
                          {isActive && <ChevronRight size={13} className="text-brand-400 flex-shrink-0" />}
                        </>
                      )}
                    </NavLink>
                  </li>
                )}
              </>
            )}
          </ul>
        </nav>

        {/* Footer with sign-out */}
        <div className="px-4 py-3 border-t border-slate-800">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-400 text-xs">All systems live</span>
            </div>
            <button
              onClick={handleSignOut}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              <LogOut size={13} />
              <span>Sign out</span>
            </button>
          </div>
          <div className="text-slate-600 text-xs">Cafe Buddy v2.1</div>
        </div>
      </aside>
    </>
  )
}
