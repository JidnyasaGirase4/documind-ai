import { BrowserRouter, HashRouter } from 'react-router-dom'
import { DEMO } from './demo/config'
import { DemoBanner } from './demo/DemoBanner'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import AppRoutes from './routes/AppRoutes'

// GitHub Pages has no fallback to index.html, so the demo uses #/ routes.
const Router = DEMO ? HashRouter : BrowserRouter

export default function App() {
  return (
    <Router>
      <DemoBanner />
      <ToastProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ToastProvider>
    </Router>
  )
}
