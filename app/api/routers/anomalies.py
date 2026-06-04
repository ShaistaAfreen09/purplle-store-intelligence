from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.anomaly import StoreAnomaly
from app.services.anomaly_service import get_store_anomalies

router = APIRouter()


@router.get("/{store_id}/anomalies", response_model=list[StoreAnomaly])
def read_store_anomalies(store_id: int, db: Session = Depends(get_db)) -> list[StoreAnomaly]:
    try:
        return get_store_anomalies(db, store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
