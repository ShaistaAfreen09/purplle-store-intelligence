import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE ?? ''

const api = axios.create({
  baseURL,
  timeout: 10000,
})

export async function getStoreMetrics(storeId) {
  const res = await api.get(`/stores/${storeId}/metrics`)
  return res.data
}

export async function getStoreFunnel(storeId) {
  const res = await api.get(`/stores/${storeId}/funnel`)
  return res.data
}

export async function getStoreAnomalies(storeId) {
  const res = await api.get(`/stores/${storeId}/anomalies`)
  return res.data
}

export default api
