"""API routes for CryoDash."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from cryodash.config import ALERT_THRESHOLDS
from cryodash.database import get_db
from cryodash.models import (
    CryogenCurrentSchema,
    CryogenReading,
    CryogenReadingCreateSchema,
    CryogenReadingSchema,
    EvaporationRateSchema,
    Instrument,
    InstrumentCreateSchema,
    InstrumentDetailSchema,
    InstrumentSchema,
    SyncHistory,
    SyncHistorySchema,
)
from cryodash.scripts.sync_remote_logs import sync_logs
from cryodash.websocket import manager

router = APIRouter(prefix="/api", tags=["api"])


def _get_alert_status(device: str, cryogen: str, level: float) -> str:
    """Determine alert status based on threshold."""
    thresholds = ALERT_THRESHOLDS.get(device, {}).get(cryogen, {})
    critical = thresholds.get("critical", 0)
    warning = thresholds.get("warning", float("inf"))

    if level <= critical:
        return "critical"
    elif level <= warning:
        return "warning"
    return "ok"


@router.get("/instruments", response_model=list[InstrumentSchema])
def get_instruments(db: Session = Depends(get_db)):
    """Get list of all instruments."""
    instruments = db.query(Instrument).all()
    return instruments


@router.get("/instruments/{name}", response_model=InstrumentDetailSchema)
def get_instrument_detail(name: str, db: Session = Depends(get_db)):
    """Get detailed information about an instrument including current levels."""
    instrument = db.query(Instrument).filter(Instrument.name == name).first()

    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    # Get current readings for each cryogen
    cryogens = instrument.cryogens.split(",")
    current_readings = []

    for cryogen in cryogens:
        cryogen = cryogen.strip()
        # Get latest reading
        latest = (
            db.query(CryogenReading)
            .filter(
                and_(
                    CryogenReading.device == name,
                    CryogenReading.cryogen == cryogen,
                )
            )
            .order_by(desc(CryogenReading.timestamp))
            .first()
        )

        if latest:
            status = _get_alert_status(name, cryogen, latest.level)
            current_readings.append(
                CryogenCurrentSchema(
                    cryogen=cryogen,
                    level=latest.level,
                    timestamp=latest.timestamp,
                    status=status,
                )
            )

    return InstrumentDetailSchema(
        id=instrument.id,
        name=instrument.name,
        frequency=instrument.frequency,
        description=instrument.description,
        cryogens=instrument.cryogens,
        current=current_readings,
        created_at=instrument.created_at,
        updated_at=instrument.updated_at,
    )


@router.get("/instruments/{name}/current", response_model=list[CryogenCurrentSchema])
def get_instrument_current(name: str, db: Session = Depends(get_db)):
    """Get current cryogenic levels for an instrument."""
    instrument = db.query(Instrument).filter(Instrument.name == name).first()

    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    cryogens = instrument.cryogens.split(",")
    current_readings = []

    for cryogen in cryogens:
        cryogen = cryogen.strip()
        latest = (
            db.query(CryogenReading)
            .filter(
                and_(
                    CryogenReading.device == name,
                    CryogenReading.cryogen == cryogen,
                )
            )
            .order_by(desc(CryogenReading.timestamp))
            .first()
        )

        if latest:
            status = _get_alert_status(name, cryogen, latest.level)
            current_readings.append(
                CryogenCurrentSchema(
                    cryogen=cryogen,
                    level=latest.level,
                    timestamp=latest.timestamp,
                    status=status,
                )
            )

    return current_readings


@router.get("/instruments/{name}/history", response_model=list[CryogenReadingSchema])
def get_instrument_history(
    name: str,
    cryogen: Optional[str] = Query(None, description="Cryogen type (N2 or He)"),
    hours: int = Query(24, description="Hours of history to retrieve"),
    limit: int = Query(1000, description="Maximum number of records"),
    db: Session = Depends(get_db),
):
    """Get historical cryogenic readings for an instrument."""
    instrument = db.query(Instrument).filter(Instrument.name == name).first()

    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(CryogenReading).filter(
        and_(
            CryogenReading.device == name,
            CryogenReading.timestamp >= cutoff_time,
        )
    )

    if cryogen:
        query = query.filter(CryogenReading.cryogen == cryogen.upper())

    readings = query.order_by(desc(CryogenReading.timestamp)).limit(limit).all()

    return sorted(readings, key=lambda x: x.timestamp)


@router.post("/readings", response_model=CryogenReadingSchema)
def create_reading(
    reading: CryogenReadingCreateSchema,
    db: Session = Depends(get_db),
):
    """Create a new cryogenic reading."""
    timestamp = reading.timestamp if reading.timestamp else datetime.utcnow()
    db_reading = CryogenReading(
        device=reading.device,
        cryogen=reading.cryogen,
        level=reading.level,
        timestamp=timestamp,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


@router.post("/instruments", response_model=InstrumentSchema)
def create_instrument(
    instrument: InstrumentCreateSchema,
    db: Session = Depends(get_db),
):
    """Create a new instrument."""
    db_instrument = Instrument(
        name=instrument.name,
        frequency=instrument.frequency,
        description=instrument.description,
        cryogens=instrument.cryogens,
    )
    db.add(db_instrument)
    db.commit()
    db.refresh(db_instrument)
    return db_instrument


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/sync-logs")
def sync_logs_endpoint():
    """Manually trigger log synchronization from remote server."""
    try:
        results = sync_logs()
        return {
            "status": "success",
            "timestamp": results["timestamp"],
            "total_imported": results["total_imported"],
            "files_processed": results["files_processed"],
            "files_failed": results["files_failed"],
            "details": results["details"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}") from e


@router.get("/sync-status")
def sync_status():
    """Get information about the scheduled sync."""
    return {
        "status": "running",
        "schedule": "Every 1 hour",
        "next_sync": "Scheduled automatically at startup",
        "manual_sync_endpoint": "POST /api/sync-logs",
    }


@router.get("/sync-history")
def get_sync_history(db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=500)):
    """Get sync history records."""
    records = db.query(SyncHistory).order_by(desc(SyncHistory.started_at)).limit(limit).all()
    return [SyncHistorySchema.from_orm(record) for record in records]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get general statistics about the database."""
    total_readings = db.query(CryogenReading).count()
    total_instruments = db.query(Instrument).count()

    # Find latest reading timestamp
    latest = db.query(CryogenReading).order_by(desc(CryogenReading.timestamp)).first()
    latest_timestamp = latest.timestamp if latest else None

    # Find oldest reading timestamp
    oldest = db.query(CryogenReading).order_by(CryogenReading.timestamp).first()
    oldest_timestamp = oldest.timestamp if oldest else None

    return {
        "total_readings": total_readings,
        "total_instruments": total_instruments,
        "latest_reading_timestamp": latest_timestamp,
        "oldest_reading_timestamp": oldest_timestamp,
        "latest_sync": (
            db.query(SyncHistory).order_by(desc(SyncHistory.completed_at)).first().completed_at
            if db.query(SyncHistory).count() > 0
            else None
        ),
    }


@router.get("/evaporation-rate")
def get_evaporation_rates(
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=8760),
    device: str = Query(None),
):
    """
    Calculate evaporation rates (% per day) for cryogens.

    Automatically detects refills (sudden level increases) and calculates
    evaporation rate only from the last refill onwards, ignoring historical
    filling periods.

    Args:
        hours: Number of hours to look back (default 24)
        device: Filter by specific device (optional)

    Returns:
        List of EvaporationRateSchema with:
        - rate_percent_per_day: Negative values = evaporation, positive = replenishment
        - last_refill_timestamp: When the last refill was detected
        - refill_detected: Boolean indicating if refill was detected in period
    """
    evaporation_rates = []

    # Get all instruments
    instruments = db.query(Instrument).all()
    if device:
        instruments = [i for i in instruments if i.name == device]

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for instrument in instruments:
        # Parse cryogens
        cryogens = instrument.cryogens.split(",") if instrument.cryogens else []

        for cryogen in cryogens:
            cryogen = cryogen.strip().upper()

            # Get all readings in the time window, ordered by timestamp
            readings = (
                db.query(CryogenReading)
                .filter(
                    and_(
                        CryogenReading.device == instrument.name,
                        CryogenReading.cryogen == cryogen,
                        CryogenReading.timestamp >= cutoff_time,
                    )
                )
                .order_by(CryogenReading.timestamp)
                .all()
            )

            if len(readings) < 2:
                continue  # Skip if not enough data points

            # Detect refills (sudden level increases)
            refill_threshold = 10.0  # % increase considered a refill
            last_refill_index = 0  # Start from first reading
            last_refill_timestamp = readings[0].timestamp

            for i in range(1, len(readings)):
                level_increase = readings[i].level - readings[i - 1].level
                # Detect refill if increase > threshold and not just measurement noise
                if level_increase > refill_threshold:
                    last_refill_index = i
                    last_refill_timestamp = readings[i].timestamp

            # Use readings from last refill onwards
            relevant_readings = readings[last_refill_index:]
            refill_detected = last_refill_index > 0

            if len(relevant_readings) < 2:
                continue  # Need at least 2 points after refill

            oldest = relevant_readings[0]
            latest = relevant_readings[-1]

            time_diff = (latest.timestamp - oldest.timestamp).total_seconds() / 3600  # hours
            if time_diff == 0:
                continue

            level_change = latest.level - oldest.level  # Negative = evaporation
            rate_percent_per_day = (level_change / time_diff) * 24  # Normalize to per day

            # Create extended schema with refill info
            rate_data = {
                "device": instrument.name,
                "cryogen": cryogen,
                "rate_percent_per_day": round(rate_percent_per_day, 2),
                "last_24h_change": round(level_change, 2),
                "hours_calculated": round(time_diff, 1),
                "latest_level": latest.level,
                "oldest_level": oldest.level,
                "latest_timestamp": latest.timestamp,
                "oldest_timestamp": oldest.timestamp,
                "refill_detected": refill_detected,
                "last_refill_timestamp": last_refill_timestamp if refill_detected else None,
            }

            evaporation_rates.append(EvaporationRateSchema(**rate_data))

    return evaporation_rates


@router.websocket("/ws/readings/{instrument_id}")
async def websocket_readings(websocket: WebSocket, instrument_id: str):
    """
    WebSocket endpoint for real-time cryogenic readings.

    Clients connect to receive live updates of cryogenic levels for an instrument.
    """
    await manager.connect(websocket, instrument_id)
    # Send latest reading immediately upon connection
    await manager.send_latest_reading(websocket, instrument_id)

    try:
        while True:
            # Keep connection open and receive messages
            # (We don't expect client messages, but we listen for disconnects)
            data = await websocket.receive_text()
            # Echo back or ignore client messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, instrument_id)
    except Exception:
        manager.disconnect(websocket, instrument_id)
        raise
