import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import PublicLayout from '../layouts/PublicLayout'
import AppLayout from '../layouts/AppLayout'
import ProtectedRoute from './ProtectedRoute'
import Landing from '../pages/public/Landing'
import Login from '../pages/public/Login'
import Register from '../pages/public/Register'
import NotFound from '../pages/public/NotFound'

const Features = lazy(() => import('../pages/public/Features'))
const HowItWorks = lazy(() => import('../pages/public/HowItWorks'))
const About = lazy(() => import('../pages/public/About'))
const Dashboard = lazy(() => import('../pages/app/Dashboard'))
const Documents = lazy(() => import('../pages/app/Documents'))
const DocumentDetails = lazy(() => import('../pages/app/DocumentDetails'))
const ReviewCenter = lazy(() => import('../pages/app/ReviewCenter'))
const SearchPage = lazy(() => import('../pages/app/Search'))
const KnowledgeBase = lazy(() => import('../pages/app/KnowledgeBase'))
const CollectionDetails = lazy(() => import('../pages/app/CollectionDetails'))
const Assistant = lazy(() => import('../pages/app/Assistant'))
const History = lazy(() => import('../pages/app/History'))
const Analytics = lazy(() => import('../pages/app/Analytics'))
const Settings = lazy(() => import('../pages/app/Settings'))

function Fallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" role="status">
      <Loader2 className="h-6 w-6 animate-spin text-brand-600" aria-hidden="true" />
      <span className="sr-only">Loading…</span>
    </div>
  )
}

export default function AppRoutes() {
  return (
    <Suspense fallback={<Fallback />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Landing />} />
          <Route path="/features" element={<Features />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/about" element={<About />} />
        </Route>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/app" element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="documents" element={<Documents />} />
            <Route path="documents/:documentId" element={<DocumentDetails />} />
            <Route path="reviews" element={<ReviewCenter />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="knowledge" element={<KnowledgeBase />} />
            <Route path="knowledge/collections/:collectionId" element={<CollectionDetails />} />
            <Route path="assistant/:conversationId?" element={<Assistant />} />
            <Route path="history" element={<History />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
