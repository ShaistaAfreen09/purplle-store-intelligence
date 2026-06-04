"""Simple analytics over generated events.jsonl for checkout queue metrics."""
from __future__ import annotations

import json
from typing import Dict, Any


def compute_queue_metrics(path: str) -> Dict[str, Any]:
    """Compute basic queue metrics from an events.jsonl file.

    Returns:
      - current_queue_depth: int
      - total_joins: int
      - total_abandons: int
      - avg_abandon_wait_ms: float | None
      - avg_wait_ms_over_abandons: same as above
    """
    joins = {}
    in_queue = set()
    total_joins = 0
    total_abandons = 0
    abandon_waits = []

    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():
                continue
            e = json.loads(line)
            et = e.get("event_type")
            vid = e.get("visitor_id")
            if et == "BILLING_QUEUE_JOIN":
                total_joins += 1
                joins[vid] = e.get("timestamp")
                in_queue.add(vid)
            elif et == "BILLING_QUEUE_ABANDON":
                total_abandons += 1
                # prefer dwell_ms if present
                dwell = e.get("dwell_ms")
                if dwell is not None:
                    abandon_waits.append(int(dwell))
                else:
                    # fallback: if we have a join timestamp, cannot compute ms reliably here
                    pass
                if vid in in_queue:
                    in_queue.remove(vid)

    avg_abandon = sum(abandon_waits) / len(abandon_waits) if abandon_waits else None

    return {
        "current_queue_depth": len(in_queue),
        "total_joins": total_joins,
        "total_abandons": total_abandons,
        "avg_abandon_wait_ms": avg_abandon,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("events", help="events.jsonl file")
    args = p.parse_args()

    metrics = compute_queue_metrics(args.events)
    print(json.dumps(metrics, indent=2))
