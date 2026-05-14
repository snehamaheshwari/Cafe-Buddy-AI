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

function isAuthenticated(): boolean {
  try {
    const raw = localStorage.getItem('cafe_buddy_auth')
    if (!raw) return false
    const parsed = JSON.parse(raw)
    return Boolean(parsed?.token)
  } catch {
    return false
  }
}

function PrivateLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />
      <div className="flex-1 ml-64 min-h-screen flex flex-col">
        {children}
      </div>
    </div>
  )
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  if (isAuthenticated()) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          <PublicRoute><Login /></PublicRoute>
        } />
        <Route path="/" element={
          <PrivateLayout><Dashboard /></PrivateLayout>
        } />
        <Route path="/data-collection" element={
          <PrivateLayout><DataCollection /></PrivateLayout>
        } />
        <Route path="/data-engineering" element={
          <PrivateLayout><DataEngineering /></PrivateLayout>
        } />
        <Route path="/ai-intelligence" element={
          <PrivateLayout><AIMLIntelligence /></PrivateLayout>
        } />
        <Route path="/decision-engine" element={
          <PrivateLayout><DecisionEngine /></PrivateLayout>
        } />
        <Route path="/cafe-os" element={
          <PrivateLayout><CafeOS /></PrivateLayout>
        } />
        <Route path="/chatbot" element={
          <PrivateLayout><Chatbot /></PrivateLayout>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
