from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.database.models.models import Event, Store, VisitorSession
from app.services.metrics_service import get_store_metrics
from app.schemas.metrics import StoreMetrics


def make_session(id: int, visitor_id: str, entry_offset: int, exit_offset: int, is_staff: bool = False) -> VisitorSession:
    return VisitorSession(
        id=id,
        store_id=1,
        visitor_id=visitor_id,
        entry_time=datetime.now(timezone.utc) - timedelta(minutes=entry_offset),
        exit_time=datetime.now(timezone.utc) - timedelta(minutes=exit_offset) if exit_offset is not None else None,
        is_repeat_visitor=False,
        is_staff=is_staff,
    )


def test_get_store_metrics_calculates_expected_metrics():
    store = Store(id=1, store_code="STORE-001", name="Store One")
    session_a = make_session(1, "visitor-a", entry_offset=10, exit_offset=5)
    session_b = make_session(2, "visitor-b", entry_offset=8, exit_offset=3)
    session_staff = make_session(3, "staff-1", entry_offset=15, exit_offset=5, is_staff=True)

    transaction_count = 1

    queue_events = [
        (1, "BILLING_QUEUE_JOIN", datetime.now(timezone.utc) - timedelta(minutes=8)),
        (2, "BILLING_QUEUE_JOIN", datetime.now(timezone.utc) - timedelta(minutes=5)),
        (2, "BILLING_QUEUE_ABANDON", datetime.now(timezone.utc) - timedelta(minutes=2)),
    ]

    db = MagicMock()
    db.get.return_value = store
    db.scalars.return_value.all.return_value = [session_a, session_b, session_staff]
    db.scalar.return_value = transaction_count
    db.execute.return_value.all.return_value = queue_events

    metrics = get_store_metrics(db, store_id=1)

    assert isinstance(metrics, StoreMetrics)
    assert metrics.store_id == 1
    assert metrics.unique_visitors == 2
    assert metrics.conversion_rate == 0.5
    assert metrics.queue_depth == 1
    assert metrics.abandonment_rate == 0.5
    assert metrics.average_dwell_ms > 0


def test_get_store_metrics_uses_purchase_events_when_no_transactions():
    store = Store(id=1, store_code="STORE-001", name="Store One")
    session_a = make_session(1, "visitor-a", entry_offset=10, exit_offset=5)

    db = MagicMock()
    db.get.return_value = store
    db.scalars.return_value.all.return_value = [session_a]
    db.scalar.side_effect = [0, 1]
    db.execute.return_value.all.return_value = []

    metrics = get_store_metrics(db, store_id=1)

    assert metrics.conversion_rate == 1.0
