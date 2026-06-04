from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.event import ChallengeEvent
from app.services.ingestion_service import ingest_events as ingest_events_service

router = APIRouter()


@router.post("/ingest")
def ingest_events(
    events: list[dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if len(events) > 500:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Maximum 500 events are allowed per request.",
        )

    valid_events: list[ChallengeEvent] = []
    errors: list[dict[str, Any]] = []
    rejected = 0

    for index, event_payload in enumerate(events):
        try:
            if not isinstance(event_payload, dict):
                raise TypeError("Each event must be a JSON object.")

            valid_events.append(ChallengeEvent.model_validate(event_payload))
        except ValidationError as exc:
            rejected += 1
            errors.append(
                {
                    "index": index,
                    "event_id": event_payload.get("event_id") if isinstance(event_payload, dict) else None,
                    "errors": exc.errors(),
                }
            )
        except TypeError as exc:
            rejected += 1
            errors.append(
                {
                    "index": index,
                    "event_id": event_payload.get("event_id") if isinstance(event_payload, dict) else None,
                    "errors": [{"type": "type_error", "msg": str(exc)}],
                }
            )

    result = ingest_events_service(db, valid_events)
    return {
        "accepted": result["accepted"],
        "duplicates": result["duplicates"],
        "rejected": rejected,
        "errors": errors,
    }
