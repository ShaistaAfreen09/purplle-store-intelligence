#!/usr/bin/env sh
set -e

python - <<'PY'
import time
from sqlalchemy import exc, text
from app.database.connection import engine
from app.database.models.models import Base

wait_seconds = 30
deadline = time.time() + wait_seconds
while time.time() < deadline:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except exc.SQLAlchemyError:
        time.sleep(1)
else:
    raise SystemExit(f"Database did not become available within {wait_seconds} seconds")

Base.metadata.create_all(bind=engine)
PY

exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
