"""WebSocket connection management for real-time data streaming."""

import logging
from typing import Optional, cast

from fastapi import WebSocket

from cryodash.database import SessionLocal
from cryodash.models import CryogenReading

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections and broadcast updates."""

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, instrument_id: str):
        """
        Register a new WebSocket connection for an instrument.

        Args:
            websocket: The WebSocket connection
            instrument_id: The instrument ID to monitor
        """
        await websocket.accept()
        if instrument_id not in self.active_connections:
            self.active_connections[instrument_id] = set()
        self.active_connections[instrument_id].add(websocket)
        logger.info(
            f"WebSocket connected for instrument {instrument_id}. "
            f"Total connections: {len(self.active_connections[instrument_id])}"
        )

    def disconnect(self, websocket: WebSocket, instrument_id: str):
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            instrument_id: The instrument ID
        """
        if instrument_id in self.active_connections:
            self.active_connections[instrument_id].discard(websocket)
            if not self.active_connections[instrument_id]:
                del self.active_connections[instrument_id]
            logger.info(
                f"WebSocket disconnected for instrument {instrument_id}. "
                f"Remaining connections: "
                f"{len(self.active_connections.get(instrument_id, []))}"
            )

    async def broadcast(
        self, instrument_id: str, message: dict, exclude: Optional[WebSocket] = None
    ):
        """
        Broadcast a message to all connections for an instrument.

        Args:
            instrument_id: The instrument ID
            message: The message to broadcast
            exclude: Optional connection to exclude from broadcast
        """
        if instrument_id not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[instrument_id]:
            if exclude and connection == exclude:
                continue
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, instrument_id)

    async def send_latest_reading(self, websocket: WebSocket, instrument_id: str):
        """
        Send the latest reading for an instrument to a specific connection.

        Args:
            websocket: The WebSocket connection
            instrument_id: The instrument ID
        """
        # Import here to avoid circular import
        from cryodash.api.routes import _get_alert_status

        db = SessionLocal()
        try:
            latest = (
                db.query(CryogenReading)
                .filter(CryogenReading.device == instrument_id)
                .order_by(CryogenReading.timestamp.desc())
                .first()
            )

            if latest:
                status = _get_alert_status(
                    cast(str, latest.device),
                    cast(str, latest.cryogen),
                    cast(float, latest.level),
                )
                message = {
                    "type": "reading",
                    "data": {
                        "id": latest.id,
                        "device": latest.device,
                        "cryogen": latest.cryogen,
                        "level": latest.level,
                        "timestamp": latest.timestamp.isoformat(),
                        "status": status,
                    },
                }
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending latest reading: {e}")
        finally:
            db.close()


# Global connection manager instance
manager = ConnectionManager()
