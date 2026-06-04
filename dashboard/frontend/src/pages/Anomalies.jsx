import React, { useContext, useEffect, useState } from 'react'
import { StoreContext } from '../context/StoreContext'
import { getStoreAnomalies } from '../services/api'
import ChartCard from '../components/ChartCard'
import Spinner from '../components/Spinner'

function SeverityBadge({ s }) {
  const cls = s === 'CRITICAL' ? 'bg-red-100 text-red-700' : s === 'WARN' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'
  return <span className={`px-2 py-1 rounded text-xs font-medium ${cls}`}>{s}</span>
}

export default function Anomalies() {
  const { storeId } = useContext(StoreContext)
  const [anomalies, setAnomalies] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getStoreAnomalies(storeId)
      .then((d) => setAnomalies(d))
      .catch((e) => setError(e.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [storeId])

  if (loading) return <div className="container py-8"><Spinner /></div>
  if (error) return <div className="container py-8 text-red-600">{error}</div>
  if (!anomalies) return null

  return (
    <div className="container py-8">
      <div className="grid gap-4">
        {anomalies.length === 0 && <div className="text-sm text-gray-600">No anomalies detected.</div>}
        {anomalies.map((a, idx) => (
          <ChartCard key={idx} title={`${a.anomaly_type} - ${a.severity}`}>
            <div className="space-y-2">
              <div className="text-sm text-gray-700">{a.description}</div>
              <div className="text-sm text-gray-600">Suggested: {a.suggested_action}</div>
            </div>
          </ChartCard>
        ))}
      </div>
    </div>
  )
}
