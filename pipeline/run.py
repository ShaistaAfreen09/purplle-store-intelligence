"""Run the CCTV -> events pipeline.

Usage:
    python pipeline/run.py --video CAM1.mp4 --store 1 --camera CAM1 --output output/events.jsonl
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import sys
from pathlib import Path

# Ensure repository root is on sys.path so package imports work when running
# the script directly (e.g. `python pipeline/run.py`).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.detect import Detector
from pipeline.tracker import Tracker
from pipeline.sessions import SessionManager
from pipeline.zones import ZoneManager
from pipeline.events import EventWriter, make_event


def process(video_path: str, output_path: str, store_id: int, camera_id: str, max_frames: int | None = None, entry_line_y: float | None = None, entry_direction: str = "down"):
    # defer importing cv2 to allow running `--help` without OpenCV native libs
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    detector = Detector()
    tracker = Tracker()
    zm = ZoneManager(path="config/store_zones.yaml")
    sessions = SessionManager(exit_timeout=2.0, zone_manager=zm, camera_id=camera_id)
    # apply optional entry line settings
    sessions.entry_line_y = entry_line_y
    sessions.entry_direction = entry_direction
    writer = EventWriter(output_path)

    frame_idx = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_time = lambda idx: datetime.now(timezone.utc)

    # ensure output dir exists
    import os
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if max_frames and frame_idx > max_frames:
                break

            detections = detector.detect(frame)
            tracks = tracker.update(detections)

            # sessions produces entry and exit events
            evs = sessions.update(tracks)
            for e in evs:
                if e["type"] == "ENTRY":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e["visitor_id"],
                        event_type="ENTRY",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=None,
                        dwell_ms=None,
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "EXIT":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e["visitor_id"],
                        event_type="EXIT",
                        timestamp=datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"],
                        zone_id=None,
                        dwell_ms=e.get("dwell_ms"),
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "ZONE_ENTER":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e.get("visitor_id"),
                        event_type="ZONE_ENTER",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=e.get("zone"),
                        dwell_ms=None,
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "ZONE_EXIT":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e.get("visitor_id"),
                        event_type="ZONE_EXIT",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=e.get("zone"),
                        dwell_ms=e.get("dwell_ms"),
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "REENTRY":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e.get("visitor_id"),
                        event_type="REENTRY",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=None,
                        dwell_ms=None,
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "BILLING_QUEUE_JOIN":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e.get("visitor_id"),
                        event_type="BILLING_QUEUE_JOIN",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=e.get("zone"),
                        dwell_ms=None,
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)
                elif e["type"] == "BILLING_QUEUE_ABANDON":
                    ev = make_event(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=e.get("visitor_id"),
                        event_type="BILLING_QUEUE_ABANDON",
                        timestamp=(datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) if isinstance(e["timestamp"], str) else e["timestamp"]),
                        zone_id=e.get("zone"),
                        dwell_ms=e.get("dwell_ms"),
                        is_staff=False,
                        confidence=1.0,
                    )
                    writer.write(ev)

    finally:
        writer.close()
        cap.release()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--output", default="output/events.jsonl")
    p.add_argument("--store", type=int, default=1)
    p.add_argument("--camera", default="CAM1")
    p.add_argument("--max-frames", type=int, default=None)
    p.add_argument("--entry-line-y", type=float, default=None, help="Y coordinate (pixels) of ENTRY_LINE for line crossing detection")
    p.add_argument("--entry-direction", choices=["down", "up"], default="down", help="Direction considered entry when crossing the line")
    args = p.parse_args()
    # The optional entry-line processing was merged into `process` above.
    # Call process with provided CLI args.
    process(args.video, args.output, args.store, args.camera, args.max_frames, args.entry_line_y, args.entry_direction)


if __name__ == "__main__":
    main()
