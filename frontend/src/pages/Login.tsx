import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Coffee, Eye, EyeOff, AlertCircle, Building2, UserPlus, LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────
type Mode = 'signin' | 'register'

const DEFAULT_COLOR = '#6366f1'

export default function Login() {
  const navigate          = useNavigate()
  const [searchParams]    = useSearchParams()
  const { login }         = useAuth()

  const [mode, setMode]   = useState<Mode>('signin')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // ── Sign-in form state ──────────────────────────────────────────────────────
  const [signIn, setSignIn] = useState({ username: '', password: '' })
  const [showPw, setShowPw] = useState(false)

  // Workspace slug from URL (?workspace=heenu-cafe)
  const workspaceSlug = searchParams.get('workspace') || ''
  const [workspaceBrand, setWorkspaceBrand] = useState<{
    cafe_name: string; brand_color: string; logo_url: string
  } | null>(null)

  // ── Registration form state ─────────────────────────────────────────────────
  const [reg, setReg] = useState({
    cafe_name:   '',
    owner_name:  '',
    owner_email: '',
    username:    '',
    password:    '',
    confirm_pw:  '',
    brand_color: DEFAULT_COLOR,
  })
  const [showRegPw, setShowRegPw]         = useState(false)
  const [showRegConfirm, setShowRegConfirm] = useState(false)
  const [registeredSlug, setRegisteredSlug] = useState<string | null>(null)

  // ── Fetch workspace branding when slug present ──────────────────────────────
  useEffect(() => {
    if (!workspaceSlug) return
    api.auth.workspace(workspaceSlug)
      .then(data => setWorkspaceBrand({
        cafe_name:   data.cafe_name,
        brand_color: data.brand_color,
        logo_url:    data.logo_url,
      }))
      .catch(() => setWorkspaceBrand(null))
  }, [workspaceSlug])

  // ── Effective brand color for this page ────────────────────────────────────
  const pageColor = workspaceBrand?.brand_color || DEFAULT_COLOR

  // ─── Sign-in submit ────────────────────────────────────────────────────────
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const body: { username: string; password: string; workspace?: string } = {
        username: signIn.username,
        password: signIn.password,
      }
      if (workspaceSlug) body.workspace = workspaceSlug

      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Login failed')
      }
      const data = await res.json()
      login({
        username:    data.username,
        full_name:   data.full_name ?? data.username,
        role_id:     data.role_id ?? 'viewer',
        role:        data.role ?? 'Viewer',
        permissions: data.permissions ?? [],
        token:       data.token,
        tenant_id:   data.tenant_id,
        tenant_slug: data.tenant_slug,
        cafe_name:   data.cafe_name,
        brand_color: data.brand_color,
        logo_url:    data.logo_url,
      })
      // Preserve workspace slug in the URL so the app stays tenant-scoped
      navigate(workspaceSlug ? `/?workspace=${workspaceSlug}` : '/', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  // ─── Registration submit ────────────────────────────────────────────────────
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (reg.password !== reg.confirm_pw) {
      setError('Passwords do not match')
      return
    }
    if (reg.password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRe.test(reg.owner_email)) {
      setError('Enter a valid email address')
      return
    }

    setLoading(true)
    try {
      const data = await api.auth.register({
        cafe_name:   reg.cafe_name,
        owner_name:  reg.owner_name,
        owner_email: reg.owner_email,
        username:    reg.username,
        password:    reg.password,
        brand_color: reg.brand_color,
      }) as any

      // Auto-login after successful registration — save token BEFORE showing success screen
      login({
        username:    data.username,
        full_name:   reg.owner_name || data.username,
        role_id:     'admin',
        role:        'Admin',
        permissions: data.permissions ?? [],
        token:       data.token,
        tenant_id:   data.tenant_id,
        tenant_slug: data.slug,
        cafe_name:   data.cafe_name,
        brand_color: data.brand_color,
        logo_url:    data.logo_url,
      })
      // Show workspace URL on success screen so the user can bookmark their login link
      setRegisteredSlug(data.slug)
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const brandIconBg = { backgroundColor: pageColor }
  const workspaceLoginUrl = registeredSlug
    ? `${window.location.origin}/login?workspace=${registeredSlug}`
    : ''

  // ── Registration success screen ─────────────────────────────────────────────
  if (registeredSlug) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg bg-emerald-500">
              <Coffee size={30} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Workspace Ready!</h1>
            <p className="text-slate-400 text-sm mt-1">Your café dashboard is set up</p>
          </div>

          <div className="bg-white rounded-xl shadow-2xl p-7 space-y-5">
            <div className="text-center">
              <div className="text-4xl mb-3">🎉</div>
              <h2 className="text-lg font-bold text-slate-900">Welcome to Cafe Buddy!</h2>
              <p className="text-sm text-slate-500 mt-1">
                Your workspace <strong>{reg.cafe_name || registeredSlug}</strong> is ready.
                Save your login URL below — you'll need it every time you sign in.
              </p>
            </div>

            {/* Workspace URL box */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-xs font-semibold text-amber-700 mb-2">Your Login URL (bookmark this!)</p>
              {/* Use input[readonly] so the user can always select + copy, even on HTTP */}
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={workspaceLoginUrl}
                  onFocus={e => e.currentTarget.select()}
                  className="flex-1 text-xs text-amber-900 bg-amber-100 rounded px-2 py-1.5 border-0 outline-none cursor-text"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (navigator.clipboard) {
                      navigator.clipboard.writeText(workspaceLoginUrl)
                    } else {
                      // HTTP fallback: select the input text so user can Ctrl+C
                      const el = document.querySelector('input[readonly]') as HTMLInputElement | null
                      el?.select()
                    }
                  }}
                  className="shrink-0 text-xs bg-amber-500 text-white px-3 py-1.5 rounded hover:bg-amber-600 transition-colors"
                >
                  Copy
                </button>
              </div>
              <p className="text-xs text-amber-600 mt-2">
                Workspace slug: <strong>{registeredSlug}</strong>
              </p>
            </div>

            <button
              onClick={() => navigate(`/?workspace=${registeredSlug}`, { replace: true })}
              className="w-full py-3 rounded-lg font-semibold text-white transition-colors"
              style={{ backgroundColor: '#10b981' }}
            >
              Go to Dashboard →
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        {/* ── Logo ── */}
        <div className="text-center mb-8">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg"
            style={brandIconBg}
          >
            {workspaceBrand?.logo_url ? (
              <img src={workspaceBrand.logo_url} alt="logo"
                className="w-10 h-10 object-contain rounded-lg" />
            ) : (
              <Coffee size={30} className="text-white" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-white">
            {workspaceBrand?.cafe_name || 'Cafe Buddy'}
          </h1>
          <p className="text-slate-400 text-sm mt-1">AI Café Operating System</p>
        </div>

        {/* ── Card ── */}
        <div className="bg-white rounded-xl shadow-2xl overflow-hidden">
          {/* Tab switcher */}
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => { setMode('signin'); setError('') }}
              className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-semibold transition-colors
                ${mode === 'signin'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/40'
                  : 'text-slate-500 hover:bg-slate-50'}`}
            >
              <LogIn size={15} />
              Sign In
            </button>
            <button
              onClick={() => { setMode('register'); setError('') }}
              className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-semibold transition-colors
                ${mode === 'register'
                  ? 'text-emerald-600 border-b-2 border-emerald-600 bg-emerald-50/40'
                  : 'text-slate-500 hover:bg-slate-50'}`}
            >
              <UserPlus size={15} />
              New Cafe Setup
            </button>
          </div>

          <div className="p-7">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600 text-sm">
                <AlertCircle size={15} className="flex-shrink-0" />
                {error}
              </div>
            )}

            {/* ══════════════ SIGN IN ══════════════ */}
            {mode === 'signin' && (
              <>
                <h2 className="text-lg font-bold text-slate-900 mb-0.5">Sign in to your account</h2>
                <p className="text-xs text-slate-400 mb-5">
                  {workspaceBrand
                    ? `Workspace: ${workspaceBrand.cafe_name}`
                    : 'Enter your credentials to continue'}
                </p>

                <form onSubmit={handleSignIn} className="space-y-4">
                  {/* Workspace info chip if logging into tenant */}
                  {workspaceBrand && (
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-50 border border-indigo-200 text-xs text-indigo-700">
                      <Building2 size={13} />
                      <span>Logging into <strong>{workspaceBrand.cafe_name}</strong> workspace</span>
                    </div>
                  )}

                  <div>
                    <label className="label-base">Username</label>
                    <input
                      type="text"
                      className="input-base"
                      placeholder="admin"
                      value={signIn.username}
                      onChange={(e) => setSignIn({ ...signIn, username: e.target.value })}
                      required
                      autoFocus
                    />
                  </div>

                  <div>
                    <label className="label-base">Password</label>
                    <div className="relative">
                      <input
                        type={showPw ? 'text' : 'password'}
                        className="input-base pr-10"
                        placeholder="••••••••"
                        value={signIn.password}
                        onChange={(e) => setSignIn({ ...signIn, password: e.target.value })}
                        required
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        onClick={() => setShowPw(!showPw)}
                      >
                        {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary w-full mt-2 flex items-center justify-center gap-2 py-2.5"
                    style={{ backgroundColor: pageColor, borderColor: pageColor }}
                  >
                    {loading ? (
                      <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : 'Sign In'}
                  </button>
                </form>

                {/* Demo credentials hint (system workspace only) */}
                {!workspaceSlug && (
                  <div className="mt-5 p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-xs font-semibold text-slate-500 mb-2">Demo Credentials</p>
                    <div className="space-y-1 text-xs">
                      {[
                        { user: 'admin', pass: 'cafe123',     role: 'Admin (full access)' },
                        { user: 'owner', pass: 'buddy@2024',  role: 'Admin (full access)' },
                      ].map(c => (
                        <div key={c.user} className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <button
                              className="font-mono font-semibold text-brand-600 hover:underline"
                              onClick={() => setSignIn({ username: c.user, password: c.pass })}
                            >
                              {c.user}
                            </button>
                            <span className="text-slate-400">/ {c.pass}</span>
                          </div>
                          <span className="text-slate-400 text-right shrink-0">{c.role}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs text-slate-400 mt-1.5">(Click username to auto-fill)</p>
                  </div>
                )}

                {/* Link to register */}
                <p className="text-center text-xs text-slate-400 mt-4">
                  New café?{' '}
                  <button
                    className="text-emerald-600 font-semibold hover:underline"
                    onClick={() => { setMode('register'); setError('') }}
                  >
                    Create your workspace →
                  </button>
                </p>
              </>
            )}

            {/* ══════════════ REGISTRATION ══════════════ */}
            {mode === 'register' && (
              <>
                <h2 className="text-lg font-bold text-slate-900 mb-0.5">Create your café workspace</h2>
                <p className="text-xs text-slate-400 mb-5">
                  Set up your account in under a minute. Free plan: 3 users · 200 MB data.
                </p>

                <form onSubmit={handleRegister} className="space-y-3">
                  {/* Café details */}
                  <div className="rounded-lg border border-slate-200 p-3 space-y-3 bg-slate-50/40">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
                      <Building2 size={11} /> Café Details
                    </p>
                    <div>
                      <label className="label-base">Café Name <span className="text-red-500">*</span></label>
                      <input
                        type="text"
                        className="input-base"
                        placeholder="e.g. Heenu's Café"
                        value={reg.cafe_name}
                        onChange={e => setReg({ ...reg, cafe_name: e.target.value })}
                        required
                        autoFocus
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <label className="label-base">Brand Color</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={reg.brand_color}
                            onChange={e => setReg({ ...reg, brand_color: e.target.value })}
                            className="w-10 h-9 rounded border border-slate-300 cursor-pointer p-0.5"
                            title="Pick your brand colour"
                          />
                          <span className="text-xs text-slate-500 font-mono">{reg.brand_color}</span>
                        </div>
                      </div>
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 mt-4"
                        style={{ backgroundColor: reg.brand_color }}
                        title="Preview"
                      >
                        <Coffee size={18} className="text-white" />
                      </div>
                    </div>
                  </div>

                  {/* Owner details */}
                  <div className="rounded-lg border border-slate-200 p-3 space-y-3 bg-slate-50/40">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
                      <UserPlus size={11} /> Owner Details
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2 sm:col-span-1">
                        <label className="label-base">Full Name <span className="text-red-500">*</span></label>
                        <input
                          type="text"
                          className="input-base"
                          placeholder="Your name"
                          value={reg.owner_name}
                          onChange={e => setReg({ ...reg, owner_name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="col-span-2 sm:col-span-1">
                        <label className="label-base">Email <span className="text-red-500">*</span></label>
                        <input
                          type="email"
                          className="input-base"
                          placeholder="you@example.com"
                          value={reg.owner_email}
                          onChange={e => setReg({ ...reg, owner_email: e.target.value })}
                          required
                        />
                      </div>
                    </div>
                  </div>

                  {/* Account credentials */}
                  <div className="rounded-lg border border-slate-200 p-3 space-y-3 bg-slate-50/40">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      Login Credentials
                    </p>
                    <div>
                      <label className="label-base">Username <span className="text-red-500">*</span></label>
                      <input
                        type="text"
                        className="input-base"
                        placeholder="e.g. heenu_admin"
                        value={reg.username}
                        onChange={e => setReg({ ...reg, username: e.target.value.replace(/\s+/g, '_') })}
                        required
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="label-base">Password <span className="text-red-500">*</span></label>
                        <div className="relative">
                          <input
                            type={showRegPw ? 'text' : 'password'}
                            className="input-base pr-9"
                            placeholder="Min 6 chars"
                            value={reg.password}
                            onChange={e => setReg({ ...reg, password: e.target.value })}
                            required
                          />
                          <button type="button"
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                            onClick={() => setShowRegPw(!showRegPw)}
                          >
                            {showRegPw ? <EyeOff size={13} /> : <Eye size={13} />}
                          </button>
                        </div>
                      </div>
                      <div>
                        <label className="label-base">Confirm Password <span className="text-red-500">*</span></label>
                        <div className="relative">
                          <input
                            type={showRegConfirm ? 'text' : 'password'}
                            className="input-base pr-9"
                            placeholder="Repeat"
                            value={reg.confirm_pw}
                            onChange={e => setReg({ ...reg, confirm_pw: e.target.value })}
                            required
                          />
                          <button type="button"
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                            onClick={() => setShowRegConfirm(!showRegConfirm)}
                          >
                            {showRegConfirm ? <EyeOff size={13} /> : <Eye size={13} />}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Plan summary */}
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                    <span className="font-semibold">Free Plan included: </span>
                    3 user accounts · 200 MB data storage · All AI features
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-white font-semibold text-sm transition-opacity disabled:opacity-60"
                    style={{ backgroundColor: reg.brand_color || DEFAULT_COLOR }}
                  >
                    {loading ? (
                      <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <>
                        <UserPlus size={16} />
                        Create Workspace & Sign In
                      </>
                    )}
                  </button>
                </form>

                <p className="text-center text-xs text-slate-400 mt-4">
                  Already have an account?{' '}
                  <button
                    className="text-indigo-600 font-semibold hover:underline"
                    onClick={() => { setMode('signin'); setError('') }}
                  >
                    Sign in →
                  </button>
                </p>
              </>
            )}
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-5">
          Cafe Buddy v2.0 · AI Café Operating System
        </p>
      </div>
    </div>
  )
}
