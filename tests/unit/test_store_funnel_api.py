from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routers import stores
from app.schemas.funnel import StoreFunnel, FunnelStage


def test_store_funnel_endpoint_returns_funnel(monkeypatch):
    expected = StoreFunnel(
        store_id=42,
        stages=[
            FunnelStage(stage="ENTRY", count=10, dropoff_rate=0.0, conversion_rate=1.0),
            FunnelStage(stage="ZONE_ENTER", count=8, dropoff_rate=0.2, conversion_rate=0.8),
            FunnelStage(stage="BILLING_QUEUE_JOIN", count=5, dropoff_rate=0.375, conversion_rate=0.625),
            FunnelStage(stage="PURCHASE", count=3, dropoff_rate=0.4, conversion_rate=0.6),
        ],
    )

    def fake_get_db():
        yield None

    def fake_get_store_funnel(db, store_id: int):
        return expected

    monkeypatch.setattr(stores, "get_db", fake_get_db)
    monkeypatch.setattr(stores, "get_store_funnel", fake_get_store_funnel)

    client = TestClient(app)
    response = client.get("/stores/42/funnel")

    assert response.status_code == 200
    assert response.json() == expected.model_dump()
