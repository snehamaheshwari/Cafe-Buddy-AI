import { Bell, RefreshCw, LogOut } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface Props {
  title: string
  subtitle?: string
}

export default function Header({ title, subtitle }: Props) {
  const [time, setTime] = useState(new Date())
  const navigate = useNavigate()

  const user = (() => {
    try { return JSON.parse(localStorage.getItem('cafe_buddy_auth') || '{}') } catch { return {} }
  })()

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const handleSignOut = () => {
    localStorage.removeItem('cafe_buddy_auth')
    navigate('/login', { replace: true })
  }

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
      <div>
        <h1 className="text-lg font-bold text-slate-900 leading-tight">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Clock */}
        <div className="text-right hidden sm:block">
          <div className="text-sm font-semibold text-slate-700 font-mono">
            {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </div>
          <div className="text-xs text-slate-400">
            {time.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
          </div>
        </div>

        <button
          className="p-2 rounded hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700"
          title="Refresh"
          onClick={() => window.location.reload()}
        >
          <RefreshCw size={16} />
        </button>

        <button className="relative p-2 rounded hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700">
          <Bell size={16} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User + sign-out */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded bg-brand-500 flex items-center justify-center text-white text-xs font-bold uppercase">
            {(user.username || 'A').slice(0, 2)}
          </div>
          <div className="hidden sm:block">
            <div className="text-xs font-semibold text-slate-700 capitalize">{user.username || 'Admin'}</div>
            <div className="text-xs text-slate-400">{user.role || 'Owner'}</div>
          </div>
          <button
            onClick={handleSignOut}
            className="ml-1 flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium text-slate-500 hover:bg-red-50 hover:text-red-600 border border-transparent hover:border-red-200 transition-colors"
            title="Sign out"
          >
            <LogOut size={13} />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </div>
    </header>
  )
}
