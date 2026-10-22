import { Component, StrictMode, type ErrorInfo, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles.css'

if (window.location.pathname.startsWith('/.auth/')) {
  window.history.replaceState({}, '', '/')
}

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Poopr render failed', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-shell">
          <section className="empty app-error">
            <p>Poopr had trouble loading</p>
            <span>Refresh the page to try again. If it keeps happening, sign out and sign in again.</span>
            <button className="primary-action" onClick={() => window.location.assign('/')}>
              Reload Poopr
            </button>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

