"""Event generation and JSONL writer."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
from typing import Optional, Dict, Any
import uuid


@dataclass
class Event:
    event_id: str
    store_id: int
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str]
    dwell_ms: Optional[int]
    is_staff: bool
    confidence: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventWriter:
    def __init__(self, path: str):
        self.path = path
        self.fp = open(path, "w", encoding="utf-8")

    def write(self, event: Event) -> None:
        self.fp.write(json.dumps(event.to_dict(), default=str) + "\n")
        self.fp.flush()

    def close(self) -> None:
        try:
            self.fp.close()
        except Exception:
            pass


def make_event(store_id: int, camera_id: str, visitor_id: str, event_type: str, timestamp: datetime, zone_id: Optional[str], dwell_ms: Optional[int], is_staff: bool, confidence: float, metadata: Optional[Dict] = None) -> Event:
    return Event(
        event_id=str(uuid.uuid4()),
        store_id=store_id,
        camera_id=camera_id,
        visitor_id=visitor_id,
        event_type=event_type,
        timestamp=timestamp.isoformat(),
        zone_id=zone_id,
        dwell_ms=dwell_ms,
        is_staff=is_staff,
        confidence=float(confidence),
        metadata=metadata,
    )
