from __future__ import annotations

from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.models.models import Event, Store, VisitorSession
from app.schemas.funnel import FunnelStage, StoreFunnel

FUNNEL_STAGES = ["ENTRY", "ZONE_ENTER", "BILLING_QUEUE_JOIN", "PURCHASE"]


def get_store_funnel(db: Session, store_id: int) -> StoreFunnel:
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError("store not found")

    rows = db.execute(
        select(Event.event_type, Event.visitor_id, Event.session_id)
        .where(Event.store_id == store_id)
        .where(Event.event_type.in_(FUNNEL_STAGES))
        .where(Event.is_staff.is_(False))
        .outerjoin(VisitorSession, Event.session_id == VisitorSession.id)
        .where(or_(Event.session_id.is_(None), VisitorSession.is_staff.is_(False)))
        .where(Event.visitor_id.is_not(None))
    ).all()

    stage_visitors: dict[str, set[str]] = defaultdict(set)
    for event_type, visitor_id, session_id in rows:
        if visitor_id is None:
            continue
        stage_visitors[event_type].add(visitor_id)

    funnel_stages: list[FunnelStage] = []
    previous_count = None

    for stage in FUNNEL_STAGES:
        count = len(stage_visitors.get(stage, set()))
        if previous_count is None:
            conversion_rate = 1.0 if count > 0 else 0.0
            dropoff_rate = 0.0
        else:
            conversion_rate = count / previous_count if previous_count else 0.0
            dropoff_rate = 1.0 - conversion_rate

        funnel_stages.append(
            FunnelStage(
                stage=stage,
                count=count,
                dropoff_rate=round(dropoff_rate, 4),
                conversion_rate=round(conversion_rate, 4),
            )
        )
        previous_count = count

    return StoreFunnel(store_id=store_id, stages=funnel_stages)
