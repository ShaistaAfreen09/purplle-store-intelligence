from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    PURCHASE = "PURCHASE"
    REENTRY = "REENTRY"


class ChallengeEvent(BaseModel):
    event_id: StrictStr = Field(..., min_length=1)
    store_id: StrictStr = Field(..., min_length=1)
    camera_id: StrictStr = Field(..., min_length=1)
    visitor_id: StrictStr = Field(..., min_length=1)
    event_type: EventType = Field(...)
    timestamp: datetime = Field(...)
    zone_id: StrictStr | None = Field(default=None, min_length=1)
    dwell_ms: StrictInt | None = Field(default=None, ge=0)
    is_staff: StrictBool = Field(...)
    confidence: StrictFloat = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("metadata must be a JSON object")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone information")
        return value

    class Config:
        populate_by_name = True
        extra = "forbid"
