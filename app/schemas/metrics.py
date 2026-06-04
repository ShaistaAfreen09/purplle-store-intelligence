from __future__ import annotations

from pydantic import BaseModel, Field


class StoreMetrics(BaseModel):
    store_id: int = Field(..., ge=1)
    unique_visitors: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0.0, le=1.0)
    average_dwell_ms: float = Field(..., ge=0.0)
    queue_depth: int = Field(..., ge=0)
    abandonment_rate: float = Field(..., ge=0.0, le=1.0)
