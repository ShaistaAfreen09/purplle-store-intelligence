"""Session management: map tracker IDs to visitor sessions and emit ENTRY/EXIT events.

Simple logic:
- When a track first appears => ENTRY
- When a track disappears for > exit_timeout => EXIT (emit dwell_ms)
- Maintains visitor_id (UUID) per track
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, List
import time
import uuid

from app.schemas.anomaly import AnomalyType  # noqa: F401 (not used here)


@dataclass
class Session:
    track_id: int
    visitor_id: str
    first_seen: float
    last_seen: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    zone: Optional[int] = None
    prev_center: Optional[tuple[float, float]] = None
    inside: bool = False
    zone_entry_time: Optional[datetime] = None
    zone_type: Optional[str] = None
    in_queue: bool = False
    queue_join_time: Optional[datetime] = None
    # shelf interaction tracking
    shelf_ref_center: Optional[tuple[float, float]] = None
    shelf_still_since: Optional[float] = None
    shelf_interacted: bool = False


class SessionManager:
    def __init__(self, exit_timeout: float = 5.0, zone_manager: object | None = None, camera_id: Optional[str] = None, reentry_window: float = 1800.0, reentry_max_dist: float = 100.0):
        self.exit_timeout = exit_timeout
        self.sessions: Dict[int, Session] = {}
        self.entry_line_y: Optional[float] = None
        self.entry_direction: str = "down"
        self.zone_manager = zone_manager
        self.camera_id = camera_id
        # recent visitors for re-entry detection: list of dicts {visitor_id, last_seen_ts, last_center}
        self.recent_visitors: list[dict] = []
        self.reentry_window = reentry_window
        self.reentry_max_dist = reentry_max_dist
        # shelf interaction params
        self.shelf_distance_meters = 1.0
        self.pixels_per_meter = 100.0
        self.shelf_still_threshold_seconds = 3.0

    def update(self, tracks: List[Dict]) -> List[Dict]:
        """Process current active tracks and return list of events generated now.

        Returns list of event dicts for ENTRY and EXIT as they occur.
        """
        now_ts = time.time()
        active_ids = {t["track_id"] for t in tracks}
        events = []

        # Update or create sessions
        for t in tracks:
            tid = t["track_id"]
            if tid not in self.sessions:
                center = t.get("center")
                # try to detect reentry using recent visitors when seen at the entrance camera
                visitor_id = str(uuid.uuid4())
                if self.camera_id == "CAM3" and center is not None:
                    found = None
                    now_ts_f = now_ts
                    for rv in list(self.recent_visitors):
                        age = now_ts_f - rv.get("last_seen_ts", 0)
                        if age <= self.reentry_window:
                            # compute distance
                            lx, ly = rv.get("last_center", (None, None))
                            if lx is None:
                                continue
                            dx = lx - center[0]
                            dy = ly - center[1]
                            dist = (dx * dx + dy * dy) ** 0.5
                            if dist <= self.reentry_max_dist:
                                found = rv
                                break
                    if found is not None:
                        visitor_id = found["visitor_id"]
                        # remove from recent_visitors to avoid duplicate matches
                        try:
                            self.recent_visitors.remove(found)
                        except ValueError:
                            pass
                        reentry_flag = True
                    else:
                        reentry_flag = False
                else:
                    reentry_flag = False
                s = Session(
                    track_id=tid,
                    visitor_id=visitor_id,
                    first_seen=now_ts,
                    last_seen=now_ts,
                    entry_time=datetime.now(timezone.utc),
                )
                s.prev_center = t.get("center")
                # assign initial zone if zone manager configured
                if self.zone_manager is not None and s.prev_center is not None and self.camera_id is not None:
                    zone = self.zone_manager.get_zone_for_point(self.camera_id, s.prev_center)
                    if zone is not None:
                        s.zone = zone.name
                        s.zone_type = zone.type
                        s.zone_entry_time = datetime.now(timezone.utc)
                        events.append({
                            "type": "ZONE_ENTER",
                            "track_id": tid,
                            "visitor_id": s.visitor_id,
                            "zone": s.zone,
                            "timestamp": s.zone_entry_time.isoformat(),
                        })
                        # if this is a checkout zone, mark queue join
                        if zone.type == "CHECKOUT":
                            s.in_queue = True
                            s.queue_join_time = datetime.now(timezone.utc)
                            events.append({
                                "type": "BILLING_QUEUE_JOIN",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "zone": s.zone,
                                "timestamp": s.queue_join_time.isoformat(),
                            })
                        # if this is a shelf-like zone, start shelf tracking
                        if zone.type in ("SKINCARE", "COSMETICS", "SHELF"):
                            s.shelf_ref_center = s.prev_center
                            s.shelf_still_since = now_ts
                            s.shelf_interacted = False
                self.sessions[tid] = s
                # do not emit ENTRY immediately; emit on line crossing if configured
                # For entrance camera (CAM3) emit ENTRY/REENTRY immediately on first seen
                if self.entry_line_y is None:
                    if self.camera_id == "CAM3":
                        if reentry_flag:
                            events.append({
                                "type": "REENTRY",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "timestamp": s.entry_time.isoformat(),
                            })
                        else:
                            events.append({
                                "type": "ENTRY",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "timestamp": s.entry_time.isoformat(),
                            })
            else:
                s = self.sessions[tid]
                s.last_seen = now_ts
                center = t.get("center")
                # zone transition detection
                if self.zone_manager is not None and center is not None and self.camera_id is not None:
                    zone = self.zone_manager.get_zone_for_point(self.camera_id, center)
                    zone_name = zone.name if zone is not None else None
                    if zone_name != s.zone:
                        # exiting previous zone
                        if s.zone is not None and s.zone_entry_time is not None:
                            exit_time = datetime.now(timezone.utc)
                            dwell_ms = int((exit_time - s.zone_entry_time).total_seconds() * 1000.0)
                            events.append({
                                "type": "ZONE_EXIT",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "zone": s.zone,
                                "timestamp": exit_time.isoformat(),
                                "dwell_ms": dwell_ms,
                            })
                            # if leaving checkout zone while in queue, emit abandon
                            if s.zone_type == "CHECKOUT" and s.in_queue:
                                events.append({
                                    "type": "BILLING_QUEUE_ABANDON",
                                    "track_id": tid,
                                    "visitor_id": s.visitor_id,
                                    "zone": s.zone,
                                    "timestamp": exit_time.isoformat(),
                                    "dwell_ms": dwell_ms,
                                })
                        # entering new zone
                        if zone_name is not None:
                            s.zone_entry_time = datetime.now(timezone.utc)
                            # set zone type
                            s.zone_type = zone.type if zone is not None else None
                            # if entering checkout, mark queue
                            if s.zone_type == "CHECKOUT":
                                s.in_queue = True
                                s.queue_join_time = s.zone_entry_time
                                events.append({
                                    "type": "BILLING_QUEUE_JOIN",
                                    "track_id": tid,
                                    "visitor_id": s.visitor_id,
                                    "zone": zone_name,
                                    "timestamp": s.queue_join_time.isoformat(),
                                })
                            events.append({
                                "type": "ZONE_ENTER",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "zone": zone_name,
                                "timestamp": s.zone_entry_time.isoformat(),
                            })
                        else:
                            s.zone_entry_time = None
                            # clear shelf tracking when leaving zone
                            s.shelf_ref_center = None
                            s.shelf_still_since = None
                            s.shelf_interacted = False
                        s.zone = zone_name
                else:
                    # when staying in same zone, check shelf interaction heuristics
                    if s.zone_type in ("SKINCARE", "COSMETICS", "SHELF") and center is not None:
                        # threshold in pixels
                        threshold_px = self.shelf_distance_meters * self.pixels_per_meter
                        ref = s.shelf_ref_center
                        if ref is None:
                            s.shelf_ref_center = center
                            s.shelf_still_since = now_ts
                            s.shelf_interacted = False
                        else:
                            dx = ref[0] - center[0]
                            dy = ref[1] - center[1]
                            dist = (dx * dx + dy * dy) ** 0.5
                            if dist <= threshold_px:
                                if s.shelf_still_since is None:
                                    s.shelf_still_since = now_ts
                                # check duration
                                if not s.shelf_interacted and (now_ts - s.shelf_still_since) >= self.shelf_still_threshold_seconds:
                                    s.shelf_interacted = True
                                    duration_ms = int((now_ts - s.shelf_still_since) * 1000.0)
                                    events.append({
                                        "type": "SHELF_INTERACTION",
                                        "track_id": tid,
                                        "visitor_id": s.visitor_id,
                                        "zone": s.zone,
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "duration_ms": duration_ms,
                                    })
                            else:
                                # moved away, reset reference
                                s.shelf_ref_center = center
                                s.shelf_still_since = now_ts
                                s.shelf_interacted = False
                # check line crossing if center available and entry_line configured
                if center is not None and s.prev_center is not None and self.entry_line_y is not None:
                    prev_y = s.prev_center[1]
                    cur_y = center[1]
                    line_y = self.entry_line_y
                    # crossing downwards = entry
                    if not s.inside and self.entry_direction == "down" and prev_y < line_y <= cur_y:
                        s.inside = True
                        events.append({
                            "type": "ENTRY",
                            "track_id": tid,
                            "visitor_id": s.visitor_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    # crossing upwards = exit
                    elif s.inside and self.entry_direction == "down" and prev_y >= line_y > cur_y:
                        s.inside = False
                        s.exit_time = datetime.now(timezone.utc)
                        dwell_ms = int((s.exit_time - s.entry_time).total_seconds() * 1000.0)
                        events.append({
                            "type": "EXIT",
                            "track_id": tid,
                            "visitor_id": s.visitor_id,
                            "timestamp": s.exit_time.isoformat(),
                            "dwell_ms": dwell_ms,
                        })
                        # record to recent_visitors for possible reentry
                        try:
                            self.recent_visitors.append({
                                "visitor_id": s.visitor_id,
                                "last_seen_ts": now_ts,
                                "last_center": s.prev_center,
                            })
                        except Exception:
                            pass
                        # if exiting and was in queue, emit abandon
                        if s.in_queue:
                            queue_exit_time = datetime.now(timezone.utc)
                            queue_dwell_ms = None
                            if s.queue_join_time is not None:
                                queue_dwell_ms = int((queue_exit_time - s.queue_join_time).total_seconds() * 1000.0)
                            events.append({
                                "type": "BILLING_QUEUE_ABANDON",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "zone": s.zone,
                                "timestamp": queue_exit_time.isoformat(),
                                "dwell_ms": queue_dwell_ms,
                            })
                            s.in_queue = False
                            s.queue_join_time = None
                # update previous center
                s.prev_center = center

        # Find disappeared tracks
        for tid in list(self.sessions.keys()):
            if tid not in active_ids:
                s = self.sessions[tid]
                if now_ts - s.last_seen > self.exit_timeout:
                    s.exit_time = datetime.now(timezone.utc)
                    dwell_ms = int((s.exit_time - s.entry_time).total_seconds() * 1000.0)
                    events.append({
                        "type": "EXIT",
                        "track_id": tid,
                        "visitor_id": s.visitor_id,
                        "timestamp": s.exit_time.isoformat(),
                        "dwell_ms": dwell_ms,
                    })
                    # if leaving a zone, emit zone exit as well
                    if s.zone is not None and s.zone_entry_time is not None:
                        exit_time = datetime.now(timezone.utc)
                        zone_dwell_ms = int((exit_time - s.zone_entry_time).total_seconds() * 1000.0)
                        events.append({
                            "type": "ZONE_EXIT",
                            "track_id": tid,
                            "visitor_id": s.visitor_id,
                            "zone": s.zone,
                            "timestamp": exit_time.isoformat(),
                            "dwell_ms": zone_dwell_ms,
                        })
                        # if leaving checkout zone while in queue, emit abandon
                        if s.zone_type == "CHECKOUT" and s.in_queue:
                            queue_dwell = None
                            if s.queue_join_time is not None:
                                queue_dwell = int((exit_time - s.queue_join_time).total_seconds() * 1000.0)
                            events.append({
                                "type": "BILLING_QUEUE_ABANDON",
                                "track_id": tid,
                                "visitor_id": s.visitor_id,
                                "zone": s.zone,
                                "timestamp": exit_time.isoformat(),
                                "dwell_ms": queue_dwell,
                            })
                            s.in_queue = False
                            s.queue_join_time = None
                    # record to recent_visitors for possible reentry
                    try:
                        self.recent_visitors.append({
                            "visitor_id": s.visitor_id,
                            "last_seen_ts": now_ts,
                            "last_center": s.prev_center,
                        })
                    except Exception:
                        pass
                    # prune old recent visitors
                    cutoff = now_ts - self.reentry_window
                    self.recent_visitors = [rv for rv in self.recent_visitors if rv.get("last_seen_ts", 0) >= cutoff]
                    del self.sessions[tid]

        return events
