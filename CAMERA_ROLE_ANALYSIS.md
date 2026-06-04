# Camera Role Analysis

This analysis reviews the repository configuration and sample CAM3 event dataset to infer roles for all available cameras.

## Evidence sources

- `config/store_zones.yaml`
- `pipeline/sessions.py`
- `output/events_cam3.jsonl`

There are no video contents directly inspected in this repository, so the role assignments are derived from the existing camera zone definitions and session/event logic.

## Camera role summary

| Camera | Role | Confidence | Justification | Expected event types |
|---|---|---|---|---|
| CAM1 | Shelf interaction (skincare merchandising) | High | `config/store_zones.yaml` maps CAM1 to `SKINCARE`; `pipeline/sessions.py` treats `SKINCARE` zones as shelf interaction areas. | `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, possibly `BILLING_QUEUE_JOIN` if checkout path is reached downstream. |
| CAM2 | Shelf interaction (cosmetics merchandising) | High | `config/store_zones.yaml` maps CAM2 to `COSMETICS`; `pipeline/sessions.py` includes `COSMETICS` in shelf interaction tracking. | `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `ZONE_DWELL`, possibly `BILLING_QUEUE_JOIN` if checkout path is reached downstream. |
| CAM3 | Entrance camera | Very high | Explicit `ENTRANCE` zone in config, special-case `CAM3` reentry logic in `pipeline/sessions.py`, and sample events show entrance session patterns. | `ENTRY`, `EXIT`, `REENTRY`, `ZONE_ENTER`, `ZONE_EXIT` |
| CAM4 | Staff / backroom / non-customer traffic | Medium | Configured as `STAFF_ONLY` in `config/store_zones.yaml`; no special queue or shelf logic applies in `pipeline/sessions.py`. | likely `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT` for staff movement; not expected to generate customer queue/shelf analytics. |
| CAM5 | Billing / checkout camera | Very high | Mapped to `CHECKOUT` in config; checkout zone type is used by session logic to emit queue join and abandon events. | `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `BILLING_QUEUE_JOIN`, `BILLING_QUEUE_ABANDON` |

## Camera-by-camera analysis

### CAM1 — Shelf interaction camera

- Role: `SKINCARE` merchandising camera.
- Confidence: **High**.
- Justification:
  - `config/store_zones.yaml` defines CAM1 as a full-frame `SKINCARE` zone.
  - `pipeline/sessions.py` treats `SKINCARE` zones as shelf interaction areas for dwell detection.
- Expected event types:
  - `ENTRY`, `EXIT` (visitor presence in view)
  - `ZONE_ENTER`, `ZONE_EXIT` (zone transitions)
  - `ZONE_DWELL` or shelf dwell-related events as soon as the detector remains in a merchandising zone.

### CAM2 — Shelf interaction camera

- Role: `COSMETICS` merchandising camera.
- Confidence: **High**.
- Justification:
  - `config/store_zones.yaml` maps CAM2 to a `COSMETICS` zone.
  - `pipeline/sessions.py` includes `COSMETICS` in the same interaction classification as `SKINCARE`.
- Expected event types:
  - `ENTRY`, `EXIT`
  - `ZONE_ENTER`, `ZONE_EXIT`
  - `ZONE_DWELL` or shelf interaction events for sustained presence in cosmetics area.

### CAM3 — Entrance camera

- Role: `ENTRANCE` camera.
- Confidence: **Very high**.
- Justification:
  - explicit `ENTRANCE` zone definition in `config/store_zones.yaml`.
  - `pipeline/sessions.py` contains special-case logic for `self.camera_id == "CAM3"` to detect reentry and emit `ENTRY`/`REENTRY` immediately.
  - observed event sample `output/events_cam3.jsonl` includes only entrance-related events and no checkout queue events.
- Expected event types:
  - `ENTRY`
  - `EXIT`
  - `REENTRY`
  - `ZONE_ENTER`
  - `ZONE_EXIT`

### CAM4 — Staff camera / non-customer area

- Role: `STAFF_ONLY` / staff movement camera.
- Confidence: **Medium**.
- Justification:
  - config labels CAM4 as `STAFF_ONLY`.
  - the pipeline has no explicit `staff` classification logic, but `STAFF_ONLY` is not in shelf or checkout zone type groups used for queue or merchandising analytics.
- Expected event types:
  - likely `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT` for staff movement
  - not expected to generate customer-facing queue or shelf interaction events unless reused for customer tracking.

### CAM5 — Billing / checkout camera

- Role: `CHECKOUT` camera.
- Confidence: **Very high**.
- Justification:
  - `config/store_zones.yaml` maps CAM5 to a `CHECKOUT` zone.
  - `pipeline/sessions.py` emits `BILLING_QUEUE_JOIN` and `BILLING_QUEUE_ABANDON` specifically when a track enters and leaves a `CHECKOUT` zone.
- Expected event types:
  - `ENTRY`, `EXIT`
  - `ZONE_ENTER`, `ZONE_EXIT`
  - `BILLING_QUEUE_JOIN`
  - `BILLING_QUEUE_ABANDON`

## Expected event role mapping

- **Entrance camera:** CAM3
- **Billing camera:** CAM5
- **Shelf interaction cameras:** CAM1 and CAM2
- **Low-value / staff-only camera:** CAM4

## Confidence grading notes

- `Very high` confidence for CAM3 and CAM5 because the repository explicitly encodes their roles both in config and pipeline logic.
- `High` confidence for CAM1 and CAM2 based on merchandising zone types and shelf interaction logic.
- `Medium` confidence for CAM4 because the role is defined but the pipeline does not appear to generate dedicated staff-only analytics.

## Conclusion

The repository’s existing configuration strongly supports the following camera role assignments:

- **CAM1** — shelf/merchandising camera for skincare interactions
- **CAM2** — shelf/merchandising camera for cosmetics interactions
- **CAM3** — entrance camera with session entry/reentry focus
- **CAM4** — staff-only / low-value traffic camera
- **CAM5** — checkout/billing camera responsible for queue analytics

This analysis is based on current camera zone definitions, session logic, and the available CAM3 event dataset. No code was generated or executed as part of this analysis.
