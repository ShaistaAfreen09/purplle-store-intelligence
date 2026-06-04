from pathlib import Path

from pipeline.pos_ingest import parse_pos_transactions, write_purchase_events


def test_parse_pos_transactions_reads_purchase_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "pos_transactions.csv"
    csv_path.write_text(
        "transaction_id,store_id,visitor_id,timestamp,amount,currency,payment_method,items\n"
        "txn-123,1,visitor-1,2026-05-30T17:00:00+00:00,199.99,USD,card,\"[{\\\"sku\\\": \\\"ABC123\\\", \\\"qty\\\": 1}]\"\n",
        encoding="utf-8",
    )

    events = parse_pos_transactions(str(csv_path))

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "PURCHASE"
    assert event.store_id == "1"
    assert event.camera_id == "CAM5"
    assert event.zone_id == "CHECKOUT"
    assert event.dwell_ms == 0
    assert event.metadata["transaction_reference"] == "txn-123"
    assert event.metadata["amount"] == 199.99
    assert event.metadata["currency"] == "USD"
    assert event.metadata["payment_method"] == "card"
    assert isinstance(event.metadata["items"], list)


def test_write_purchase_events_writes_jsonl(tmp_path: Path) -> None:
    csv_path = tmp_path / "pos_transactions.csv"
    out_path = tmp_path / "purchase_events.jsonl"
    csv_path.write_text(
        "transaction_id,store_id,visitor_id,timestamp,amount\n"
        "txn-456,2,visitor-2,2026-05-30 18:30:00,49.50\n",
        encoding="utf-8",
    )

    count = write_purchase_events(str(csv_path), str(out_path))

    assert count == 1
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 1
    assert "PURCHASE" in content[0]
