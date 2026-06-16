import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DataCollection from './pages/DataCollection'
import DataEngineering from './pages/DataEngineering'
import AIMLIntelligence from './pages/AIMLIntelligence'
import DecisionEngine from './pages/DecisionEngine'
import CafeOS from './pages/CafeOS'
import Chatbot from './pages/Chatbot'
import WhatsAppNotifications from './pages/WhatsAppNotifications'
import PeerComparison from './pages/PeerComparison'
import RoleManagement from './pages/RoleManagement'
import AuditLog from './pages/AuditLog'
import TenantSettings from './pages/TenantSettings'
import WorkspaceAdmin from './pages/WorkspaceAdmin'
import { SidebarProvider } from './context/SidebarContext'
import { AuthProvider, useAuth } from './context/AuthContext'

// ─── Route-level permission guard ────────────────────────────────────────────
/**
 * Wraps a page that requires a specific permission key.
 * Redirects to "/" with a "forbidden" flash if the current user lacks it.
 * If the user is not logged in at all, redirects to /login.
 */
function PermissionRoute({
  feature,
  children,
}: {
  feature: string
  children: React.ReactNode
}) {
  const { user, hasPermission } = useAuth()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  if (!hasPermission(feature)) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

// ─── Authenticated layout wrapper ────────────────────────────────────────────
function PrivateLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return (
    <SidebarProvider>
      <div className="flex min-h-screen bg-slate-100">
        <Sidebar />
        {/* md:ml-64 pushes content right of sidebar on desktop */}
        <div className="flex-1 md:ml-64 min-h-screen flex flex-col min-w-0">
          {children}
        </div>
      </div>
    </SidebarProvider>
  )
}

// ─── Public route (redirect to home if already logged in) ────────────────────
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={
            <PublicRoute><Login /></PublicRoute>
          } />

          {/* Protected — dashboard (always accessible when logged in) */}
          <Route path="/" element={
            <PrivateLayout><Dashboard /></PrivateLayout>
          } />

          {/* Protected — feature-gated pages */}
          <Route path="/data-collection" element={
            <PrivateLayout>
              <PermissionRoute feature="upload_data">
                <DataCollection />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/data-engineering" element={
            <PrivateLayout>
              <PermissionRoute feature="reports">
                <DataEngineering />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/ai-intelligence" element={
            <PrivateLayout>
              <PermissionRoute feature="analytics">
                <AIMLIntelligence />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/decision-engine" element={
            <PrivateLayout>
              <PermissionRoute feature="decision_engine">
                <DecisionEngine />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/cafe-os" element={
            <PrivateLayout>
              <PermissionRoute feature="auto_pilot">
                <CafeOS />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/chatbot" element={
            <PrivateLayout>
              <PermissionRoute feature="chatbot">
                <Chatbot />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/peer-comparison" element={
            <PrivateLayout>
              <PermissionRoute feature="market_radar">
                <PeerComparison />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/notifications" element={
            <PrivateLayout>
              <PermissionRoute feature="whatsapp_alerts">
                <WhatsAppNotifications />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/role-management" element={
            <PrivateLayout>
              <PermissionRoute feature="role_management">
                <RoleManagement />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/audit" element={
            <PrivateLayout>
              <PermissionRoute feature="audit_logs">
                <AuditLog />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/settings" element={
            <PrivateLayout>
              <PermissionRoute feature="role_management">
                <TenantSettings />
              </PermissionRoute>
            </PrivateLayout>
          } />

          <Route path="/workspace-admin" element={
            <PrivateLayout>
              <WorkspaceAdmin />
            </PrivateLayout>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
