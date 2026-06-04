from __future__ import annotations

from typing import Iterable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models.models import Event
from app.schemas.event import ChallengeEvent

MAX_BATCH_SIZE = 500


def _event_payload(event: ChallengeEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "store_id": event.store_id,
        "camera_id": event.camera_id,
        "visitor_id": event.visitor_id,
        "event_type": event.event_type.value,
        "event_time": event.timestamp,
        "zone_id": event.zone_id,
        "dwell_ms": event.dwell_ms,
        "is_staff": event.is_staff,
        "confidence": event.confidence,
        "event_metadata": event.metadata,
    }


def ingest_events(db: Session, events: list[ChallengeEvent]) -> dict[str, int]:
    if len(events) > MAX_BATCH_SIZE:
        raise ValueError(f"A maximum of {MAX_BATCH_SIZE} events can be ingested in one request.")

    unique_events: dict[str, ChallengeEvent] = {}
    duplicates = 0

    for event in events:
        if event.event_id in unique_events:
            duplicates += 1
            continue
        unique_events[event.event_id] = event

    if not unique_events:
        return {"accepted": 0, "duplicates": duplicates, "rejected": 0, "errors": []}

    records = [_event_payload(event) for event in unique_events.values()]
    stmt = insert(Event).values(records).on_conflict_do_nothing(index_elements=["event_id"])
    result = db.execute(stmt)
    db.commit()

    inserted = int(result.rowcount or 0)
    duplicates += len(records) - inserted

    return {"accepted": inserted, "duplicates": duplicates, "rejected": 0, "errors": []}
