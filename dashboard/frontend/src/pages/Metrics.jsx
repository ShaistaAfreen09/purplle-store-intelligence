import React, { useContext, useEffect, useState } from 'react'
import { StoreContext } from '../context/StoreContext'
import { getStoreMetrics } from '../services/api'
import ChartCard from '../components/ChartCard'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Spinner from '../components/Spinner'

export default function Metrics() {
  const { storeId } = useContext(StoreContext)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getStoreMetrics(storeId)
      .then((m) => setMetrics(m))
      .catch((e) => setError(e.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [storeId])

  if (loading) return <div className="container py-8"><Spinner /></div>
  if (error) return <div className="container py-8 text-red-600">{error}</div>
  if (!metrics) return null

  // create a synthetic timeseries for the dashboard display
  const series = Array.from({ length: 14 }).map((_, i) => ({
    day: `-${14 - i}`,
    visitors: Math.max(1, Math.round(metrics.unique_visitors * (0.7 + Math.random() * 0.6))),
    queue: Math.max(0, Math.round(metrics.queue_depth * (0.6 + Math.random() * 0.8))),
  }))

  return (
    <div className="container py-8 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="kpi">
          <div className="text-xs text-gray-500">Unique visitors</div>
          <div className="text-2xl font-semibold">{metrics.unique_visitors}</div>
        </div>
        <div className="kpi">
          <div className="text-xs text-gray-500">Conversion rate</div>
          <div className="text-2xl font-semibold">{(metrics.conversion_rate * 100).toFixed(2)}%</div>
        </div>
        <div className="kpi">
          <div className="text-xs text-gray-500">Avg dwell (ms)</div>
          <div className="text-2xl font-semibold">{Math.round(metrics.average_dwell_ms)}</div>
        </div>
        <div className="kpi">
          <div className="text-xs text-gray-500">Queue depth</div>
          <div className="text-2xl font-semibold">{metrics.queue_depth}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Visitors">
          <div style={{ height: 240 }}>
            <ResponsiveContainer>
              <LineChart data={series}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="visitors" stroke="#2563eb" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Queue depth">
          <div style={{ height: 240 }}>
            <ResponsiveContainer>
              <LineChart data={series}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="queue" stroke="#dc2626" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
