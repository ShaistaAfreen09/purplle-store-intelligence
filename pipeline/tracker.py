"""Simple tracker with optional ByteTrack fallback.

Implements Tracker.update(detections) -> list[dict] with keys:
- track_id
- bbox
- confidence
- class_id
"""
from __future__ import annotations

from typing import List, Dict, Tuple
import math
import time

try:
    # Attempt to import a ByteTrack implementation if available
    from bytetrack import Tracker as ByteTracker  # type: ignore
    BYTE_AVAILABLE = True
except Exception:
    BYTE_AVAILABLE = False


class SimpleTracker:
    def __init__(self, max_distance: float = 80.0, max_missing: int = 30):
        self.next_id = 1
        self.tracks: dict[int, dict] = {}
        self.max_distance = max_distance
        self.max_missing = max_missing

    @staticmethod
    def _center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @staticmethod
    def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def update(self, detections: List[Dict]) -> List[Dict]:
        assigned = set()
        results = []
        centers = [self._center(d["bbox"]) for d in detections]

        # Try to match existing tracks by nearest center
        for tid, track in list(self.tracks.items()):
            best_idx = None
            best_dist = None
            for i, c in enumerate(centers):
                if i in assigned:
                    continue
                d = self._dist(track["center"], c)
                if d <= self.max_distance and (best_dist is None or d < best_dist):
                    best_dist = d
                    best_idx = i
            if best_idx is not None:
                det = detections[best_idx]
                assigned.add(best_idx)
                track["bbox"] = det["bbox"]
                track["center"] = centers[best_idx]
                track["last_seen"] = time.time()
                track["missing"] = 0
                track["confidence"] = det.get("confidence", 1.0)
                results.append({
                    "track_id": tid,
                    "bbox": track["bbox"],
                    "confidence": track["confidence"],
                    "center": track["center"],
                    "class_id": det.get("class_id", 0),
                })
            else:
                track["missing"] += 1
                if track["missing"] > self.max_missing:
                    del self.tracks[tid]

        # Create new tracks for unassigned detections
        for i, det in enumerate(detections):
            if i in assigned:
                continue
            tid = self.next_id
            self.next_id += 1
            center = centers[i]
            self.tracks[tid] = {
                "bbox": det["bbox"],
                "center": center,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "missing": 0,
                "confidence": det.get("confidence", 1.0),
            }
            results.append({
                "track_id": tid,
                "bbox": det["bbox"],
                "confidence": det.get("confidence", 1.0),
                "center": center,
                "class_id": det.get("class_id", 0),
            })

        return results


class Tracker:
    def __init__(self):
        if BYTE_AVAILABLE:
            # Wrap ByteTrack if available (best-effort)
            self.impl = ByteTracker()
            self._byte = True
        else:
            self.impl = SimpleTracker()
            self._byte = False

    def update(self, detections: List[Dict]) -> List[Dict]:
        return self.impl.update(detections)
