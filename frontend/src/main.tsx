import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// ─── Top-level Error Boundary ─────────────────────────────────────────────────
// Catches any unhandled render crash and shows a readable message
// instead of a blank white page.
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  handleReset = () => {
    // Clear any stale auth state and reload
    try { localStorage.removeItem('cafe_buddy_auth') } catch {}
    window.location.href = '/'
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: '#0f172a', padding: '2rem',
        }}>
          <div style={{
            background: '#1e293b', borderRadius: '1rem', padding: '2rem',
            maxWidth: '480px', width: '100%', textAlign: 'center',
            border: '1px solid #334155',
          }}>
            <div style={{
              width: '56px', height: '56px', background: '#ef4444',
              borderRadius: '50%', display: 'flex', alignItems: 'center',
              justifyContent: 'center', margin: '0 auto 1rem',
              fontSize: '1.5rem',
            }}>⚠</div>
            <h1 style={{ color: '#f1f5f9', fontSize: '1.25rem', marginBottom: '0.5rem' }}>
              Something went wrong
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
              {this.state.error.message}
            </p>
            <button
              onClick={this.handleReset}
              style={{
                background: '#3b82f6', color: '#fff', border: 'none',
                borderRadius: '0.5rem', padding: '0.625rem 1.5rem',
                fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer',
              }}
            >
              Clear session & reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
