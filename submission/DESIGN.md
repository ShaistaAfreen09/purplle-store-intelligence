# System Design for Purplle Store Intelligence

This document describes the architecture and runtime design decisions for the Purplle Store Intelligence project. It is written from the perspective of the current repository implementation and explains the main components, processing pipeline, data flows, and tradeoffs.

## 1. Problem Statement

Physical retail stores generate large volumes of CCTV video and POS/ingest events. The system's goal is to convert raw video and sensor inputs into structured events, analytics, and dashboard-ready metrics to support monitoring, anomaly detection, staff optimization, and business insights. Key non-functional requirements include near real-time processing, scalable ingestion, robust session handling across camera downtime, and the ability to extend detection models and analytics rules.

## 2. System Architecture

High-level components in the repository map to a modular, loosely-coupled architecture:

- Ingest layer: `pipeline/ingest_api.py`, `pipeline/pos_ingest.py` and `app/api/routers/*` accept events and control messages.
- Detection and preprocessing: `pipeline/detect.py` and `pipeline/detection/*` contain the video preprocessing, feature extraction, and detection orchestration.
- Model layer: YOLOv8 object detection model file (`yolov8n.pt`) and code hooks in `pipeline/detection` and `services/detection_service.py` implement the detection layer.
- Tracking & sessionization: session and tracking logic exists in `pipeline/sessions.py`, `tracker.py` and `pipeline/zones.py` for mapping detections to store zones and sessions.
- Event generation & output: `pipeline/output.py`, `app/services/ingestion_service.py`, and `app/api/routers/events.py` handle transforming detections into domain events and pushing them to downstream storage.
- Analytics engine: `analytics/engine.py`, `analytics/transformers.py` and `analytics/reporting.py` implement aggregations, metrics, and reports used by the dashboard.
- Persistence: `app/database/connection.py`, `app/database/models` and migrations provide relational storage for events, sessions and derived metrics.
- Dashboard: `dashboard/frontend` and `dashboard/backend` provide visualization and API endpoints for business users.

These components are organized to allow independent scaling: multiple detection worker processes, a stateless API layer, and a persistent database.

## 3. CCTV Processing Pipeline

Pipeline flow (as implemented under `pipeline/`):

1. Video frames or small batches arrive to the pipeline input (ingest scripts or stream producers).
2. Frames are preprocessed in `pipeline/detection/preprocess.py` (normalization, ROI cropping, resizing) to match model input requirements.
3. Feature extraction runs (`pipeline/detection/feature_extraction.py`) to compute auxiliary descriptors when needed.
4. Object detection is executed using the YOLO model (see Section 4).
5. Raw detections are fed into the tracking layer to maintain temporal identity.
6. Zone mapping and session state are applied producing events for entry/exit, dwell, and other domain-specific occurrences.
7. Events are emitted via the Event Ingestion API or written to local output adapters (`pipeline/output.py`).

This design keeps the heavy model inference and light business logic separate so that model upgrades or optimizations can be introduced with minimal changes.

## 4. YOLO Detection Layer

The repo includes `yolov8n.pt` (a YOLOv8-nano model) and there are integration points in `pipeline/detect.py` and `services/detection_service.py` to load and run the model. Characteristics:

- Inference is performed on preprocessed frames sized to the model input for predictable latency.
- The detection layer produces bounding boxes, class labels, and confidence scores which are normalized to a canonical coordinate system used by downstream components.
- The model is treated as a replaceable artifact; heavier or custom-trained weights can be swapped while keeping downstream translation code stable.

Operational notes: inference can be accelerated by batching, running GPU-backed inference, or using a specialized inference server. The codebase structures the IO so that an external inference service could replace the local model call.

## 5. Tracking Layer

The tracking layer resides in `tracker.py` and pipeline tracking modules. Its responsibilities:

- Assign persistent track IDs to detections across frames using motion and IoU heuristics.
- Produce trajectories for each tracked entity to compute dwell time and movement patterns.
- Resolve short occlusions and merge/split scenarios conservatively to avoid producing false session boundaries.

Design choices favor simplicity and stability over cutting-edge multi-object tracking; the current approach reduces class of errors seen in retail scenes (false merges, frequent ID flips) and is sufficient for analytics needs.

## 6. Session Management

Sessions represent a tracked person's interaction with the store or a zone. Sessionization is handled via `pipeline/sessions.py` and zone mapping in `pipeline/zones.py`:

- A session is created when a new track crosses an entry boundary or appears inside a monitored zone.
- Idle-time heuristics (time-based) are used to terminate sessions when a track disappears for a configurable timeout.
- Sessions aggregate detections, dwell, and events into a contiguous object that is persisted to the database when finalized.

The session model supports resilience to short camera interruptions by keeping soft-state in-memory with periodic persistence.

## 7. Event Generation

Events are domain objects (entry, exit, dwell, anomaly, product-interaction) created from session and tracking signals. The event generation code lives in the pipeline and `app/services` layers. Key points:

- Events are normalized with timestamps, source identifiers (camera, zone), track/session ID, and metadata such as bounding box, confidence, and derived features.
- Events are generated deterministically from pipeline rules so replaying the same frame sequence yields identical events.

Events are intentionally small and extensible to support downstream analytics and ingestion.

## 8. Event Ingestion API

The repository includes an API surface under `app/api/routers` (notably `events.py`, `analytics.py`, `stores.py`) and `app/api/main.py` to accept events and other domain requests. The ingestion API:

- Exposes endpoints for batched event ingestion and health checks.
- Validates and transforms incoming payloads into internal event models and forwards them to the ingestion service (`app/services/ingestion_service.py`).
- Supports synchronous and asynchronous ingestion backends allowing immediate acks while persisting in the background.

Security, authentication and rate limiting are left to deployment-level concerns (reverse proxies or API gateways).

## 9. Analytics Engine

Analytics is implemented in `analytics/engine.py`, with transformer and reporting helpers. Responsibilities:

- Aggregate event streams into windowed metrics (per minute/hour/day), funnels, and anomaly statistics.
- Support KPI computation such as visits, average dwell, conversion across zones, and staff-response times.
- Provide programmatic APIs consumed by the dashboard backend (`dashboard/backend`) or exported reports in `analytics/reporting.py`.

The engine is designed to be run both as a scheduled batch and an online aggregator to meet different latency requirements.

## 10. Dashboard Architecture

The dashboard splits into a backend and frontend under `dashboard/`. The frontend is a Vite + Tailwind app (`dashboard/frontend`) that calls the backend for metrics, events and visualization tiles. The backend provides API endpoints to query aggregated analytics and ad-hoc event queries. This separation allows independent deployment and scaling.

## 11. Database Design

Persistent storage is implemented via `app/database` and `app/database/models`. Main entities:

- Event: timestamp, source (camera/zone), session_id, track_id, event_type, payload (JSON).
- Session: session_id, start_ts, end_ts, track_history, summary fields (dwell, interactions).
- Zone and Store metadata: configured zones from `config/store_zones.yaml` and store-level info.

Relational tables are used for ACID guarantees; event payloads are JSON for schema flexibility. Indexes should be added on timestamps, session_id and camera_id for efficient queries.

## 12. AI-Assisted Decisions

The system supports AI-assisted decisions at multiple layers:

- Detection model improvements (replace `yolov8n.pt` with a domain-tuned model).
- Analytics-driven alarms (statistical models in `analytics/` to detect anomalies).
- Business-rule suggestions in the dashboard driven by historical patterns (e.g., staffing recommendations).

Models and rules are realized as replaceable modules so experimentation can be done without touching the core pipeline.

## 13. Tradeoffs

- Latency vs accuracy: Using YOLOv8-nano prioritizes lower latency at some accuracy cost. The architecture allows switching to larger models as needed.
- Statefulness vs scalability: Sessionization keeps soft in-memory state to be simple and fast, but this makes horizontal scaling more complex. A recommended future improvement is moving session state to a distributed store (Redis).
- Simplicity vs sophistication in tracking: Current tracker favors robustness over SOTA accuracy. For complex occlusions, a more advanced multi-object tracker could be integrated.

## 14. Future Improvements

- Replace in-process model inference with an inference microservice to scale GPU usage and allow A/B testing of models.
- Move session state to a distributed cache (Redis) to allow stateless workers and better resilience.
- Add authentication/authorization to API endpoints and use TLS by default.
- Introduce event streaming (Kafka) to decouple producers from consumers and enable replay and robust backpressure handling.
- Improve the analytics engine with a streaming framework (e.g., Flink or Spark Structured Streaming) for at-scale continuous metrics.

---

This DESIGN.md is intended to be a living document and should be updated as the repository evolves, particularly when the detection, tracking or analytics approaches change.
