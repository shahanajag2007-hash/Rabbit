import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Alert } from './components/common/Widgets'
import AppearancePage from './pages/AppearancePage'
import AvatarPage from './pages/AvatarPage'
import CompleteLookPage from './pages/CompleteLookPage'
import FinalLookPage from './pages/FinalLookPage'
import ProfilePage from './pages/ProfilePage'
import RecommendationsPage from './pages/RecommendationsPage'
import { api } from './services/api'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function BackendStatus() {
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api.health().catch((e: Error) => setError(e.message))
  }, [])
  if (!error) return null
  return (
    <div style={{ marginBottom: '1rem' }}>
      <Alert kind="error">{error}</Alert>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="app-shell">
        <main className="block-container">
          <BackendStatus />
          <Routes>
            <Route path="/" element={<Navigate to="/profile" replace />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/appearance" element={<AppearancePage />} />
            <Route path="/avatar" element={<AvatarPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/complete-look" element={<CompleteLookPage />} />
            <Route path="/final-look" element={<FinalLookPage />} />
            <Route path="*" element={<Navigate to="/profile" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
