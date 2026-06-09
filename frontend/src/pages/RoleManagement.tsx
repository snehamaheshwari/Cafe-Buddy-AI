import { useState, useEffect, useCallback } from 'react'
import {
  Shield, Users, Plus, Trash2, Edit2, Save, X, Check,
  AlertCircle, ChevronDown, ChevronUp, Lock, UserCheck,
  LayoutDashboard, Database, BarChart2, TrendingUp, Lightbulb,
  Rocket, MessageCircle, Target, Bell, Settings,
} from 'lucide-react'
import Header from '../components/Header'
import { useAuth } from '../context/AuthContext'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Role {
  id: string
  name: string
  description: string
  is_system: boolean
  permissions: string[]
}

interface User {
  username: string
  full_name: string
  email: string
  role_id: string
  is_active: boolean
  is_system: boolean
  created_at: string
}

interface PermMeta {
  key: string
  label: string
  icon: React.ElementType
  color: string
}

// ─── Permission metadata ──────────────────────────────────────────────────────
const PERM_META: PermMeta[] = [
  { key: 'dashboard',       label: 'Home / Dashboard',    icon: LayoutDashboard, color: 'text-brand-500' },
  { key: 'upload_data',     label: 'Upload My Data',      icon: Database,        color: 'text-blue-500' },
  { key: 'reports',         label: 'Reports & Insights',  icon: BarChart2,       color: 'text-green-500' },
  { key: 'analytics',       label: 'Smart Analytics',     icon: TrendingUp,      color: 'text-purple-500' },
  { key: 'decision_engine', label: 'What To Do Next',     icon: Lightbulb,       color: 'text-yellow-500' },
  { key: 'auto_pilot',      label: 'Auto-Pilot Mode',     icon: Rocket,          color: 'text-orange-500' },
  { key: 'chatbot',         label: 'Ask Cafe Buddy',      icon: MessageCircle,   color: 'text-cyan-500' },
  { key: 'market_radar',    label: 'Market Radar',        icon: Target,          color: 'text-rose-500' },
  { key: 'whatsapp_alerts', label: 'WhatsApp Alerts',     icon: Bell,            color: 'text-emerald-500' },
  { key: 'role_management', label: 'Role Management',     icon: Settings,        color: 'text-slate-500' },
]

const ROLE_COLORS: Record<string, string> = {
  admin:     'bg-red-100 text-red-700 border-red-200',
  sub_admin: 'bg-blue-100 text-blue-700 border-blue-200',
  viewer:    'bg-slate-100 text-slate-700 border-slate-200',
}
const ROLE_COLOR_DEFAULT = 'bg-purple-100 text-purple-700 border-purple-200'

// ─── Helpers ─────────────────────────────────────────────────────────────────
function roleBadge(roleId: string, roleName: string) {
  const cls = ROLE_COLORS[roleId] ?? ROLE_COLOR_DEFAULT
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      {roleName}
    </span>
  )
}

// ─── Modals ───────────────────────────────────────────────────────────────────
interface RoleModalProps {
  roles: Role[]
  initial?: Partial<Role>
  onSave: (data: { id: string; name: string; description: string; permissions: string[] }) => void
  onClose: () => void
}

function RoleModal({ roles, initial, onSave, onClose }: RoleModalProps) {
  const isEdit = Boolean(initial?.id)
  const [id, setId]               = useState(initial?.id ?? '')
  const [name, setName]           = useState(initial?.name ?? '')
  const [desc, setDesc]           = useState(initial?.description ?? '')
  const [perms, setPerms]         = useState<string[]>(initial?.permissions ?? [])
  const [error, setError]         = useState('')

  const togglePerm = (key: string) =>
    setPerms(p => p.includes(key) ? p.filter(k => k !== key) : [...p, key])

  const handleSave = () => {
    if (!name.trim()) { setError('Name is required'); return }
    if (!isEdit && !id.trim()) { setError('Role ID is required'); return }
    if (perms.length === 0) { setError('Select at least one permission'); return }
    const roleId = isEdit ? (initial?.id ?? id) : id.trim().toLowerCase().replace(/\s+/g, '_')
    if (!isEdit && roles.some(r => r.id === roleId)) {
      setError('A role with this ID already exists'); return
    }
    setError('')
    onSave({ id: roleId, name: name.trim(), description: desc.trim(), permissions: perms })
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Shield size={18} className="text-brand-500" />
            {isEdit ? 'Edit Role' : 'Create New Role'}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 text-slate-400"><X size={18} /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              <AlertCircle size={15} /> {error}
            </div>
          )}

          {!isEdit && (
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Role ID <span className="text-red-400">*</span></label>
              <input
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
                placeholder="e.g. kitchen_staff"
                value={id}
                onChange={e => setId(e.target.value)}
              />
              <p className="text-xs text-slate-400 mt-1">Lowercase, underscores only. Cannot be changed later.</p>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Display Name <span className="text-red-400">*</span></label>
            <input
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="e.g. Kitchen Staff"
              value={name}
              onChange={e => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Description</label>
            <input
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Briefly describe this role"
              value={desc}
              onChange={e => setDesc(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-2">
              Permissions <span className="text-red-400">*</span>
              <span className="ml-2 text-slate-400 font-normal">({perms.length} selected)</span>
            </label>
            <div className="grid grid-cols-1 gap-1.5">
              {PERM_META.map(p => {
                const Icon = p.icon
                const checked = perms.includes(p.key)
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => togglePerm(p.key)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-sm transition-all text-left ${
                      checked
                        ? 'bg-brand-50 border-brand-300 text-brand-800'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                      checked ? 'bg-brand-500 border-brand-500' : 'border-slate-300'
                    }`}>
                      {checked && <Check size={12} className="text-white" />}
                    </div>
                    <Icon size={14} className={checked ? 'text-brand-500' : p.color} />
                    <span className="flex-1 font-medium">{p.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-semibold bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Save size={14} /> {isEdit ? 'Save Changes' : 'Create Role'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Member Modal ─────────────────────────────────────────────────────────────
interface MemberModalProps {
  roles: Role[]
  initial?: Partial<User>
  onSave: (data: { username: string; password: string; role_id: string; full_name: string; email: string }) => void
  onClose: () => void
  isEdit: boolean
}

function MemberModal({ roles, initial, onSave, onClose, isEdit }: MemberModalProps) {
  const [username,  setUsername]  = useState(initial?.username ?? '')
  const [password,  setPassword]  = useState('')
  const [roleId,    setRoleId]    = useState(initial?.role_id ?? 'viewer')
  const [fullName,  setFullName]  = useState(initial?.full_name ?? '')
  const [email,     setEmail]     = useState(initial?.email ?? '')
  const [error,     setError]     = useState('')

  const handleSave = () => {
    if (!isEdit && !username.trim()) { setError('Username is required'); return }
    if (!isEdit && !password) { setError('Password is required'); return }
    if (!roleId) { setError('Select a role'); return }
    setError('')
    onSave({ username: username.trim(), password, role_id: roleId, full_name: fullName.trim(), email: email.trim() })
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <UserCheck size={18} className="text-brand-500" />
            {isEdit ? 'Edit Member' : 'Add New Member'}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-slate-100 text-slate-400"><X size={18} /></button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              <AlertCircle size={15} /> {error}
            </div>
          )}

          {!isEdit ? (
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Username <span className="text-red-400">*</span></label>
              <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. manager1" value={username} onChange={e => setUsername(e.target.value)} />
            </div>
          ) : (
            <div className="p-3 bg-slate-50 rounded-lg text-sm text-slate-600 font-mono border border-slate-200">
              <span className="text-slate-400 font-sans text-xs">Username: </span>{username}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              {isEdit ? 'New Password' : 'Password'} {!isEdit && <span className="text-red-400">*</span>}
            </label>
            <input type="password"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder={isEdit ? 'Leave blank to keep current' : '••••••••'}
              value={password} onChange={e => setPassword(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Full Name</label>
            <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="e.g. Priya Sharma" value={fullName} onChange={e => setFullName(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Email</label>
            <input type="email"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="priya@cafe.com" value={email} onChange={e => setEmail(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Role <span className="text-red-400">*</span></label>
            <select
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              value={roleId} onChange={e => setRoleId(e.target.value)}
            >
              {roles.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
            {roles.find(r => r.id === roleId) && (
              <p className="text-xs text-slate-400 mt-1">{roles.find(r => r.id === roleId)?.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200 rounded-lg">Cancel</button>
          <button onClick={handleSave}
            className="px-4 py-2 text-sm font-semibold bg-brand-500 hover:bg-brand-600 text-white rounded-lg flex items-center gap-1.5">
            <Save size={14} /> {isEdit ? 'Save Changes' : 'Add Member'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Role Card ────────────────────────────────────────────────────────────────
interface RoleCardProps {
  role: Role
  userCount: number
  onEdit: () => void
  onDelete: () => void
}

function RoleCard({ role, userCount, onEdit, onDelete }: RoleCardProps) {
  const [expanded, setExpanded] = useState(false)
  const badge = ROLE_COLORS[role.id] ?? ROLE_COLOR_DEFAULT

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between p-5">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
            role.id === 'admin' ? 'bg-red-50' :
            role.id === 'sub_admin' ? 'bg-blue-50' :
            role.id === 'viewer' ? 'bg-slate-100' : 'bg-purple-50'
          }`}>
            <Shield size={18} className={
              role.id === 'admin' ? 'text-red-500' :
              role.id === 'sub_admin' ? 'text-blue-500' :
              role.id === 'viewer' ? 'text-slate-500' : 'text-purple-500'
            } />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-slate-900 text-base">{role.name}</h3>
              {role.is_system && (
                <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                  <Lock size={10} /> System
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{role.description}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-xs text-slate-500">{role.permissions.length} permissions</span>
              <span className="text-slate-300">·</span>
              <span className="text-xs text-slate-500">{userCount} {userCount === 1 ? 'member' : 'members'}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1 ml-3 flex-shrink-0">
          <button onClick={onEdit}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-brand-600 transition-colors"
            title="Edit role">
            <Edit2 size={15} />
          </button>
          {!role.is_system && (
            <button onClick={onDelete}
              className="p-2 rounded-lg hover:bg-red-50 text-slate-500 hover:text-red-600 transition-colors"
              title="Delete role">
              <Trash2 size={15} />
            </button>
          )}
          <button onClick={() => setExpanded(e => !e)}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors">
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>
      </div>

      {/* Permissions grid */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Permissions</p>
          <div className="grid grid-cols-2 gap-1.5">
            {PERM_META.map(p => {
              const Icon = p.icon
              const has = role.permissions.includes(p.key)
              return (
                <div key={p.key} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs ${
                  has ? 'bg-green-50 text-green-700' : 'bg-slate-50 text-slate-400 line-through'
                }`}>
                  {has ? <Check size={11} className="text-green-500 flex-shrink-0" /> : <X size={11} className="text-slate-300 flex-shrink-0" />}
                  <Icon size={12} className={has ? p.color : 'text-slate-300'} />
                  <span className="truncate">{p.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function RoleManagement() {
  const { user: authUser } = useAuth()
  const [tab,        setTab]        = useState<'roles' | 'members'>('roles')
  const [roles,      setRoles]      = useState<Role[]>([])
  const [users,      setUsers]      = useState<User[]>([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState('')
  const [toast,      setToast]      = useState('')

  // Modals
  const [showRoleModal,   setShowRoleModal]   = useState(false)
  const [editingRole,     setEditingRole]     = useState<Role | undefined>()
  const [showMemberModal, setShowMemberModal] = useState(false)
  const [editingUser,     setEditingUser]     = useState<User | undefined>()
  const [deleteConfirm,   setDeleteConfirm]   = useState<{ type: 'role' | 'user'; id: string; name: string } | null>(null)

  // ── Fetch data ───────────────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [rRes, uRes] = await Promise.all([
        fetch('/api/roles'),
        fetch('/api/users'),
      ])
      if (!rRes.ok || !uRes.ok) throw new Error('Failed to load data')
      const rData = await rRes.json()
      const uData = await uRes.json()
      setRoles(rData.roles ?? [])
      setUsers(uData.users ?? [])
    } catch (e: any) {
      setError(e.message || 'Could not load role data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  // ── Role actions ─────────────────────────────────────────────────────────
  const handleRoleSave = async (data: { id: string; name: string; description: string; permissions: string[] }) => {
    const isEdit = Boolean(editingRole)
    const url    = isEdit ? `/api/roles/${data.id}` : '/api/roles'
    const method = isEdit ? 'PUT' : 'POST'
    const body   = isEdit
      ? { name: data.name, description: data.description, permissions: data.permissions }
      : data
    const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    const json = await res.json()
    if (!res.ok) { showToast(`Error: ${json.detail}`); return }
    showToast(isEdit ? `Role "${data.name}" updated` : `Role "${data.name}" created`)
    setShowRoleModal(false)
    setEditingRole(undefined)
    fetchData()
  }

  const handleRoleDelete = async (roleId: string) => {
    const res = await fetch(`/api/roles/${roleId}`, { method: 'DELETE' })
    const json = await res.json()
    if (!res.ok) { showToast(`Error: ${json.detail}`); return }
    showToast('Role deleted')
    setDeleteConfirm(null)
    fetchData()
  }

  // ── Member actions ───────────────────────────────────────────────────────
  const handleMemberSave = async (data: { username: string; password: string; role_id: string; full_name: string; email: string }) => {
    const isEdit = Boolean(editingUser)
    const url    = isEdit ? `/api/users/${data.username}` : '/api/users'
    const method = isEdit ? 'PUT' : 'POST'
    // For edit: only send fields that changed; skip empty password
    const body: Record<string, any> = isEdit
      ? { role_id: data.role_id, full_name: data.full_name, email: data.email,
          ...(data.password ? { password: data.password } : {}) }
      : data
    const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    const json = await res.json()
    if (!res.ok) { showToast(`Error: ${json.detail}`); return }
    showToast(isEdit ? `Member "${data.username}" updated` : `Member "${data.username}" added`)
    setShowMemberModal(false)
    setEditingUser(undefined)
    fetchData()
  }

  const handleToggleActive = async (username: string, isActive: boolean) => {
    const res = await fetch(`/api/users/${username}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
    if (!res.ok) { showToast('Error updating status'); return }
    showToast(isActive ? `${username} activated` : `${username} deactivated`)
    fetchData()
  }

  const handleMemberDelete = async (username: string) => {
    const res = await fetch(`/api/users/${username}`, { method: 'DELETE' })
    const json = await res.json()
    if (!res.ok) { showToast(`Error: ${json.detail}`); return }
    showToast(`Member "${username}" removed`)
    setDeleteConfirm(null)
    fetchData()
  }

  const userCountForRole = (roleId: string) => users.filter(u => u.role_id === roleId).length

  const getRoleName = (roleId: string) => roles.find(r => r.id === roleId)?.name ?? roleId

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <Header
        title="Role Management"
        subtitle="Manage team roles, permissions and member access"
      />

      <div className="flex-1 p-4 md:p-6 max-w-5xl mx-auto w-full">

        {/* Stats strip */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Total Roles',   value: roles.length,  icon: Shield, color: 'text-brand-500', bg: 'bg-brand-50' },
            { label: 'Team Members',  value: users.length,  icon: Users,  color: 'text-blue-500',  bg: 'bg-blue-50'  },
            { label: 'Active Users',  value: users.filter(u => u.is_active).length, icon: UserCheck, color: 'text-green-500', bg: 'bg-green-50' },
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

        {/* Tabs */}
        <div className="flex items-center gap-2 mb-5">
          {(['roles', 'members'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                tab === t
                  ? 'bg-brand-500 text-white shadow-sm'
                  : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
              }`}>
              {t === 'roles' ? (
                <span className="flex items-center gap-1.5"><Shield size={14} /> Roles</span>
              ) : (
                <span className="flex items-center gap-1.5"><Users size={14} /> Members</span>
              )}
            </button>
          ))}
          <div className="flex-1" />
          {tab === 'roles' ? (
            <button onClick={() => { setEditingRole(undefined); setShowRoleModal(true) }}
              className="flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm">
              <Plus size={15} /> New Role
            </button>
          ) : (
            <button onClick={() => { setEditingUser(undefined); setShowMemberModal(true) }}
              className="flex items-center gap-1.5 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold rounded-lg transition-colors shadow-sm">
              <Plus size={15} /> Add Member
            </button>
          )}
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
            Loading…
          </div>
        ) : tab === 'roles' ? (
          /* ── Roles tab ── */
          <div className="space-y-4">
            {roles.length === 0 ? (
              <div className="text-center py-16 text-slate-400">No roles found.</div>
            ) : (
              roles.map(role => (
                <RoleCard
                  key={role.id}
                  role={role}
                  userCount={userCountForRole(role.id)}
                  onEdit={() => { setEditingRole(role); setShowRoleModal(true) }}
                  onDelete={() => setDeleteConfirm({ type: 'role', id: role.id, name: role.name })}
                />
              ))
            )}
          </div>
        ) : (
          /* ── Members tab ── */
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Member</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Email</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">Status</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-12 text-slate-400">No members found.</td></tr>
                ) : (
                  users.map(u => (
                    <tr key={u.username} className="hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white text-xs font-bold uppercase flex-shrink-0">
                            {u.username.slice(0, 2)}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900">{u.full_name || u.username}</div>
                            <div className="text-xs text-slate-400 font-mono">@{u.username}</div>
                          </div>
                          {u.is_system && (
                            <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">
                              <Lock size={9} /> sys
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 hidden md:table-cell">{u.email || '—'}</td>
                      <td className="px-4 py-3">{roleBadge(u.role_id, getRoleName(u.role_id))}</td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.is_active ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-green-500' : 'bg-slate-400'}`} />
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => { setEditingUser(u); setShowMemberModal(true) }}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-brand-600 transition-colors"
                            title="Edit">
                            <Edit2 size={13} />
                          </button>
                          {!u.is_system && (
                            <>
                              <button
                                onClick={() => handleToggleActive(u.username, !u.is_active)}
                                className={`p-1.5 rounded transition-colors ${
                                  u.is_active
                                    ? 'hover:bg-yellow-50 text-slate-500 hover:text-yellow-600'
                                    : 'hover:bg-green-50 text-slate-500 hover:text-green-600'
                                }`}
                                title={u.is_active ? 'Deactivate' : 'Activate'}>
                                <UserCheck size={13} />
                              </button>
                              <button
                                onClick={() => setDeleteConfirm({ type: 'user', id: u.username, name: u.full_name || u.username })}
                                className="p-1.5 rounded hover:bg-red-50 text-slate-500 hover:text-red-600 transition-colors"
                                title="Delete">
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Modals ── */}
      {showRoleModal && (
        <RoleModal
          roles={roles}
          initial={editingRole}
          onSave={handleRoleSave}
          onClose={() => { setShowRoleModal(false); setEditingRole(undefined) }}
        />
      )}

      {showMemberModal && (
        <MemberModal
          roles={roles}
          initial={editingUser}
          onSave={handleMemberSave}
          onClose={() => { setShowMemberModal(false); setEditingUser(undefined) }}
          isEdit={Boolean(editingUser)}
        />
      )}

      {/* Delete confirm */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900">Confirm Delete</h3>
                <p className="text-sm text-slate-500">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-slate-700 mb-5">
              Are you sure you want to delete <strong>{deleteConfirm.name}</strong>?
              {deleteConfirm.type === 'role' && (
                <span className="text-amber-600"> Members with this role will be downgraded to Viewer.</span>
              )}
            </p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteConfirm(null)}
                className="flex-1 px-4 py-2 text-sm font-medium border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-700">
                Cancel
              </button>
              <button
                onClick={() => deleteConfirm.type === 'role'
                  ? handleRoleDelete(deleteConfirm.id)
                  : handleMemberDelete(deleteConfirm.id)}
                className="flex-1 px-4 py-2 text-sm font-semibold bg-red-500 hover:bg-red-600 text-white rounded-lg">
                Delete
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
