from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routers import stores
from app.schemas.metrics import StoreMetrics


def test_store_metrics_endpoint_returns_metrics(monkeypatch):
    expected = StoreMetrics(
        store_id=42,
        unique_visitors=10,
        conversion_rate=0.25,
        average_dwell_ms=35000.0,
        queue_depth=3,
        abandonment_rate=0.2,
    )

    def fake_get_db():
        yield None

    def fake_get_store_metrics(db, store_id: int):
        return expected

    monkeypatch.setattr(stores, "get_db", fake_get_db)
    monkeypatch.setattr(stores, "get_store_metrics", fake_get_store_metrics)

    client = TestClient(app)
    response = client.get("/stores/42/metrics")

    assert response.status_code == 200
    assert response.json() == expected.model_dump()
