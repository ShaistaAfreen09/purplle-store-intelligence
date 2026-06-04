from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("store_code", name="uq_stores_store_code"),
        Index("ix_stores_city", "city"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_sq_ft: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    store_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sessions: Mapped[list[VisitorSession]] = relationship("VisitorSession", back_populates="store", cascade="all, delete-orphan")
    zones: Mapped[list[Zone]] = relationship("Zone", back_populates="store", cascade="all, delete-orphan")
    events: Mapped[list[Event]] = relationship("Event", back_populates="store", cascade="all, delete-orphan")
    anomalies: Mapped[list[Anomaly]] = relationship("Anomaly", back_populates="store", cascade="all, delete-orphan")
    transactions: Mapped[list[POSTransaction]] = relationship("POSTransaction", back_populates="store", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("store_id", "name", name="uq_zones_store_name"),
        Index("ix_zones_store_id", "store_id"),
        Index("ix_zones_zone_type", "zone_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(64), nullable=False)
    layout: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="zones")
    transactions: Mapped[list[POSTransaction]] = relationship("POSTransaction", back_populates="zone", cascade="all, delete-orphan")


class VisitorSession(Base):
    __tablename__ = "visitor_sessions"
    __table_args__ = (
        Index("ix_visitor_sessions_store_entry", "store_id", "entry_time"),
        Index("ix_visitor_sessions_store_exit", "store_id", "exit_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    visitor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_repeat_visitor: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    session_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="sessions")
    events: Mapped[list[Event]] = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    anomalies: Mapped[list[Anomaly]] = relationship("Anomaly", back_populates="session", cascade="all, delete-orphan")
    transactions: Mapped[list[POSTransaction]] = relationship("POSTransaction", back_populates="session", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_events_event_id"),
        Index("ix_events_event_id", "event_id"),
        Index("ix_events_session_time", "session_id", "event_time"),
        Index("ix_events_store_type_time", "store_id", "event_type", "event_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="SET NULL"), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    visitor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dwell_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    sequence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="events")
    session: Mapped[VisitorSession | None] = relationship("VisitorSession", back_populates="events")
    anomalies: Mapped[list[Anomaly]] = relationship("Anomaly", back_populates="event", cascade="all, delete-orphan")


class Anomaly(Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        Index("ix_anomalies_store_detected", "store_id", "detected_at"),
        Index("ix_anomalies_type_status", "anomaly_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="SET NULL"), nullable=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    anomaly_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, server_default="medium")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomaly_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="anomalies")
    session: Mapped[VisitorSession | None] = relationship("VisitorSession", back_populates="anomalies")
    event: Mapped[Event | None] = relationship("Event", back_populates="anomalies")


class POSTransaction(Base):
    __tablename__ = "pos_transactions"
    __table_args__ = (
        UniqueConstraint("transaction_reference", name="uq_pos_transactions_reference"),
        Index("ix_pos_transactions_store_time", "store_id", "transaction_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("visitor_sessions.id", ondelete="SET NULL"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    transaction_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    transaction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default="USD")
    payment_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    items: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    transaction_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="transactions")
    session: Mapped[VisitorSession | None] = relationship("VisitorSession", back_populates="transactions")
    zone: Mapped[Zone | None] = relationship("Zone", back_populates="transactions")
