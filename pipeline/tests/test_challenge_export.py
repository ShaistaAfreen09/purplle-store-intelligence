from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.challenge_export import export_challenge_events, format_store_code


def test_format_store_code_from_int() -> None:
    assert format_store_code(1076) == "store_1076"


def test_format_store_code_from_string_store_prefix() -> None:
    assert format_store_code("store_1076") == "store_1076"


def test_format_store_code_from_string_st_prefix() -> None:
    assert format_store_code("ST1076") == "store_1076"


def test_export_challenge_events_maps_entry_and_zone_events(tmp_path: Path) -> None:
    input_path = tmp_path / "internal_events.jsonl"
    output_path = tmp_path / "submission_events.jsonl"

    internal_events = [
        {
            "event_id": "e1",
            "store_id": 1076,
            "camera_id": "cam1",
            "visitor_id": "ID_60001",
            "event_type": "ENTRY",
            "timestamp": "2026-03-08T18:10:05.120000",
            "zone_id": None,
            "dwell_ms": None,
            "is_staff": False,
            "confidence": 0.95,
            "metadata": {},
        },
        {
            "event_id": "e2",
            "store_id": 1076,
            "camera_id": "CAM2",
            "visitor_id": "101",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-03-08T18:10:45.280000",
            "zone_id": "PURPLLE_MUM_1076_Z01",
            "dwell_ms": None,
            "is_staff": False,
            "confidence": 0.88,
            "metadata": {},
        },
    ]

    input_path.write_text("\n".join(json.dumps(event) for event in internal_events) + "\n", encoding="utf-8")
    export_challenge_events(str(input_path), str(output_path))

    output_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(output_lines) == 2

    entry_event = json.loads(output_lines[0])
    assert entry_event["event_type"] == "entry"
    assert entry_event["id_token"] == "ID_60001"
    assert entry_event["store_code"] == "store_1076"
    assert entry_event["event_timestamp"] == "2026-03-08T18:10:05.120000"
    assert entry_event["camera_id"] == "cam1"
    assert entry_event["is_staff"] is False
    assert "track_id" not in entry_event

    zone_event = json.loads(output_lines[1])
    assert zone_event["event_type"] == "zone_entered"
    assert zone_event["track_id"] == "101"
    assert zone_event["store_code"] == "store_1076"
    assert zone_event["event_time"] == "2026-03-08T18:10:45.280000"
    assert zone_event["zone_id"] == "PURPLLE_MUM_1076_Z01"
    assert zone_event["camera_id"] == "CAM2"
    assert zone_event["is_staff"] is False
    assert "id_token" not in zone_event


def test_export_challenge_events_reentry_maps_to_entry(tmp_path: Path) -> None:
    input_path = tmp_path / "internal_events.jsonl"
    output_path = tmp_path / "submission_events.jsonl"

    internal_events = [
        {
            "event_id": "e3",
            "store_id": "ST1076",
            "camera_id": "cam3",
            "visitor_id": "ID_60010",
            "event_type": "REENTRY",
            "timestamp": "2026-03-08T18:12:00.000000",
            "zone_id": None,
            "dwell_ms": None,
            "is_staff": True,
            "confidence": 0.80,
            "metadata": {},
        }
    ]

    input_path.write_text("\n".join(json.dumps(event) for event in internal_events) + "\n", encoding="utf-8")
    export_challenge_events(str(input_path), str(output_path))

    output_event = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert output_event["event_type"] == "entry"
    assert output_event["id_token"] == "ID_60010"
    assert output_event["store_code"] == "store_1076"
    assert output_event["event_timestamp"] == "2026-03-08T18:12:00.000000"
    assert output_event["is_staff"] is True


def test_export_challenge_events_raises_on_unsupported_event_type(tmp_path: Path) -> None:
    input_path = tmp_path / "internal_events.jsonl"
    output_path = tmp_path / "submission_events.jsonl"

    internal_events = [
        {
            "event_id": "e4",
            "store_id": 1076,
            "camera_id": "cam4",
            "visitor_id": "ID_60011",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": "2026-03-08T18:13:00.000000",
            "zone_id": None,
            "dwell_ms": None,
            "is_staff": False,
            "confidence": 0.75,
            "metadata": {},
        }
    ]

    input_path.write_text("\n".join(json.dumps(event) for event in internal_events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported event type"):
        export_challenge_events(str(input_path), str(output_path))
