/**
 * WorkspaceAdmin.tsx — System-admin-only page that lists all registered
 * café workspaces and allows permanent deletion.
 *
 * Only visible/accessible when the logged-in user belongs to the system
 * tenant (user.tenant_id === 'system' or undefined).
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Building2, Trash2, RefreshCw, AlertCircle, Check,
  Users, HardDrive, Calendar, ShieldAlert, X,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Tenant {
  tenant_id:        string
  slug:             string
  cafe_name:        string
  owner_name:       string
  owner_email:      string
  admin_username:   string
  plan:             string
  max_users:        number
  storage_limit_mb: number
  storage_used_mb:  number
  is_active:        boolean
  created_at:       string
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function WorkspaceAdmin() {
  const [tenants,         setTenants]         = useState<Tenant[]>([])
  const [loading,         setLoading]         = useState(true)
  const [error,           setError]           = useState('')
  const [toast,           setToast]           = useState('')
  const [deleteConfirm,   setDeleteConfirm]   = useState<Tenant | null>(null)
  const [deleting,        setDeleting]        = useState<string | null>(null)

  // ── Fetch tenants ─────────────────────────────────────────────────────────
  const fetchTenants = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.admin.listTenants()
      setTenants(data.tenants ?? [])
    } catch (e: any) {
      setError(e.message || 'Failed to load workspaces')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchTenants() }, [fetchTenants])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  // ── Delete workspace ──────────────────────────────────────────────────────
  const handleDelete = async (tenant: Tenant) => {
    setDeleting(tenant.tenant_id)
    try {
      await api.admin.deleteTenant(tenant.tenant_id)
      showToast(`Workspace "${tenant.cafe_name}" deleted successfully`)
      setDeleteConfirm(null)
      fetchTenants()
    } catch (e: any) {
      showToast(`Error: ${e.message}`)
    } finally {
      setDeleting(null)
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  const storagePct = (t: Tenant) =>
    t.storage_limit_mb > 0
      ? Math.min(100, (t.storage_used_mb / t.storage_limit_mb) * 100)
      : 0

  const planBadge = (plan: string) => {
    const cls =
      plan === 'free'    ? 'bg-slate-100 text-slate-600 border-slate-200' :
      plan === 'pro'     ? 'bg-blue-100 text-blue-700 border-blue-200'    :
                           'bg-purple-100 text-purple-700 border-purple-200'
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border capitalize ${cls}`}>
        {plan}
      </span>
    )
  }

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <Header
        title="Workspace Admin"
        subtitle="View and manage all registered café workspaces"
      />

      <div className="flex-1 p-4 md:p-6 max-w-6xl mx-auto w-full">

        {/* Warning banner */}
        <div className="flex items-start gap-3 p-4 mb-6 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <ShieldAlert size={18} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">System Admin Panel</p>
            <p className="text-amber-700 mt-0.5">
              Deleting a workspace permanently removes all its data, users, and uploaded files.
              This action cannot be undone.
            </p>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Total Workspaces', value: tenants.length, icon: Building2, color: 'text-brand-500', bg: 'bg-brand-50' },
            { label: 'Active Workspaces', value: tenants.filter(t => t.is_active).length, icon: Check, color: 'text-green-500', bg: 'bg-green-50' },
            { label: 'Total Users', value: tenants.reduce((s, t) => s + t.max_users, 0), icon: Users, color: 'text-blue-500', bg: 'bg-blue-50' },
          ].map(s => {
            const Icon = s.icon
            return (
              <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3 shadow-sm">
                <div className={`w-10 h-10 rounded-xl ${s.bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon size={18} className={s.color} />
                </div>
                <div>
                  <div className="text-2xl font-bold text-slate-900">{s.value}</div>
                  <div className="text-xs text-slate-500">{s.label}</div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
            <Building2 size={16} className="text-brand-500" />
            All Workspaces ({tenants.length})
          </h2>
          <button
            onClick={fetchTenants}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm mb-5">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mr-3" />
            Loading workspaces…
          </div>
        ) : tenants.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <Building2 size={40} className="mx-auto mb-3 opacity-30" />
            <p>No workspaces registered yet.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {tenants.map(tenant => (
              <div
                key={tenant.tenant_id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Workspace info */}
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    <div className="w-11 h-11 bg-brand-500 rounded-xl flex items-center justify-center text-white font-bold text-base flex-shrink-0 uppercase">
                      {tenant.cafe_name.slice(0, 2)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-bold text-slate-900 text-base">{tenant.cafe_name}</h3>
                        {planBadge(tenant.plan)}
                        {!tenant.is_active && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700 border border-red-200">
                            Inactive
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">/{tenant.slug}</span>
                        {' '}· Owner: <strong>{tenant.owner_name}</strong>
                        {' '}· Admin: <code className="text-xs">{tenant.admin_username}</code>
                      </p>
                      <p className="text-xs text-slate-400 mt-1">{tenant.owner_email}</p>

                      {/* Metadata row */}
                      <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Users size={11} />
                          Up to {tenant.max_users} users
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive size={11} />
                          {tenant.storage_used_mb.toFixed(1)} / {tenant.storage_limit_mb} MB used
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar size={11} />
                          Created {tenant.created_at}
                        </span>
                      </div>

                      {/* Storage bar */}
                      {tenant.storage_used_mb > 0 && (
                        <div className="mt-2 flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden max-w-xs">
                            <div
                              className={`h-full rounded-full transition-all ${
                                storagePct(tenant) > 80 ? 'bg-red-500' :
                                storagePct(tenant) > 50 ? 'bg-amber-400' : 'bg-green-500'
                              }`}
                              style={{ width: `${storagePct(tenant)}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">
                            {storagePct(tenant).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right: Delete button */}
                  <button
                    onClick={() => setDeleteConfirm(tenant)}
                    disabled={deleting === tenant.tenant_id}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50 transition-colors flex-shrink-0"
                    title="Delete workspace"
                  >
                    <Trash2 size={13} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Delete confirmation modal ── */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Trash2 size={22} className="text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg">Delete Workspace</h3>
                <p className="text-sm text-slate-500">This action is permanent and cannot be undone.</p>
              </div>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="ml-auto p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-4 bg-red-50 border border-red-200 rounded-xl mb-5">
              <p className="text-sm text-red-800 font-semibold mb-1">
                You are about to delete: <strong>{deleteConfirm.cafe_name}</strong>
              </p>
              <ul className="text-xs text-red-700 space-y-1 list-disc list-inside mt-2">
                <li>All uploaded data files will be deleted</li>
                <li>All user accounts for this workspace will be removed</li>
                <li>The workspace URL <code>/{deleteConfirm.slug}</code> will become available again</li>
                <li>The owner ({deleteConfirm.owner_email}) will lose access immediately</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2.5 text-sm font-medium border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleting === deleteConfirm.tenant_id}
                className="flex-1 px-4 py-2.5 text-sm font-semibold bg-red-500 hover:bg-red-600 disabled:bg-red-300 text-white rounded-xl flex items-center justify-center gap-2 transition-colors"
              >
                {deleting === deleteConfirm.tenant_id ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Deleting…
                  </>
                ) : (
                  <>
                    <Trash2 size={14} />
                    Delete Workspace
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-slate-900 text-white px-4 py-3 rounded-xl shadow-xl text-sm font-medium animate-fade-in">
          <Check size={15} className="text-green-400" /> {toast}
        </div>
      )}
    </div>
  )
}
