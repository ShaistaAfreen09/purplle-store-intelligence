from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routers import anomalies
from app.schemas.anomaly import AnomalySeverity, AnomalyType, StoreAnomaly


def test_store_anomalies_endpoint_returns_anomalies(monkeypatch):
    expected = [
        StoreAnomaly(
            anomaly_type=AnomalyType.STALE_FEED,
            severity=AnomalySeverity.CRITICAL,
            description="No events have been received for more than 10 minutes.",
            suggested_action="Check event feed connectivity and confirm sensor or camera data are arriving.",
        )
    ]

    def fake_get_db():
        yield None

    def fake_get_store_anomalies(db, store_id: int):
        return expected

    monkeypatch.setattr(anomalies, "get_db", fake_get_db)
    monkeypatch.setattr(anomalies, "get_store_anomalies", fake_get_store_anomalies)

    client = TestClient(app)
    response = client.get("/stores/42/anomalies")

    assert response.status_code == 200
    assert response.json() == [item.model_dump() for item in expected]
