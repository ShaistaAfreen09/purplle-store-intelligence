from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.funnel import StoreFunnel
from app.schemas.metrics import StoreMetrics
from app.services.funnel_service import get_store_funnel
from app.services.metrics_service import get_store_metrics

router = APIRouter()


@router.get("/{store_id}/metrics", response_model=StoreMetrics)
def read_store_metrics(store_id: int, db: Session = Depends(get_db)) -> StoreMetrics:
    try:
        return get_store_metrics(db, store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")


@router.get("/{store_id}/funnel", response_model=StoreFunnel)
def read_store_funnel(store_id: int, db: Session = Depends(get_db)) -> StoreFunnel:
    try:
        return get_store_funnel(db, store_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Store not found")
