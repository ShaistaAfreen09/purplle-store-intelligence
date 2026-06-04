# End-to-End Validation

This document summarizes the current end-to-end validation status for the Purplle Store Intelligence pipeline.
The evaluation is based on repository implementation evidence and generated CAM3 sample event output.

## Flow and Status

| Stage | Status | Notes |
|---|---|---|
| Video | PASS | `pipeline/run.py` reads video via OpenCV and sample output exists in `output/events_cam3.jsonl`. |
| Detection | PARTIAL | `pipeline/detect.py` provides a YOLOv8 wrapper, but the detection path is runtime dependent and has a fallback that can produce no detections if the model is unavailable. |
| Tracking | PASS | `pipeline/tracker.py` implements `Tracker.update()` and supports persistent track assignment. |
| Session Engine | PASS | `pipeline/sessions.py` emits ENTRY/EXIT/REENTRY and zone/queue events, with CAM3 output confirming generation of entrance and zone transition events. |
| Event Generation | PASS | `pipeline/run.py` writes structured JSONL events through `pipeline/events.py`, and `output/events_cam3.jsonl` contains 30 generated events. |
| Event Ingestion | PARTIAL | `app/api/routers/events.py` exposes `POST /events/ingest`, but there is no confirmed end-to-end ingestion of generated CAM3 JSONL into the database in the current repository evidence. |
| Metrics API | PASS | `app/api/routers/stores.py` exposes `GET /stores/{store_id}/metrics` and `app/services/metrics_service.py` computes metrics from sessions/events with unit tests. |
| Dashboard | PARTIAL | The React dashboard exists under `dashboard/frontend/` and is documented for API integration, but there is no full live UI validation captured in the repository. |

## Evidence Summary

### Video
- `pipeline/run.py` is a CLI entrypoint for processing video files.
- It uses OpenCV `cv2.VideoCapture(video_path)` to read camera input.
- `output/events_cam3.jsonl` exists and confirms pipeline execution against CAM3 sample data.

### Detection
- `pipeline/detect.py` wraps the YOLOv8 model via `ultralytics.YOLO`.
- `Detector.detect(frame)` returns detection boxes for tracker input.
- The implementation is present, but the fallback mode is a no-op when YOLO is unavailable.

### Tracking
- `pipeline/tracker.py` implements a tracking layer with `Tracker.update(detections)`.
- A simple nearest-center track assignment is used when ByteTrack is not installed.
- Tracker output flows directly into the session engine.

### Session Engine
- `pipeline/sessions.py` manages visitor sessions and emits lifecycle events.
- It handles entrance reentry logic for `CAM3`, zone transitions, queue joins, and abandon events.
- Sample CAM3 event output includes:
  - `ENTRY`: 7
  - `EXIT`: 11
  - `REENTRY`: 5
  - `ZONE_ENTER`: 4
  - `ZONE_EXIT`: 3

### Event Generation
- Generated events are serialized by `pipeline/events.py` with `EventWriter`.
- `pipeline/run.py` converts session events into structured event payloads written as JSONL.
- `output/events_cam3.jsonl` contains 30 event records.

### Event Ingestion
- `app/api/routers/events.py` implements the ingestion endpoint `POST /events/ingest`.
- Incoming payloads are validated against `app.schemas.event.ChallengeEvent`.
- Ingestion service `app.services.ingestion_service` is the expected receiver, but automated JSONL-to-API ingestion is not demonstrated in repository evidence.

### Metrics API
- `app/api/routers/stores.py` exposes `GET /stores/{store_id}/metrics`.
- `app/services/metrics_service.py` computes metrics from `VisitorSession`, `Event`, and `POSTransaction` models.
- Unit test coverage exists for metrics calculation logic.

### Dashboard
- A React dashboard is present in `dashboard/frontend/`.
- `dashboard/frontend/README.md` documents API integration and frontend pages.
- Build and serve configuration is present in `docker/Dockerfile.dashboard`, but end-to-end UI validation against backend data is not captured.

## Conclusion
The current repository supports the core end-to-end pipeline path from video input through session event generation and API metrics exposure. Key gaps remain in reliable detection model availability, automated ingestion of generated event JSONL, and documented live dashboard validation.
