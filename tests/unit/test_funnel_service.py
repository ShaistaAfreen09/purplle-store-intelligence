from unittest.mock import MagicMock

from app.services.funnel_service import get_store_funnel
from app.schemas.funnel import FunnelStage, StoreFunnel
from app.database.models.models import Store


def test_get_store_funnel_counts_unique_visitors_and_filters_reentry():
    store = Store(id=1, store_code="STORE-001", name="Store One")

    rows = [
        ("ENTRY", "visitor-1", 1),
        ("ZONE_ENTER", "visitor-1", 1),
        ("BILLING_QUEUE_JOIN", "visitor-1", 1),
        ("PURCHASE", "visitor-1", 1),
        ("ENTRY", "visitor-1", 1),
        ("ZONE_ENTER", "visitor-1", 1),
        ("ENTRY", "visitor-2", 2),
    ]

    db = MagicMock()
    db.get.return_value = store
    db.execute.return_value.all.return_value = rows

    funnel = get_store_funnel(db, store_id=1)

    assert isinstance(funnel, StoreFunnel)
    assert funnel.store_id == 1
    assert funnel.stages == [
        FunnelStage(stage="ENTRY", count=2, dropoff_rate=0.0, conversion_rate=1.0),
        FunnelStage(stage="ZONE_ENTER", count=1, dropoff_rate=0.5, conversion_rate=0.5),
        FunnelStage(stage="BILLING_QUEUE_JOIN", count=1, dropoff_rate=0.0, conversion_rate=1.0),
        FunnelStage(stage="PURCHASE", count=1, dropoff_rate=0.0, conversion_rate=1.0),
    ]


def test_get_store_funnel_raises_value_error_for_missing_store():
    db = MagicMock()
    db.get.return_value = None

    try:
        get_store_funnel(db, store_id=1)
        assert False, "Expected ValueError for missing store"
    except ValueError:
        pass
