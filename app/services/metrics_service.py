from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.database.models.models import Event, POSTransaction, Store, VisitorSession
from app.schemas.metrics import StoreMetrics

BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
PURCHASE_EVENT_TYPE = "PURCHASE"
QUEUE_EVENT_TYPES = {BILLING_QUEUE_JOIN, BILLING_QUEUE_ABANDON}


def _extract_average_dwell_ms(sessions: Iterable[VisitorSession]) -> float:
    durations: list[float] = []

    for session in sessions:
        if session.entry_time is None or session.exit_time is None:
            continue

        delta = session.exit_time - session.entry_time
        if delta < timedelta(0):
            continue

        durations.append(delta.total_seconds() * 1000.0)

    if not durations:
        return 0.0

    return sum(durations) / len(durations)


def get_store_metrics(db: Session, store_id: int) -> StoreMetrics:
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError("store not found")

    nonstaff_sessions = db.scalars(
        select(VisitorSession)
        .where(VisitorSession.store_id == store_id)
        .where(VisitorSession.is_staff.is_(False))
    ).all()

    nonstaff_sessions = [
        session for session in nonstaff_sessions
        if not getattr(session, "is_staff", False)
    ]

    unique_visitors = len({session.visitor_id for session in nonstaff_sessions if session.visitor_id})

    transaction_sessions = db.scalar(
        select(func.count(distinct(POSTransaction.session_id)))
        .join(VisitorSession, POSTransaction.session_id == VisitorSession.id)
        .where(VisitorSession.store_id == store_id)
        .where(VisitorSession.is_staff.is_(False))
        .where(POSTransaction.session_id.is_not(None))
    )
    transaction_sessions = int(transaction_sessions or 0)

    purchase_visitors = db.scalar(
        select(func.count(distinct(Event.visitor_id)))
        .where(Event.store_id == store_id)
        .where(Event.event_type == PURCHASE_EVENT_TYPE)
        .where(Event.is_staff.is_(False))
        .where(Event.visitor_id.is_not(None))
    )
    purchase_visitors = int(purchase_visitors or 0)

    if transaction_sessions:
        conversion_rate = transaction_sessions / unique_visitors if unique_visitors else 0.0
    else:
        conversion_rate = purchase_visitors / unique_visitors if unique_visitors else 0.0

    average_dwell_ms = _extract_average_dwell_ms(nonstaff_sessions)

    queue_event_rows = db.execute(
        select(Event.session_id, Event.event_type, Event.event_time)
        .join(VisitorSession, Event.session_id == VisitorSession.id)
        .where(Event.store_id == store_id)
        .where(Event.event_type.in_(QUEUE_EVENT_TYPES))
        .where(VisitorSession.is_staff.is_(False))
        .where(Event.session_id.is_not(None))
        .order_by(Event.session_id, Event.event_time)
    ).all()

    latest_queue_event: dict[int, tuple[str, object]] = {}
    join_count = 0
    abandon_count = 0

    for session_id, event_type, event_time in queue_event_rows:
        if session_id is None:
            continue

        latest_queue_event[session_id] = (event_type, event_time)
        if event_type == BILLING_QUEUE_JOIN:
            join_count += 1
        elif event_type == BILLING_QUEUE_ABANDON:
            abandon_count += 1

    queue_depth = sum(1 for event_type, _ in latest_queue_event.values() if event_type == BILLING_QUEUE_JOIN)
    abandonment_rate = abandon_count / join_count if join_count else 0.0

    return StoreMetrics(
        store_id=store_id,
        unique_visitors=unique_visitors,
        conversion_rate=round(conversion_rate, 4),
        average_dwell_ms=round(average_dwell_ms, 2),
        queue_depth=queue_depth,
        abandonment_rate=round(abandonment_rate, 4),
    )
