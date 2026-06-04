# Deployment

This repository can be deployed locally using Docker Compose for the PostgreSQL database, FastAPI backend, and React dashboard.

## Services

- `postgres`: PostgreSQL database
- `backend`: FastAPI API server
- `dashboard`: React dashboard served by Nginx

## Environment

Copy the example environment file and then customize it as needed:

```bash
cp .env.example .env
```

The following variables are supported:

- `POSTGRES_USER` — PostgreSQL user name
- `POSTGRES_PASSWORD` — PostgreSQL password
- `POSTGRES_DB` — PostgreSQL database name
- `DATABASE_URL` — database connection string for the backend
- `VITE_API_BASE` — dashboard API base URL baked into the frontend build

## Getting Started

Build and start the stack:

```bash
docker compose up --build
```

Then access:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:4173`

For detached mode:

```bash
docker compose up --build -d
```

## Notes

- The backend startup script waits for PostgreSQL and creates missing database tables automatically.
- The dashboard build uses `VITE_API_BASE` at build time; update `.env` before rebuilding to point the frontend to the correct backend host.
- If backend or frontend dependencies change, restart with `docker compose up --build`.

## Stopping

```bash
docker compose down
```
