from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.services.anomaly_service import get_store_anomalies
from app.schemas.anomaly import AnomalySeverity, AnomalyType
from app.database.models.models import Store, VisitorSession, Zone


def make_session(id: int, visitor_id: str, entry_time: datetime, exit_time: datetime | None, is_staff: bool = False) -> VisitorSession:
    return VisitorSession(
        id=id,
        store_id=1,
        visitor_id=visitor_id,
        entry_time=entry_time,
        exit_time=exit_time,
        is_repeat_visitor=False,
        is_staff=is_staff,
    )


def test_get_store_anomalies_detects_stale_feed_and_dead_zone_and_queue_spike_and_conversion_drop():
    now = datetime.now(timezone.utc)
    store = Store(id=1, store_code="STORE-001", name="Store One")

    db = MagicMock()
    db.get.return_value = store
    db.scalar.side_effect = [
        now - timedelta(minutes=11),  # last_event_time
        3,  # historical transaction sessions count
        1,  # current transaction sessions count
    ]

    # sessions include two historic visitors and one recent visitor
    nonstaff_sessions = [
        make_session(1, "visitor-1", now - timedelta(hours=2), now - timedelta(hours=1, minutes=30)),
        make_session(2, "visitor-2", now - timedelta(hours=1), now - timedelta(minutes=10)),
        make_session(3, "visitor-3", now - timedelta(minutes=20), None),
    ]
    db.scalars.side_effect = [
        MagicMock(all=MagicMock(return_value=nonstaff_sessions)),
        MagicMock(all=MagicMock(return_value=[Zone(id=1, store_id=1, name="Front", zone_type="shop", layout=None, description=None, zone_metadata=None)])),
    ]

    db.execute.side_effect = [
        [
            (1, "BILLING_QUEUE_JOIN", now - timedelta(minutes=45)),
            (1, "BILLING_QUEUE_ABANDON", now - timedelta(minutes=35)),
            (2, "BILLING_QUEUE_JOIN", now - timedelta(minutes=4)),
            (3, "BILLING_QUEUE_JOIN", now - timedelta(minutes=3)),
            (4, "BILLING_QUEUE_JOIN", now - timedelta(minutes=2)),
        ],
        [(1, now - timedelta(hours=1, minutes=10)), (2, now - timedelta(minutes=40))],
    ]

    anomalies = get_store_anomalies(db, store_id=1)
    anomaly_types = {anomaly.anomaly_type for anomaly in anomalies}

    assert AnomalyType.STALE_FEED in anomaly_types
    assert AnomalyType.DEAD_ZONE in anomaly_types
    assert AnomalyType.QUEUE_SPIKE in anomaly_types
    assert AnomalyType.CONVERSION_DROP in anomaly_types
    assert any(anomaly.severity == AnomalySeverity.CRITICAL for anomaly in anomalies)
    assert any(anomaly.severity == AnomalySeverity.WARN for anomaly in anomalies)


def test_get_store_anomalies_returns_empty_when_no_anomaly_conditions():
    now = datetime.now(timezone.utc)
    store = Store(id=1, store_code="STORE-001", name="Store One")

    db = MagicMock()
    db.get.return_value = store
    db.scalar.side_effect = [
        now,  # last_event_time
        2,  # historical transaction count
        2,  # current transaction count
    ]

    nonstaff_sessions = [
        make_session(1, "visitor-1", now - timedelta(minutes=20), None),
        make_session(2, "visitor-2", now - timedelta(minutes=10), None),
    ]
    db.scalars.side_effect = [
        MagicMock(all=MagicMock(return_value=nonstaff_sessions)),
        MagicMock(all=MagicMock(return_value=[Zone(id=1, store_id=1, name="Front", zone_type="shop", layout=None, description=None, zone_metadata=None)])),
    ]

    db.execute.side_effect = [
        [
            (1, "BILLING_QUEUE_JOIN", now - timedelta(minutes=15)),
            (2, "BILLING_QUEUE_ABANDON", now - timedelta(minutes=5)),
        ],
        [(1, now - timedelta(minutes=5)), (2, now - timedelta(minutes=7))],
    ]

    anomalies = get_store_anomalies(db, store_id=1)
    assert anomalies == []
