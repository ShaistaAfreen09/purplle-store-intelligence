import React, { useContext } from 'react'
import { NavLink } from 'react-router-dom'
import { StoreContext } from '../context/StoreContext'

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-gray-200' : 'hover:bg-gray-100'}`
      }
    >
      {children}
    </NavLink>
  )
}

export default function NavBar() {
  const { storeId, setStoreId } = useContext(StoreContext)

  return (
    <header className="bg-white shadow">
      <div className="container flex items-center justify-between h-16">
        <div className="flex items-center gap-6">
          <div className="text-lg font-semibold">Purplle Store Dashboard</div>
          <nav className="flex items-center space-x-1">
            <NavItem to="/">Overview</NavItem>
            <NavItem to="/metrics">Metrics</NavItem>
            <NavItem to="/funnel">Funnel</NavItem>
            <NavItem to="/heatmap">Heatmap</NavItem>
            <NavItem to="/anomalies">Anomalies</NavItem>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">Store</label>
          <input
            type="number"
            min="1"
            value={storeId}
            onChange={(e) => setStoreId(Number(e.target.value || 1))}
            className="w-20 px-2 py-1 border rounded-md"
            aria-label="Store id"
          />
        </div>
      </div>
    </header>
  )
}
