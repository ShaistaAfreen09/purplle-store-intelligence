"""Export internal pipeline events into challenge-compatible submission JSONL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.ingest_api import read_jsonl_events

EVENT_TYPE_MAP: dict[str, str] = {
    "ENTRY": "entry",
    "EXIT": "exit",
    "ZONE_ENTER": "zone_entered",
    "ZONE_EXIT": "zone_exited",
    "REENTRY": "entry",
}


def format_store_code(store_id: Any) -> str:
    if isinstance(store_id, int):
        return f"store_{store_id}"

    if isinstance(store_id, str):
        if store_id.startswith("store_"):
            return store_id
        normalized = store_id.strip()
        if normalized.upper().startswith("ST") and normalized[2:].isdigit():
            return f"store_{normalized[2:]}"
        digits = "".join(ch for ch in normalized if ch.isdigit())
        if digits:
            return f"store_{digits}"
        return f"store_{normalized}"

    raise TypeError("store_id must be an integer or string")


def _map_event(record: dict[str, Any]) -> dict[str, Any]:
    event_type = record.get("event_type")
    if event_type is None:
        raise ValueError("Missing event_type in event record")

    mapped = EVENT_TYPE_MAP.get(event_type)
    if mapped is None:
        raise ValueError(f"Unsupported event type: {event_type}")

    visitor_id = record.get("visitor_id")
    if visitor_id is None:
        raise ValueError("Missing visitor_id in event record")

    store_code = format_store_code(record.get("store_id"))
    output: dict[str, Any] = {
        "event_type": mapped,
        "store_code": store_code,
        "camera_id": record.get("camera_id"),
        "is_staff": record.get("is_staff", False),
    }

    if mapped in {"entry", "exit"}:
        output["id_token"] = visitor_id
        output["event_timestamp"] = record.get("timestamp")
    else:
        output["track_id"] = visitor_id
        output["event_time"] = record.get("timestamp")

    if record.get("zone_id") is not None:
        output["zone_id"] = record["zone_id"]

    return output


def export_challenge_events(input_path: str, output_path: str) -> None:
    events = read_jsonl_events(input_path)
    if not events:
        raise ValueError("Input event file is empty")

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with output_path_obj.open("w", encoding="utf-8") as out_fp:
        for record in events:
            mapped_record = _map_event(record)
            out_fp.write(json.dumps(mapped_record, default=str) + "\n")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Export pipeline events to challenge-compatible JSONL.")
    parser.add_argument("--input", required=True, help="Path to internal generated event JSONL")
    parser.add_argument("--output", default="submission/events.jsonl", help="Path to challenge-compatible output JSONL")
    args = parser.parse_args()

    export_challenge_events(args.input, args.output)


if __name__ == "__main__":
    main()
