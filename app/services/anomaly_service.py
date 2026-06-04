from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.models import Event, POSTransaction, Store, VisitorSession, Zone
from app.schemas.anomaly import AnomalySeverity, AnomalyType, StoreAnomaly

QUEUE_EVENT_TYPES = {"BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON"}
ZONE_VISIT_TYPES = {"ZONE_ENTER", "ZONE_DWELL"}
STALE_FEED_MINUTES = 10
DEAD_ZONE_MINUTES = 30
CONVERSION_WINDOW_MINUTES = 30
QUEUE_SPIKE_MULTIPLIER = 1.5


def _calculate_queue_depth(row_iter: list[tuple[int | None, str, datetime]]) -> tuple[int, float]:
    events = sorted((row for row in row_iter if row[0] is not None), key=lambda row: row[2])
    current_depth = 0
    total_weighted_depth = 0.0
    total_duration = 0.0
    previous_time = None
    latest_by_session: dict[int, str] = {}

    for session_id, event_type, event_time in events:
        if previous_time is not None:
            duration = (event_time - previous_time).total_seconds()
            if duration > 0:
                total_weighted_depth += current_depth * duration
                total_duration += duration

        if event_type == "BILLING_QUEUE_JOIN":
            current_depth += 1
            latest_by_session[session_id] = event_type
        elif event_type == "BILLING_QUEUE_ABANDON":
            current_depth = max(current_depth - 1, 0)
            latest_by_session[session_id] = event_type

        previous_time = event_time

    average_depth = current_depth
    if total_duration > 0:
        average_depth = total_weighted_depth / total_duration

    current_queue_depth = sum(
        1
        for event_type in latest_by_session.values()
        if event_type == "BILLING_QUEUE_JOIN"
    )
    return current_queue_depth, average_depth


def _rows_from_execute(result: object) -> list[tuple[int | None, str, datetime]]:
    if hasattr(result, "all"):
        return result.all()
    return result


def get_store_anomalies(db: Session, store_id: int) -> list[StoreAnomaly]:
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError("store not found")

    now = datetime.now(timezone.utc)
    anomalies: list[StoreAnomaly] = []

    last_event_time = db.scalar(
        select(func.max(Event.event_time)).where(Event.store_id == store_id)
    )
    if last_event_time is None or (now - last_event_time) > timedelta(minutes=STALE_FEED_MINUTES):
        anomalies.append(StoreAnomaly(
            anomaly_type=AnomalyType.STALE_FEED,
            severity=AnomalySeverity.CRITICAL,
            description="No events have been received for more than 10 minutes.",
            suggested_action="Check event feed connectivity and confirm sensor or camera data are arriving.",
        ))

    queue_rows = _rows_from_execute(
        db.execute(
            select(Event.session_id, Event.event_type, Event.event_time)
            .where(Event.store_id == store_id)
            .where(Event.event_type.in_(QUEUE_EVENT_TYPES))
            .where(Event.is_staff.is_(False))
            .where(Event.session_id.is_not(None))
        )
    )
    current_queue_depth, average_queue_depth = _calculate_queue_depth(queue_rows)
    if average_queue_depth > 0 and current_queue_depth > average_queue_depth * QUEUE_SPIKE_MULTIPLIER:
        anomalies.append(StoreAnomaly(
            anomaly_type=AnomalyType.QUEUE_SPIKE,
            severity=AnomalySeverity.WARN,
            description=(
                f"Current queue depth ({current_queue_depth}) exceeds the rolling average "
                f"({average_queue_depth:.2f}) by more than 50%."
            ),
            suggested_action="Investigate staffing and queue handling to reduce waiting time.",
        ))

    nonstaff_sessions = db.scalars(
        select(VisitorSession)
        .where(VisitorSession.store_id == store_id)
        .where(VisitorSession.is_staff.is_(False))
    ).all()
    nonstaff_sessions = [
        session for session in nonstaff_sessions
        if not getattr(session, "is_staff", False)
    ]
    historical_visitors = len({session.visitor_id for session in nonstaff_sessions if session.visitor_id})
    historical_transactions = int(
        db.scalar(
            select(func.count(func.distinct(POSTransaction.session_id)))
            .where(POSTransaction.store_id == store_id)
            .where(POSTransaction.session_id.is_not(None))
        )
        or 0
    )
    historical_conversion = historical_transactions / historical_visitors if historical_visitors else 0.0

    window_start = now - timedelta(minutes=CONVERSION_WINDOW_MINUTES)
    current_visitors = len({
        session.visitor_id
        for session in nonstaff_sessions
        if session.visitor_id and (
            session.entry_time >= window_start
            or (session.exit_time is not None and session.exit_time >= window_start)
        )
    })
    current_transaction_sessions = int(
        db.scalar(
            select(func.count(func.distinct(POSTransaction.session_id)))
            .where(POSTransaction.store_id == store_id)
            .where(POSTransaction.transaction_time >= window_start)
            .where(POSTransaction.session_id.is_not(None))
        )
        or 0
    )
    current_conversion = current_transaction_sessions / current_visitors if current_visitors else 0.0
    if current_visitors and historical_visitors and current_conversion < historical_conversion:
        anomalies.append(StoreAnomaly(
            anomaly_type=AnomalyType.CONVERSION_DROP,
            severity=AnomalySeverity.WARN,
            description=(
                f"Current conversion rate ({current_conversion:.2f}) is below historical average "
                f"({historical_conversion:.2f})."
            ),
            suggested_action="Review recent promotions and customer flow to identify conversion blockers.",
        ))

    zones = db.scalars(select(Zone).where(Zone.store_id == store_id)).all()
    zone_latest = {
        zone_id: last_time
        for zone_id, last_time in _rows_from_execute(
            db.execute(
                select(Event.zone_id, func.max(Event.event_time))
                .where(Event.store_id == store_id)
                .where(Event.zone_id.is_not(None))
                .where(Event.event_type.in_(ZONE_VISIT_TYPES))
                .where(Event.is_staff.is_(False))
                .group_by(Event.zone_id)
            )
        )
    }
    dead_zones = [
        zone.name
        for zone in zones
        if zone_latest.get(zone.id) is None
        or (now - zone_latest[zone.id]) > timedelta(minutes=DEAD_ZONE_MINUTES)
    ]
    if dead_zones:
        anomalies.append(StoreAnomaly(
            anomaly_type=AnomalyType.DEAD_ZONE,
            severity=AnomalySeverity.INFO,
            description=(
                "The following zones have not received any visitors in over 30 minutes: "
                + ", ".join(dead_zones)
            ),
            suggested_action="Check signage, staff placement, or sensor coverage for these zones.",
        ))

    return anomalies
