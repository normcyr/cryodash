"""Database models and Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.sql import func

from cryodash.database import Base


# SQLAlchemy Models
class CryogenReading(Base):
    """Table for storing cryogenic level readings."""

    __tablename__ = "cryogen_readings"

    id = Column(Integer, primary_key=True, index=True)
    device = Column(String(50), nullable=False, index=True)  # e.g., "neo600", "neo700"
    cryogen = Column(String(10), nullable=False)  # e.g., "N2", "He"
    level = Column(Float, nullable=False)  # Percentage (0-100)
    timestamp = Column(DateTime, nullable=False, index=True, default=func.now())
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_device_timestamp", "device", "timestamp"),
        Index("idx_device_cryogen_timestamp", "device", "cryogen", "timestamp"),
    )


class Instrument(Base):
    """Table for instrument metadata."""

    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g., "neo600", "neo700"
    frequency = Column(String(20), nullable=False)  # e.g., "600 MHz"
    description = Column(String(255))
    cryogens = Column(String(50), nullable=False)  # e.g., "N2" or "N2,He"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SyncHistory(Base):
    """Table for tracking log synchronization events."""

    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False)  # "success", "partial", "failed"
    total_imported = Column(Integer, default=0)
    files_processed = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error_message = Column(String(500), nullable=True)
    details = Column(String(2000), nullable=True)  # JSON string with per-file results


# Pydantic Schemas
class CryogenReadingSchema(BaseModel):
    """Schema for cryogenic reading."""

    id: int
    device: str
    cryogen: str
    level: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class CryogenReadingCreateSchema(BaseModel):
    """Schema for creating cryogenic reading."""

    device: str
    cryogen: str
    level: float = Field(ge=0.0, le=100.0, description="Level percentage (0-100%)")
    timestamp: Optional[datetime] = None


class CryogenCurrentSchema(BaseModel):
    """Schema for current cryogenic level."""

    cryogen: str
    level: float
    timestamp: datetime
    status: str  # "ok", "warning", "critical"


class InstrumentSchema(BaseModel):
    """Schema for instrument."""

    id: int
    name: str
    frequency: str
    description: Optional[str] = None
    cryogens: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstrumentCreateSchema(BaseModel):
    """Schema for creating instrument."""

    name: str
    frequency: str
    description: Optional[str] = None
    cryogens: str  # e.g., "N2" or "N2,He"


class InstrumentDetailSchema(BaseModel):
    """Detailed instrument schema with current readings."""

    id: int
    name: str
    frequency: str
    description: Optional[str] = None
    cryogens: str
    current: list[CryogenCurrentSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncHistorySchema(BaseModel):
    """Schema for sync history record."""

    id: int
    started_at: datetime
    completed_at: datetime
    status: str
    total_imported: int
    files_processed: int
    files_failed: int
    error_message: Optional[str] = None
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvaporationRateSchema(BaseModel):
    """Schema for evaporation rate calculation with refill detection."""

    device: str
    cryogen: str
    rate_percent_per_day: float
    last_24h_change: float
    hours_calculated: float
    latest_level: float
    oldest_level: float
    latest_timestamp: datetime
    oldest_timestamp: datetime
    refill_detected: bool = False
    last_refill_timestamp: Optional[datetime] = None
