from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.api.routers import events as events_router
from app.api.routers import stores as stores_router
from app.database.models.models import Base, POSTransaction, Store, VisitorSession
import pipeline.ingest_api as ingest_api


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


def test_end_to_end_jsonl_ingestion_and_metrics_retrieval(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

    def fake_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[events_router.get_db] = fake_get_db
    app.dependency_overrides[stores_router.get_db] = fake_get_db

    try:
        with SessionLocal() as db:
            store = Store(
                store_code="STORE-1",
                name="Test Store",
                address="123 Main St",
                city="Testville",
                state="TS",
                country="IN",
                area_sq_ft=1200.0,
            )
            db.add(store)
            db.commit()
            db.refresh(store)

            session_record = VisitorSession(
                store_id=store.id,
                visitor_id="visitor-1",
                entry_time=datetime(2026, 5, 30, 0, 0, tzinfo=timezone.utc),
                exit_time=datetime(2026, 5, 30, 0, 2, tzinfo=timezone.utc),
                device_type="camera",
                is_staff=False,
                is_repeat_visitor=False,
            )
            db.add(session_record)
            db.commit()
            db.refresh(session_record)

            transaction_record = POSTransaction(
                store_id=store.id,
                session_id=session_record.id,
                transaction_reference="txn-1",
                transaction_time=datetime(2026, 5, 30, 0, 1, tzinfo=timezone.utc),
                amount=42.5,
                currency="USD",
            )
            db.add(transaction_record)
            db.commit()

        jsonl_path = tmp_path / "events.jsonl"
        event_payload = {
            "event_id": "event-1",
            "store_id": str(store.id),
            "camera_id": "cam-1",
            "visitor_id": "visitor-1",
            "event_type": "PURCHASE",
            "timestamp": "2026-05-30T00:00:00+00:00",
            "zone_id": None,
            "dwell_ms": None,
            "is_staff": False,
            "confidence": 0.85,
            "metadata": {},
        }
        jsonl_path.write_text(json.dumps(event_payload) + "\n", encoding="utf-8")

        original_test_client = TestClient

        def client_factory(*args: object, **kwargs: object) -> TestClient:
            return original_test_client(app)

        monkeypatch.setattr(ingest_api.httpx, "Client", client_factory)

        summary = ingest_api.ingest_jsonl_file(str(jsonl_path), api_url="http://testserver/events/ingest", batch_size=10)

        assert summary["accepted"] == 1
        assert summary["duplicates"] == 0
        assert summary["rejected"] == 0
        assert summary["errors"] == 0

        client = TestClient(app)
        response = client.get(f"/stores/{store.id}/metrics")
        assert response.status_code == 200

        metrics = response.json()
        assert metrics["store_id"] == store.id
        assert metrics["unique_visitors"] == 1
        assert metrics["conversion_rate"] == 1.0
        assert metrics["average_dwell_ms"] == 120000.0
        assert metrics["queue_depth"] == 0
        assert metrics["abandonment_rate"] == 0.0
    finally:
        app.dependency_overrides.clear()
