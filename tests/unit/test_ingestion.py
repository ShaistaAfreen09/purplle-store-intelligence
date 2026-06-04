from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routers import events as events_router
from app.schemas.event import ChallengeEvent
from app.services.ingestion_service import _event_payload, ingest_events as ingestion_service


def make_event_payload(event_id: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "store_id": "store-1",
        "camera_id": "camera-a",
        "visitor_id": "visitor-1",
        "event_type": "ENTRY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone_id": "zone-1",
        "dwell_ms": 1200,
        "is_staff": False,
        "confidence": 0.82,
        "metadata": {"source": "sensor"},
    }


def test_ingestion_service_handles_duplicates_and_insert_counts():
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.rowcount = 1
    db.execute.return_value = result_mock

    events = [
        ChallengeEvent.model_validate(make_event_payload("e1")),
        ChallengeEvent.model_validate(make_event_payload("e2")),
        ChallengeEvent.model_validate(make_event_payload("e1")),
    ]

    result = ingestion_service(db, events)

    assert result["accepted"] == 1
    assert result["duplicates"] == 2
    assert result["rejected"] == 0
    assert result["errors"] == []
    db.commit.assert_called_once()


def test_challenge_event_allows_optional_zone_id_and_dwell_ms():
    payload = make_event_payload("e1")
    payload["zone_id"] = None
    payload["dwell_ms"] = None

    event = ChallengeEvent.model_validate(payload)

    assert event.zone_id is None
    assert event.dwell_ms is None


def test_event_payload_maps_metadata_to_event_metadata():
    event = ChallengeEvent.model_validate(make_event_payload("e1"))
    payload = _event_payload(event)

    assert payload["event_metadata"] == {"source": "sensor"}
    assert "metadata" not in payload


def test_ingest_events_endpoint_partial_success(monkeypatch):
    def fake_get_db():
        yield MagicMock()

    def fake_ingest_events(db, events):
        assert len(events) == 1
        return {"accepted": 1, "duplicates": 0, "rejected": 0, "errors": []}

    monkeypatch.setattr(events_router, "get_db", fake_get_db)
    monkeypatch.setattr(events_router, "ingest_events_service", fake_ingest_events)

    client = TestClient(app)
    payload = [
        make_event_payload("e1"),
        {"bad": "payload"},
    ]
    response = client.post("/events/ingest", json=payload)

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert response.json()["duplicates"] == 0
    assert response.json()["rejected"] == 1
    assert len(response.json()["errors"]) == 1


def test_ingest_events_endpoint_accepts_optional_zone_and_dwell(monkeypatch):
    def fake_get_db():
        yield MagicMock()

    def fake_ingest_events(db, events):
        assert len(events) == 1
        assert events[0].zone_id is None
        assert events[0].dwell_ms is None
        return {"accepted": 1, "duplicates": 0, "rejected": 0, "errors": []}

    monkeypatch.setattr(events_router, "get_db", fake_get_db)
    monkeypatch.setattr(events_router, "ingest_events_service", fake_ingest_events)

    client = TestClient(app)
    payload = [make_event_payload("e1")]
    payload[0]["zone_id"] = None
    payload[0]["dwell_ms"] = None

    response = client.post("/events/ingest", json=payload)

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert response.json()["duplicates"] == 0
    assert response.json()["rejected"] == 0
    assert response.json()["errors"] == []
