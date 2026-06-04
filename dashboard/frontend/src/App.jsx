import React, { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import { StoreProvider } from './context/StoreContext'
import Spinner from './components/Spinner'

const Overview = lazy(() => import('./pages/Overview'))
const Metrics = lazy(() => import('./pages/Metrics'))
const Funnel = lazy(() => import('./pages/Funnel'))
const Heatmap = lazy(() => import('./pages/Heatmap'))
const Anomalies = lazy(() => import('./pages/Anomalies'))

export default function App() {
  return (
    <StoreProvider>
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <main className="flex-1">
          <Suspense fallback={<div className="container py-8"><Spinner /></div>}>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/metrics" element={<Metrics />} />
              <Route path="/funnel" element={<Funnel />} />
              <Route path="/heatmap" element={<Heatmap />} />
              <Route path="/anomalies" element={<Anomalies />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="py-4 text-center text-sm text-gray-500">Purplle Store Intelligence</footer>
      </div>
    </StoreProvider>
  )
}
