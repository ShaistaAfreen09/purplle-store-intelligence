"""POS transaction ingestion utilities.

This module parses a POS transaction CSV and generates PURCHASE events that can be
fed into the existing event ingestion pipeline.
"""

from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.events import Event, EventWriter, make_event

DEFAULT_CAMERA_ID = "CAM5"
DEFAULT_ZONE_ID = "CHECKOUT"

CSV_FIELD_ALIASES = {
    "transaction_id": "transaction_reference",
    "order_id": "transaction_reference",
    "store": "store_id",
    "customer_id": "visitor_id",
    "client_id": "visitor_id",
    "transaction_time": "timestamp",
    "time": "timestamp",
}

REQUIRED_FIELDS = ["transaction_reference", "store_id", "visitor_id", "timestamp", "amount"]


def _normalize_fieldnames(row: dict[str, str]) -> dict[str, str]:
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized_key = key.strip()
        if normalized_key in CSV_FIELD_ALIASES:
            normalized_key = CSV_FIELD_ALIASES[normalized_key]
        normalized[normalized_key] = (value or "").strip()
    return normalized


def _parse_timestamp(value: str) -> datetime:
    if not value:
        raise ValueError("timestamp is required")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T")
    return datetime.fromisoformat(text)


def _parse_items(value: str) -> Any:
    if not value:
        return {}
    text = value.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        parts = [item.strip() for item in text.split(";") if item.strip()]
        return parts if parts else {}


def _build_event_payload(row: dict[str, str]) -> dict[str, Any]:
    row = _normalize_fieldnames(row)
    missing = [name for name in REQUIRED_FIELDS if not row.get(name)]
    if missing:
        raise ValueError(f"Missing required POS transaction fields: {', '.join(missing)}")

    transaction_reference = row["transaction_reference"]
    store_id = row["store_id"]
    visitor_id = row["visitor_id"]
    timestamp = _parse_timestamp(row["timestamp"])
    amount = float(row["amount"])

    metadata: dict[str, Any] = {
        "transaction_reference": transaction_reference,
        "amount": amount,
        "currency": row.get("currency", "USD") or "USD",
    }

    payment_method = row.get("payment_method")
    if payment_method:
        metadata["payment_method"] = payment_method

    items = row.get("items")
    if items:
        metadata["items"] = _parse_items(items)

    if row.get("transaction_reference") is None and row.get("transaction_id"):
        metadata["transaction_reference"] = row["transaction_id"]

    zone_id = row.get("zone_id") or DEFAULT_ZONE_ID
    camera_id = row.get("camera_id") or DEFAULT_CAMERA_ID

    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": "PURCHASE",
        "timestamp": timestamp,
        "zone_id": zone_id,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 1.0,
        "metadata": metadata,
    }


def parse_pos_transactions(path: str) -> list[Event]:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"POS transactions CSV not found: {path}")

    events: list[Event] = []
    with path_obj.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if not any(row.values()):
                continue
            payload = _build_event_payload(row)
            events.append(make_event(
                store_id=payload["store_id"],
                camera_id=payload["camera_id"],
                visitor_id=payload["visitor_id"],
                event_type=payload["event_type"],
                timestamp=payload["timestamp"],
                zone_id=payload["zone_id"],
                dwell_ms=payload["dwell_ms"],
                is_staff=payload["is_staff"],
                confidence=payload["confidence"],
                metadata=payload["metadata"],
            ))
    return events


def write_purchase_events(input_path: str, output_path: str) -> int:
    events = parse_pos_transactions(input_path)
    writer = EventWriter(output_path)
    try:
        for event in events:
            writer.write(event)
    finally:
        writer.close()
    return len(events)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate PURCHASE events from a POS CSV file.")
    parser.add_argument("--input", required=True, help="POS transactions CSV path")
    parser.add_argument("--output", default="output/purchase_events.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    count = write_purchase_events(args.input, args.output)
    print(f"Wrote {count} PURCHASE events to {args.output}")


if __name__ == "__main__":
    main()
