/**
 * TenantSettings.tsx — Workspace branding & plan management page.
 *
 * Accessible at /settings (admin only).
 * Shows: café name, brand colour, logo URL, plan info, user count, storage gauge.
 */
import { useState, useEffect } from 'react'
import { Building2, Palette, Save, Users, HardDrive, CheckCircle, AlertCircle, Coffee } from 'lucide-react'
import Header from '../components/Header'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

interface TenantInfo {
  tenant_id:        string
  cafe_name:        string
  brand_color:      string
  logo_url:         string
  plan:             string
  max_users:        number
  storage_limit_mb: number
  storage_used_mb:  number
  is_active:        boolean
  owner_email?:     string
  created_at?:      string
  slug?:            string
}

export default function TenantSettings() {
  const { user, login } = useAuth()

  const [info, setInfo]       = useState<TenantInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [saved, setSaved]     = useState(false)
  const [error, setError]     = useState('')

  // Editable form state
  const [form, setForm] = useState({
    cafe_name:   '',
    brand_color: '#6366f1',
    logo_url:    '',
  })

  useEffect(() => {
    api.tenant.info()
      .then((data: any) => {
        setInfo(data)
        setForm({
          cafe_name:   data.cafe_name   || '',
          brand_color: data.brand_color || '#6366f1',
          logo_url:    data.logo_url    || '',
        })
      })
      .catch(() => setError('Failed to load workspace info'))
      .finally(() => setLoading(false))
  }, [])

  const isSystemTenant = info?.tenant_id === 'system' || info?.plan === 'system'

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isSystemTenant) return
    setError('')
    setSaving(true)
    try {
      const updated = await api.tenant.updateBranding({
        cafe_name:   form.cafe_name,
        brand_color: form.brand_color,
        logo_url:    form.logo_url,
      }) as any

      setInfo(prev => prev ? { ...prev, ...updated.tenant } : prev)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)

      // Update auth context so Header reflects new branding immediately
      if (user) {
        login({
          ...user,
          cafe_name:   updated.tenant.cafe_name,
          brand_color: updated.tenant.brand_color,
          logo_url:    updated.tenant.logo_url,
        })
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const storagePct = info
    ? Math.min(100, Math.round((info.storage_used_mb / Math.max(info.storage_limit_mb, 1)) * 100))
    : 0

  return (
    <div className="flex flex-col min-h-screen">
      <Header title="Workspace Settings" subtitle="Manage your café branding and plan" />

      <main className="flex-1 p-4 md:p-6 space-y-6 max-w-2xl">
        {loading && (
          <div className="text-slate-400 text-sm flex items-center gap-2">
            <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
            Loading workspace info…
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
            <AlertCircle size={15} />
            {error}
          </div>
        )}

        {!loading && info && (
          <>
            {/* ── Plan & Storage Card ── */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <HardDrive size={15} className="text-slate-400" />
                Plan & Storage
              </h2>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
                <div className="text-center p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-lg font-bold text-slate-800 capitalize">{info.plan}</div>
                  <div className="text-xs text-slate-500">Plan</div>
                </div>
                <div className="text-center p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-lg font-bold text-slate-800">
                    {info.max_users === 999 ? '∞' : info.max_users}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center justify-center gap-1">
                    <Users size={10} /> Max Users
                  </div>
                </div>
                <div className="text-center p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <div className="text-lg font-bold text-slate-800">
                    {info.storage_limit_mb >= 999999 ? '∞' : `${info.storage_limit_mb} MB`}
                  </div>
                  <div className="text-xs text-slate-500">Storage Limit</div>
                </div>
              </div>

              {/* Storage gauge */}
              {info.storage_limit_mb < 999999 && (
                <div>
                  <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>Storage used</span>
                    <span>
                      {info.storage_used_mb.toFixed(1)} MB / {info.storage_limit_mb} MB
                      <span className="ml-1 font-semibold text-slate-700">({storagePct}%)</span>
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        storagePct > 80 ? 'bg-red-500' : storagePct > 60 ? 'bg-amber-400' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${storagePct}%` }}
                    />
                  </div>
                </div>
              )}

              {info.slug && (
                <div className="mt-3 text-xs text-slate-500">
                  Workspace URL:{' '}
                  <code className="font-mono text-indigo-600">?workspace={info.slug}</code>
                </div>
              )}
            </div>

            {/* ── Branding Form ── */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <Palette size={15} className="text-slate-400" />
                Branding
              </h2>

              {isSystemTenant ? (
                <p className="text-sm text-slate-400 italic">
                  The system (demo) workspace branding cannot be customised.
                </p>
              ) : (
                <form onSubmit={handleSave} className="space-y-4">
                  <div>
                    <label className="label-base">Café Name</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        className="input-base flex-1"
                        value={form.cafe_name}
                        onChange={e => setForm({ ...form, cafe_name: e.target.value })}
                        placeholder="Your café name"
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="label-base">Brand Colour</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={form.brand_color}
                        onChange={e => setForm({ ...form, brand_color: e.target.value })}
                        className="w-12 h-10 rounded border border-slate-300 cursor-pointer p-0.5"
                      />
                      <span className="font-mono text-sm text-slate-600">{form.brand_color}</span>
                      {/* Live preview */}
                      <div
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-white text-xs font-semibold"
                        style={{ backgroundColor: form.brand_color }}
                      >
                        <Coffee size={14} />
                        {form.cafe_name || 'Preview'}
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="label-base">Logo URL <span className="text-slate-400">(optional)</span></label>
                    <input
                      type="url"
                      className="input-base"
                      value={form.logo_url}
                      onChange={e => setForm({ ...form, logo_url: e.target.value })}
                      placeholder="https://your-domain.com/logo.png"
                    />
                    {form.logo_url && (
                      <img
                        src={form.logo_url}
                        alt="logo preview"
                        className="mt-2 h-12 object-contain rounded border border-slate-200"
                        onError={e => (e.currentTarget.style.display = 'none')}
                      />
                    )}
                  </div>

                  <div className="flex items-center gap-3 pt-1">
                    <button
                      type="submit"
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold transition-opacity disabled:opacity-60"
                      style={{ backgroundColor: form.brand_color }}
                    >
                      {saving ? (
                        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <>
                          <Save size={14} />
                          Save Changes
                        </>
                      )}
                    </button>

                    {saved && (
                      <span className="flex items-center gap-1.5 text-emerald-600 text-sm">
                        <CheckCircle size={14} />
                        Saved!
                      </span>
                    )}
                  </div>
                </form>
              )}
            </div>

            {/* ── Owner info ── */}
            {info.owner_email && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Building2 size={15} className="text-slate-400" />
                  Account Info
                </h2>
                <div className="text-sm text-slate-600 space-y-1">
                  <div><span className="text-slate-400">Owner email:</span> {info.owner_email}</div>
                  {info.created_at && (
                    <div><span className="text-slate-400">Created:</span> {info.created_at}</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
