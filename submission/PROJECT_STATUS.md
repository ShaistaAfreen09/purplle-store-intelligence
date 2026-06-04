# Project Status Report

- Repository: purplle-store-intelligence
- Audit date: 2026-05-30
- Scope: FastAPI backend, analytics services, CCTV pipeline, dashboard, tests, Docker assets.

This file is an audit-only snapshot of the repository state at the time of writing. No code was modified as part of this report.

---

## Implemented APIs

- Health: simple health endpoint — `app/api/routers/health.py`
- Events ingestion: POST `/events/ingest` with validation + idempotent insertion — `app/api/routers/events.py` and ingestion logic in `app/services/ingestion_service.py`
- Store metrics: GET `/stores/{id}/metrics` — `app/api/routers/stores.py` → service `app/services/metrics_service.py`
- Store funnel: GET `/stores/{id}/funnel` — `app/api/routers/stores.py` → service `app/services/funnel_service.py`
- Store anomalies: GET `/stores/{id}/anomalies` — `app/api/routers/anomalies.py` → service `app/services/anomaly_service.py`
- App entry: FastAPI application wiring — `app/api/main.py`

## Implemented Services

- Ingestion service: idempotent batch insert, dedupe by `event_id` — `app/services/ingestion_service.py`
- Metrics service: unique visitors, conversion, average dwell, queue metrics — `app/services/metrics_service.py`
- Funnel service: stage counts & conversion/dropoff — `app/services/funnel_service.py`
- Anomaly service: anomaly detection algorithms (QUEUE_SPIKE / CONVERSION_DROP / DEAD_ZONE / STALE_FEED) — `app/services/anomaly_service.py`
- Dashboard / analytics / detection service placeholders: present but stubbed — `app/services/dashboard_service.py`, `app/services/analytics_service.py`, `app/services/detection_service.py`

## Implemented Detection / Pipeline Modules

- Detector wrapper: YOLOv8 wrapper with graceful fallback — `pipeline/detect.py`
- Tracker: Simple tracker with ByteTrack-best-effort fallback — `pipeline/tracker.py`
- Zone manager: polygon zones loader and point-in-polygon — `pipeline/zones.py` and config `config/store_zones.yaml`
- Session manager / events pipeline: session tracking, ENTRY/EXIT/REENTRY, queue events, shelf-interaction heuristics, zone events and JSONL writer — `pipeline/sessions.py` and `pipeline/events.py`
- Runner: CLI to run detection → tracking → sessions and write JSONL — `pipeline/run.py`
- Automated JSONL → ingestion API connector: `pipeline/ingest_api.py` can post generated event JSONL into `/events/ingest` in configurable batches.
- Event schema / ingestion compatibility: pipeline and API now accept optional `zone_id` and `dwell_ms` for events that do not carry measurement values.
- POS transaction ingestion: CSV parser and PURCHASE event generator — `pipeline/pos_ingest.py`
- Analytics helper: simple post-hoc queue metrics reader — `pipeline/analytics.py`
- Detection subsystem placeholders: feature extraction / preprocess / ingest modules exist as stubs under `pipeline/detection/`

## Implemented Dashboard Pages

- Frontend scaffolding: minimal Vue placeholders for dashboard and components — `dashboard/frontend/src/App.vue`, `dashboard/frontend/src/components/Dashboard.vue`, `dashboard/frontend/src/components/ReportCard.vue`
- Backend README: placeholder integration docs — `dashboard/backend/README.md`
- Status: dashboard files are UI placeholders (not wired to backend APIs)

## Implemented Tests

- Unit tests: multiple unit test files present under `tests/unit/` (metrics, funnel, anomalies, ingestion, etc.)
- Integration test: an E2E smoke test now exists under `tests/integration/test_end_to_end.py` and validates JSONL ingestion through the API plus metrics retrieval.
- Pipeline tests: pipeline test stubs under `pipeline/tests/`
- Status: a mix of real tests and placeholders; analytics & anomaly unit tests exist, but many test files are placeholders
- Regression coverage added for optional `zone_id` and `dwell_ms` ingestion payloads.

## Docker Status

- Dockerfiles: production-ready service images are implemented for backend and dashboard — `docker/Dockerfile.backend`, `docker/Dockerfile.dashboard`
- Compose files: root `docker-compose.yml` now defines PostgreSQL, backend, and dashboard services with environment-driven configuration
- Scripts: startup/migrate/run scripts remain placeholders under `scripts/`
- Status: containerization is implemented for local deployment, but CI and cloud production orchestration are still missing

## Missing Challenge Requirements / Gaps

- Staff detection / marking: pipeline currently defaults `is_staff=False`; no staff classifier or whitelist present. This is required for accurate metrics exclusion.
- Per-camera calibration / meters↔pixels mapping: `pixels_per_meter` is a hard-coded default in `SessionManager`; no per-camera calibration or normalized polygons in `config/store_zones.yaml`.
- Normalized zone coordinates: zones are pixel-based in `config/store_zones.yaml`; not normalized for differing resolutions.
- E2E pipeline integration tests: an end-to-end smoke test now exists for JSONL ingestion and metrics retrieval, but detector→tracker→sessions sample-video coverage is still missing.
- Dashboard integration: dashboard UI is placeholder and not wired to backend endpoints.
- Robust deployment artifacts / CI: Dockerfiles/compose are implemented for local stack deployment; no CI workflows or cloud production configs are present.
- Staff-aware pipeline events: no mechanism to mark events as staff before ingestion; will affect analytics that exclude staff.
- Detailed queue analytics: basic queue join/abandon implemented; further metrics (service/completion events, per-server throughput, SLA thresholds) absent.
- Persisted pipeline→DB integration: automated JSONL → ingestion API connector now exists, but full runtime orchestration with a live backend service still needs end-to-end smoke testing.

## Broken / Risky Code Paths

- `dwell_ms` and `zone_id` payload compatibility: the event schema and database model now support optional values for event types that do not include those fields (e.g., ENTRY, REENTRY, ZONE_ENTER).
- YOLO / ByteTrack optional dependency fallbacks: `pipeline/detect.py` and `pipeline/tracker.py` gracefully fallback to no-op detector / simple tracker — safe for import, but detection quality depends on environment setup and installation of optional packages.
- Placeholder docker-compose files may be referenced by scripts: attempting to run container-based scripts will fail because compose files are placeholders / empty.
- Stubbed modules: analytics/detection/dashboard service modules are placeholders; invoking these production flows will not function.

## Placeholder Files / Stubs (non-exhaustive)

- `app/services/analytics_service.py` — placeholder
- `app/services/dashboard_service.py` — placeholder
- `app/services/detection_service.py` — placeholder
- `analytics/*` — engine, transformers, reporting largely placeholder (`analytics/engine.py`, `analytics/transformers.py`, `analytics/reporting.py`)
- `dashboard/frontend/*` — UI placeholders
- `docker/*` — Dockerfile placeholders and compose stubs
- `tests/*` — several test files are placeholders (pipeline, dashboard, API stubs)

## Estimated Completion

- Backend API endpoints + core analytics services (metrics, funnel, anomalies, ingestion): largely implemented — ~75% complete.
- Pipeline (detection/tracking/sessions + event output): core logic implemented with heuristics (ENTRY/EXIT/REENTRY, queue, shelf) — ~70% complete (needs calibration, staff detection, robust detector integration, and E2E tests).
- Dashboard & UX, containerization, CI, and deployment: scaffolding only — ~10% complete.
- Overall repository estimated completion: ~60%.

## Actionable Recommendations (next priorities)

1. Add staff detection / staff marking into the pipeline (config-driven or ML-based) so backend metrics correctly exclude staff.
2. Make zone polygons resolution-independent (normalize 0..1 or store per-camera resolution) and add per-camera pixels↔meters calibration.
3. Harden ingestion: ensure `dwell_ms` and other non-null DB columns are sanitized before DB insert (coerce `None` → `0` or make columns nullable where appropriate).
4. Add E2E smoke tests covering a short sample video to validate detector→tracker→session→ingest flow.
5. Implement minimal Dockerfiles + compose for running backend + DB + pipeline in dev; add CI to run unit tests.
6. Wire dashboard to backend via a small API client and add basic reports (metrics & funnel).

## Next Options

If requested, the following follow-ups are available:

- (A) Produce a repository `PROJECT_STATUS.md` (this file) — completed.
- (B) Implement one priority (examples: make `dwell_ms` nullable / fix ingestion sanitization; add per-camera `pixels_per_meter` config; add unit tests for pipeline flows).

---

End of report.
