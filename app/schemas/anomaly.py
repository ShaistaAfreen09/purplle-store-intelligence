from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnomalyType(str, Enum):
    QUEUE_SPIKE = "QUEUE_SPIKE"
    CONVERSION_DROP = "CONVERSION_DROP"
    DEAD_ZONE = "DEAD_ZONE"
    STALE_FEED = "STALE_FEED"


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class StoreAnomaly(BaseModel):
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    description: str = Field(..., min_length=1)
    suggested_action: str = Field(..., min_length=1)
