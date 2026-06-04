import React from 'react'

export default function ChartCard({ title, children }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      <div>{children}</div>
    </div>
  )
}
