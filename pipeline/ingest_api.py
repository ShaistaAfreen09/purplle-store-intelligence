"""Ingest events JSONL into the backend ingestion API."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Generator, Iterable

import httpx

DEFAULT_API_URL = "http://localhost:8000/events/ingest"
MAX_BATCH_SIZE = 500


def read_jsonl_events(path: str) -> list[dict[str, Any]]:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"JSONL events file not found: {path}")

    events: list[dict[str, Any]] = []
    with path_obj.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("Each line in the JSONL file must be a JSON object.")
            events.append(item)
    return events


def _chunked(iterable: list[dict[str, Any]], size: int) -> Generator[list[dict[str, Any]], None, None]:
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def ingest_jsonl_file(path: str, api_url: str = DEFAULT_API_URL, batch_size: int = MAX_BATCH_SIZE) -> dict[str, int]:
    if batch_size <= 0 or batch_size > MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}")

    events = read_jsonl_events(path)
    if not events:
        return {"accepted": 0, "duplicates": 0, "rejected": 0, "errors": 0}

    summary = {"accepted": 0, "duplicates": 0, "rejected": 0, "errors": 0}
    with httpx.Client(timeout=30.0) as client:
        for batch in _chunked(events, batch_size):
            response = client.post(api_url, json=batch)
            response.raise_for_status()
            payload = response.json()
            summary["accepted"] += int(payload.get("accepted", 0))
            summary["duplicates"] += int(payload.get("duplicates", 0))
            summary["rejected"] += int(payload.get("rejected", 0))
            summary["errors"] += len(payload.get("errors", []))

    return summary


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest event JSONL into the FastAPI ingestion endpoint.")
    parser.add_argument("--input", required=True, help="Path to events JSONL file")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Ingestion API URL")
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE, help="Events per ingestion batch")
    args = parser.parse_args()

    summary = ingest_jsonl_file(args.input, api_url=args.api_url, batch_size=args.batch_size)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
