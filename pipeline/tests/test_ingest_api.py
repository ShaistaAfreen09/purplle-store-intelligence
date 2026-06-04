from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import pipeline.ingest_api as ingest_api


def test_read_jsonl_events_reads_valid_file(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    jsonl_path.write_text(
        json.dumps({"event_id": "e1", "store_id": "1"}) + "\n"
        + json.dumps({"event_id": "e2", "store_id": "1"}) + "\n",
        encoding="utf-8",
    )

    events = ingest_api.read_jsonl_events(str(jsonl_path))

    assert len(events) == 2
    assert events[0]["event_id"] == "e1"
    assert events[1]["event_id"] == "e2"


def test_read_jsonl_events_filtered_blank_lines(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    jsonl_path.write_text("\n" + json.dumps({"event_id": "e1", "store_id": "1"}) + "\n", encoding="utf-8")

    events = ingest_api.read_jsonl_events(str(jsonl_path))

    assert len(events) == 1


def test_ingest_jsonl_file_posts_batches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    jsonl_path = tmp_path / "events.jsonl"
    sample_events = [
        {"event_id": f"e{i}", "store_id": "1", "camera_id": "CAM1", "visitor_id": "v1", "event_type": "ENTRY", "timestamp": "2026-05-30T00:00:00+00:00", "zone_id": None, "dwell_ms": None, "is_staff": False, "confidence": 1.0, "metadata": {} }
        for i in range(5)
    ]
    jsonl_path.write_text("\n".join(json.dumps(event) for event in sample_events) + "\n", encoding="utf-8")

    calls = []

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            pass

        def post(self, url: str, json: list[dict[str, object]]) -> MagicMock:
            calls.append((url, json))
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "accepted": len(json),
                "duplicates": 0,
                "rejected": 0,
                "errors": [],
            }
            return response

    monkeypatch.setattr(ingest_api, "httpx", MagicMock(Client=FakeClient))

    summary = ingest_api.ingest_jsonl_file(str(jsonl_path), api_url="http://test/events/ingest", batch_size=2)

    assert summary["accepted"] == 5
    assert summary["duplicates"] == 0
    assert summary["rejected"] == 0
    assert summary["errors"] == 0
    assert len(calls) == 3
    assert all(call[0] == "http://test/events/ingest" for call in calls)
    assert [len(call[1]) for call in calls] == [2, 2, 1]


def test_ingest_jsonl_file_with_empty_file_returns_summary(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "empty.jsonl"
    jsonl_path.write_text("", encoding="utf-8")

    summary = ingest_api.ingest_jsonl_file(str(jsonl_path), api_url="http://test/events/ingest", batch_size=10)

    assert summary == {"accepted": 0, "duplicates": 0, "rejected": 0, "errors": 0}
