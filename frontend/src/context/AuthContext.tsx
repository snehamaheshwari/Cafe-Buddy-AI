import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

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
