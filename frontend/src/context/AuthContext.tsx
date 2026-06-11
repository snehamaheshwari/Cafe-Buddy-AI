import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────
export interface AuthUser {
  username: string
  full_name: string
  role_id: string
  role: string          // role display name
  permissions: string[]
  token: string
}

interface AuthContextValue {
  user: AuthUser | null
  login: (data: AuthUser) => void
  logout: () => void
  hasPermission: (feature: string) => boolean
  isAdmin: () => boolean
}

// ─── Context ──────────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthContextValue>({
  user: null,
  login: () => {},
  logout: () => {},
  hasPermission: () => false,
  isAdmin: () => false,
})

// ─── Load from localStorage ───────────────────────────────────────────────────
/**
 * Reads the stored auth object.
 * IMPORTANT: If the stored object is in the OLD format (no `permissions` array
 * — from before RBAC was added) it would crash every component that calls
 * `hasPermission()`. We detect this and wipe the stale record so the user
 * is redirected to /login and gets a fresh token with the correct shape.
 */
function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem('cafe_buddy_auth')
    if (!raw) return null
    const parsed = JSON.parse(raw)
    // Must have a token
    if (!parsed?.token) return null
    // Must have a permissions array — old format has only {username, role, token}
    if (!Array.isArray(parsed.permissions)) {
      // Stale format: evict it so the user re-authenticates cleanly
      localStorage.removeItem('cafe_buddy_auth')
      return null
    }
    return parsed as AuthUser
  } catch {
    localStorage.removeItem('cafe_buddy_auth')
    return null
  }
}

// ─── Provider ─────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const login = useCallback((data: AuthUser) => {
    localStorage.setItem('cafe_buddy_auth', JSON.stringify(data))
    setUser(data)
  }, [])

  // ── Startup permission refresh ──────────────────────────────────────────────
  // On every app load, call /api/auth/me to get the server's latest permissions.
  // This fixes stale localStorage when an admin adds a new permission to a role
  // (e.g. audit_logs was added after the user's last login).
  useEffect(() => {
    const stored = loadUser()
    if (!stored) return   // not logged in — nothing to refresh

    fetch('/api/auth/me', {
      headers: {
        'X-Username': stored.username,
        'X-Role':     stored.role_id,
      },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return
        // Merge fresh permissions + role name into the stored record
        const refreshed: AuthUser = {
          ...stored,
          full_name:   data.full_name   ?? stored.full_name,
          role_id:     data.role_id     ?? stored.role_id,
          role:        data.role_name   ?? stored.role,
          permissions: data.permissions ?? stored.permissions,
        }
        localStorage.setItem('cafe_buddy_auth', JSON.stringify(refreshed))
        setUser(refreshed)
      })
      .catch(() => { /* network error — keep stale data, silent fail */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])   // run once on mount
  // ───────────────────────────────────────────────────────────────────────────

  const logout = useCallback(() => {
    localStorage.removeItem('cafe_buddy_auth')
    setUser(null)
  }, [])

  const hasPermission = useCallback(
    (feature: string) => {
      if (!user) return false
      // Defensive: permissions may be missing on a stale/malformed token
      return (user.permissions ?? []).includes(feature)
    },
    [user],
  )

  const isAdmin = useCallback(
    () => {
      if (!user) return false
      return (
        user.role_id === 'admin' ||
        (user.permissions ?? []).includes('role_management')
      )
    },
    [user],
  )

  return (
    <AuthContext.Provider value={{ user, login, logout, hasPermission, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
export function useAuth() {
  return useContext(AuthContext)
}
