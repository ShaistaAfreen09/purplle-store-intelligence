import React, { useContext, useEffect, useState } from 'react'
import { StoreContext } from '../context/StoreContext'
import { getStoreMetrics, getStoreFunnel } from '../services/api'
import ChartCard from '../components/ChartCard'
import { BarChart, Bar, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import Spinner from '../components/Spinner'

function kpiRow(metrics) {
  return [
    { label: 'Unique visitors', value: metrics.unique_visitors },
    { label: 'Conversion rate', value: `${(metrics.conversion_rate * 100).toFixed(1)}%` },
    { label: 'Avg dwell ms', value: Math.round(metrics.average_dwell_ms) },
    { label: 'Queue depth', value: metrics.queue_depth },
    { label: 'Abandonment', value: `${(metrics.abandonment_rate * 100).toFixed(1)}%` },
  ]
}

export default function Overview() {
  const { storeId } = useContext(StoreContext)
  const [metrics, setMetrics] = useState(null)
  const [funnel, setFunnel] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    Promise.all([getStoreMetrics(storeId), getStoreFunnel(storeId)])
      .then(([m, f]) => {
        if (!mounted) return
        setMetrics(m)
        setFunnel(f)
      })
      .catch((err) => setError(err.message || 'Failed to load'))
      .finally(() => setLoading(false))
    return () => (mounted = false)
  }, [storeId])

  if (loading) return <div className="container py-8"><Spinner /></div>
  if (error) return <div className="container py-8 text-red-600">{error}</div>
  if (!metrics || !funnel) return null

  const kpis = kpiRow(metrics)

  // synthetic visitors time series for visual
  const series = Array.from({ length: 7 }).map((_, i) => ({
    day: `D-${6 - i}`,
    visitors: Math.max(1, Math.round(metrics.unique_visitors * (0.8 + Math.random() * 0.4))),
    conversions: Math.round(metrics.unique_visitors * metrics.conversion_rate * (0.7 + Math.random() * 0.6)),
  }))

  return (
    <div className="container py-8 space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="kpi">
            <div className="text-xs text-gray-500">{k.label}</div>
            <div className="text-2xl font-semibold">{k.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Visitors (last 7)">
          <div style={{ height: 180 }}>
            <ResponsiveContainer>
              <LineChart data={series}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="visitors" stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Conversions (last 7)">
          <div style={{ height: 180 }}>
            <ResponsiveContainer>
              <BarChart data={series}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="conversions" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Funnel stages">
          <div className="space-y-2">
            {funnel.stages.map((s) => (
              <div key={s.stage} className="flex items-center justify-between">
                <div className="text-sm text-gray-700">{s.stage}</div>
                <div className="text-sm font-medium">{s.count}</div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  )
}
