# Design Choices for Purplle Store Intelligence

This document records the major architectural and implementation choices made for the project, explains alternatives that were considered, and records the tradeoffs that led to the final decisions. It is intended to guide future contributors when evolving or refactoring the system.

## 1. Detection model choice

Options considered:

- YOLO family (v5/v8 variants): widely used for real-time object detection, well-supported, many pre-trained weights and inference libraries.
- Faster R-CNN / Mask R-CNN: higher accuracy, especially for small objects and instance segmentation, but much higher latency and heavier compute needs.
- SSD (Single Shot Detector): a compromise between speed and accuracy; older and less performant than modern YOLO variants for similar compute budgets.
- Custom transformer-based detectors (DETR / variants): promising accuracy and end-to-end learnability but heavier and more complex to tune and deploy for real-time streaming.

Final choice:

YOLOv8-nano (supplied as `yolov8n.pt`) was selected as the primary detection model in the repository.

Why this choice:

- Real-time suitability: YOLOv8-nano is optimized for low latency, enabling near real-time inference on CPU and accelerated speed on GPU. Retail use-cases require frame-level inference at a steady rate.
- Ecosystem and tooling: YOLOv8 has good tooling for training, exporting and running inference, with many community resources and pre/post-processing libraries.
- Extensibility: the repository treats the model as a replaceable artifact. Larger or custom-trained weights can be swapped with minimal changes to the pipeline.

Tradeoffs:

- Accuracy vs latency: YOLOv8-nano trades some detection accuracy (especially for small, occluded objects) for faster inference. This is acceptable for coarse retail metrics (visits, dwell, zone transitions) but may miss subtle interactions.
- Future maintenance: relying on a specific model version ties the pipeline to that model's input/output conventions. This is mitigated by a thin adapter layer in `services/detection_service.py` and `pipeline/detect.py`.

If higher detection fidelity is required later (for example, product-level interactions from packed shelf views), a larger YOLOv8 or a two-stage detection approach can be adopted and deployed as an inference microservice.

## 2. Tracking strategy choice

Options considered:

- Simple frame-to-frame IoU + motion heuristics tracker: light-weight, easy to implement, robust for well-separated objects.
- SORT / DeepSORT: SORT (Simple Online and Realtime Tracking) provides Kalman filtering + Hungarian matching; DeepSORT adds appearance descriptors which help with re-identification across occlusions.
- Joint detection-and-tracking (e.g., Tracktor, center-based trackers): more accurate in complex scenarios but more complex to integrate and tune.

Final choice:

A pragmatic tracking layer built on IoU/motion heuristics with conservative merge/split handling (implemented in `tracker.py`) was selected.

Why this choice:

- Simplicity and robustness: retail scenes in many stores have moderate density; a heuristics-based tracker yields acceptable identity continuity with minimal configuration.
- Predictable resources: the chosen strategy is CPU-friendly and predictable, meaning simpler deployment on edge devices or modest cloud instances.
- Maintenance overhead: simpler trackers are less brittle and easier to debug when errors arise in downstream analytics.

Tradeoffs:

- Occlusions and ID switches: heuristics-based tracking is more susceptible to ID switches in dense scenes and long occlusions than DeepSORT-like approaches.
- Accuracy vs complexity: more advanced trackers provide better re-identification at the cost of appearance model management and additional compute.

If required, the project can adopt DeepSORT (or a learned appearance model) later as a drop-in replacement for the tracker module, or introduce a light re-identification step for long-term identity stability.

## 3. Event schema design

Why chosen:

- The event schema in the repository favors a compact, extensible JSON payload with canonical fields: `timestamp`, `source` (camera/zone), `session_id`, `track_id`, `event_type`, and a `payload` or `metadata` JSON blob containing bounding boxes, confidence, and derived features.
- This structure balances rigidity and flexibility: core fields are typed and indexed for efficient querying, while the `payload` allows instrumenting new detectors or features without breaking schemas.

Alternatives considered:

- Strict relational fields for every attribute (one column per attribute): easier for SQL queries but brittle and inflexible as new attributes are added.
- Fully schemaless events (arbitrary JSON): maximally flexible but harder to index and optimize for queries (performance and analytics cost).

Tradeoffs:

- Choosing a hybrid approach (typed core + JSON payload) gives the best of both worlds: good query performance for frequent fields and schema flexibility for new detectors or experimental metadata.

## 4. API architecture

Why FastAPI:

- Developer productivity: FastAPI provides concise route definitions, automatic OpenAPI documentation and type-checked request/response models that speed up development and reduce runtime errors.
- Performance: FastAPI (running on ASGI servers like Uvicorn) is performant and supports async handling for better concurrency handling for IO-bound workloads.
- Ecosystem: easy integration with Pydantic models, dependency injection and background tasks makes it a good choice for the ingestion endpoints used by the pipeline.

Why REST endpoints:

- Simplicity and interoperability: REST is well-understood, easy to debug, and works with virtually all clients and integration platforms.
- Batching support: REST endpoints can accept batched payloads for ingestion, simplifying backpressure handling when large amounts of events are emitted from the pipeline.

Alternatives considered:

- gRPC: higher performance and strongly-typed interfaces, but adds complexity for clients and testing; not necessary for initial integration.
- Event streaming (Kafka): ideal for high-throughput, decoupled systems but requires additional infrastructure and operational expertise. The repository is structured to support a future migration to event streaming.

## 5. Database design

Why relational model:

- Strong consistency and transactional semantics are helpful for storing sessions, events and metadata where correctness matters.
- Relational schemas are efficient for the typical queries used by dashboards (joins, aggregations, date-range filters) and are well-supported by tooling and ORMs present in the codebase.

Alternatives considered:

- NoSQL document stores (e.g., MongoDB): good for flexible event schemas but weaker in complex analytical joins and transactional integrity.
- Time-series databases (e.g., InfluxDB): excellent for high-resolution time-series but less suited for storing rich session objects and relational metadata.

Tradeoffs:

- Using a relational DB plus JSON fields in event rows gives both query power and flexibility; for very high event volumes, augmenting with a time-series store or an OLAP system is recommended.

## 6. Dashboard design

Why React + Recharts (or similar charting libraries):

- React is widely adopted, component-driven, and integrates well with Vite and modern frontend toolchains used in the repository.
- Recharts (or similar libraries) provides composable chart primitives that are straightforward to bind to the analytics APIs and performant enough for dashboard use-cases.

Alternatives considered:

- Full-featured visualization frameworks (e.g., D3.js directly): more flexible but significantly more development effort for standard charts.
- Commercial BI platforms: faster to build but less flexible and harder to integrate with custom event data and session semantics.

Tradeoffs:

- Choosing React + Recharts prioritizes developer productivity and maintainability while delivering interactive charts that meet the product needs. For heavy analytics workloads, server-side pre-aggregation or specialized visualization libraries can be introduced.

## 7. AI-assisted decisions made during development

- Model selection: empirical testing favored YOLOv8-nano for the common dataset and latency targets; this selection was assisted by quick profiling runs comparing model size and throughput.
- Threshold tuning: confidence and IoU thresholds were tuned using small labeled sample frames to reduce false positives in entry/dwell heuristics.
- Anomaly rules: analytics pipelines use simple statistical heuristics (Z-score over moving windows) as a first-pass anomaly detector; these were validated using historical day-of-week patterns to reduce false alerts.

These decisions were made to balance reliability, deployability, and ease of iteration. As more labeled data and operational telemetry accumulate, the repository is organized to replace heuristics with learned components or more advanced statistical models.

---

This CHOICES.md should be updated as the project matures and choices are revisited in the light of new requirements, data or operational constraints.
