import React, { useContext, useEffect, useState } from 'react'
import { StoreContext } from '../context/StoreContext'
import { getStoreFunnel } from '../services/api'
import ChartCard from '../components/ChartCard'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import Spinner from '../components/Spinner'

export default function Funnel() {
  const { storeId } = useContext(StoreContext)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getStoreFunnel(storeId)
      .then((d) => setData(d))
      .catch((e) => setError(e.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [storeId])

  if (loading) return <div className="container py-8"><Spinner /></div>
  if (error) return <div className="container py-8 text-red-600">{error}</div>
  if (!data) return null

  const chartData = data.stages.map((s, idx) => ({ name: s.stage, value: s.count, idx }))

  return (
    <div className="container py-8">
      <ChartCard title={`Funnel - store ${storeId}`}>
        <div style={{ height: 320 }}>
          <ResponsiveContainer>
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={140} />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={index % 2 ? '#60a5fa' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  )
}
