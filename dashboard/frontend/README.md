# Dashboard Frontend (React)

This folder contains a Vite + React + Tailwind + Recharts dashboard that integrates with the FastAPI backend.

Quick start:

```bash
cd dashboard/frontend
npm install
npm run dev
```

Environment:
- Set `VITE_API_BASE` to the backend base URL (defaults to same origin). Example: `VITE_API_BASE=http://localhost:8000`.

Pages:
- Overview — KPIs and quick charts
- Metrics — detailed metrics
- Funnel — funnel stages
- Heatmap — synthesized heatmap from metrics
- Anomalies — anomaly list from API
