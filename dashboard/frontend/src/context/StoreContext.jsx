import React, { createContext, useState, useEffect } from 'react'

export const StoreContext = createContext({ storeId: 1, setStoreId: () => {} })

export function StoreProvider({ children }) {
  const [storeId, setStoreId] = useState(() => {
    try {
      const v = localStorage.getItem('storeId')
      return v ? Number(v) : 1
    } catch {
      return 1
    }
  })

  useEffect(() => {
    try { localStorage.setItem('storeId', String(storeId)) } catch {}
  }, [storeId])

  return (
    <StoreContext.Provider value={{ storeId, setStoreId }}>
      {children}
    </StoreContext.Provider>
  )
}
