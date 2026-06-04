# purplle-store-intelligence

AI-powered Store Intelligence System for Purplle — Tech Challenge 2026

This repository implements a modular pipeline that converts CCTV video and POS/ingest events into structured session and event data, supporting analytics, anomaly detection, and a web dashboard for visualization.

## Architecture Overview

The system is organized into clear, independently deployable components:

- Ingest & API: `app/api` exposes REST endpoints for event ingestion, health checks and analytics queries.
- Detection & Pipeline: `pipeline/` contains modules for frame preprocessing, detection orchestration, tracking, sessionization and event output.
- Model: A YOLOv8-nano object detection weight (`yolov8n.pt`) is included for inference; model integration points live in `pipeline/detect.py` and `app/services/detection_service.py`.
- Analytics: `analytics/` implements aggregations, transformers and reporting used to power KPIs and dashboard tiles.
- Persistence: `app/database` contains DB connection helpers, models and migration scaffolding for storing events and sessions.
- Dashboard: `dashboard/frontend` (Vite + React + Tailwind) and `dashboard/backend` provide the UI and API surface for visualization.

This separation allows independent scaling: detection workers can be scaled separately from stateless API servers and persistent storage.

## Setup Instructions

Prerequisites:

- Python 3.10+ (the project uses pyproject/requirements for dependency management)
- Node.js 18+ (for the dashboard frontend)
- Docker (optional, for containerized runs)

Quick start (virtualenv):

1. Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

2. Install frontend dependencies (optional if you only run backend):

```bash
cd dashboard/frontend
npm install
cd -
```

3. Configure database environment variables or use `docker-compose` described in `DEPLOYMENT.md` for a ready-made Postgres setup.

Note: The repository includes `yolov8n.pt` for local inference. For production, consider using a GPU-backed inference service or larger model weights.

## Running the Pipeline

The `pipeline/` directory contains scripts to run detection and event generation. Typical steps:

- Produce frames or point the pipeline at a video source.
- Run the pipeline script (example entrypoints: `pipeline/run.py`, `pipeline/detect.py` — consult the file headers for usage).

Example (local development):

```bash
# Run a simple pipeline ingestion (adapt flags in pipeline/run.py)
python -m pipeline.run --source samples/video.mp4 --output events.json
```

The pipeline performs preprocessing, YOLO inference, tracking, sessionization and emits events to `pipeline/output.py` or to the configured ingestion endpoint.

## Running the Backend

The backend API is implemented with FastAPI under `app/api`.

Run locally with Uvicorn:

```bash
export APP_SETTINGS=app.api.main:app
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API exposes ingestion endpoints (see `app/api/routers/events.py`), analytics endpoints and health checks. Use `http://localhost:8000/docs` for interactive OpenAPI documentation when running locally.

## Running the Dashboard

The dashboard lives in `dashboard/frontend` and talks to `dashboard/backend` for aggregated data.

Run the frontend in development mode:

```bash
cd dashboard/frontend
npm run dev
```

Run the backend for the dashboard (if provided): see `dashboard/backend/README.md` for backend-specific instructions. The frontend expects the backend to provide analytics endpoints that mirror the data produced by `analytics/engine.py`.

## Running Tests

Unit and integration tests are under `tests/` and `pipeline/tests`.

Run the full test suite (recommended in the virtualenv):

```bash
pytest -q
```

You can run individual test modules, for example:

```bash
pytest tests/unit/test_api.py -q
```

Note: Some tests may expect a running database or certain environment variables; inspect `pytest.ini` and the tests for details.

## Project Structure

Top-level layout (high-level):

- `app/` — FastAPI app, routers, services, database models and migrations.
- `pipeline/` — video ingest, detection orchestration, tracking, sessions and output adapters.
- `analytics/` — aggregation engine, transformers, and reporting.
- `dashboard/` — frontend and backend code for visualization.
- `scripts/` — helper scripts for development and deployment.
- `tests/` — unit and integration tests.
- `yolov8n.pt` — included YOLOv8-nano model weights for local testing.

See the repository for more granular module boundaries and implementation details.

## Future Work

Planned improvements and recommended next steps:

- Move session soft-state into a distributed cache (Redis) to allow stateless pipeline workers and easier horizontal scaling.
- Replace in-process inference with a GPU-backed inference microservice to support larger models and A/B testing.
- Add an event-streaming layer (Kafka) to decouple producers and consumers and enable high-throughput event replay.
- Harden production deployment: add authentication, rate-limiting, tracing and SLO-driven monitoring.
- Improve tracking accuracy by integrating appearance-based re-identification (DeepSORT) for dense or occluded scenes.
- Expand end-to-end tests that spin up a test database and exercise the full pipeline + API + dashboard stack.

---

For deeper design rationale, see `DESIGN.md` and `CHOICES.md` which document architecture decisions, tradeoffs and alternatives considered during development.

If you need help running any component or want the project packaged into container images, tell me which component and I'll provide the exact commands or Dockerfile changes.

