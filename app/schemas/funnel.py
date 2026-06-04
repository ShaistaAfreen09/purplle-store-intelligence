from __future__ import annotations

from pydantic import BaseModel, Field


class FunnelStage(BaseModel):
    stage: str
    count: int = Field(..., ge=0)
    dropoff_rate: float = Field(..., ge=0.0, le=1.0)
    conversion_rate: float = Field(..., ge=0.0, le=1.0)


class StoreFunnel(BaseModel):
    store_id: int = Field(..., ge=1)
    stages: list[FunnelStage]
