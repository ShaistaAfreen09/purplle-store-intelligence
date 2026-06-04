import React, { useContext, useEffect, useState } from 'react'
import { StoreContext } from '../context/StoreContext'
import { getStoreMetrics } from '../services/api'
import ChartCard from '../components/ChartCard'
import Spinner from '../components/Spinner'

function cellColor(v) {
  // v expected 0..1
  const r = Math.round(255 * v)
  const g = Math.round(200 * (1 - v))
  return `rgb(${r}, ${g}, 40)`
}

export default function Heatmap() {
  const { storeId } = useContext(StoreContext)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getStoreMetrics(storeId)
      .then((m) => setMetrics(m))
      .finally(() => setLoading(false))
  }, [storeId])

  if (loading) return <div className="container py-8"><Spinner /></div>
  if (!metrics) return null

  // synthesize a 8x8 grid based on queue depth and abandonment rate
  const intensity = Math.min(1, metrics.queue_depth / Math.max(1, metrics.unique_visitors / 10) + metrics.abandonment_rate)
  const grid = Array.from({ length: 8 }).map(() => Array.from({ length: 8 }).map(() => Math.min(1, Math.random() * 0.6 + intensity * 0.6)))

  return (
    <div className="container py-8">
      <ChartCard title={`Heatmap - store ${storeId}`}>
        <div className="p-4">
          <div className="grid grid-cols-8 gap-1">
            {grid.flatMap((row, r) => row.map((v, c) => (
              <div key={`${r}-${c}`} className="w-full h-8 rounded" style={{ background: cellColor(v) }} />
            )))}
          </div>
          <div className="mt-4 text-sm text-gray-600">Generated heatmap using queue depth and abandonment as intensity.</div>
        </div>
      </ChartCard>
    </div>
  )
}
