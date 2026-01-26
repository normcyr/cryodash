"""Simple unit and integration tests for CryoDash."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from cryodash.main import app
from cryodash.models import CryogenReading, Instrument


@pytest.fixture
def client(test_db):
    """Create a test client with test database."""
    return TestClient(app)


# ============================================================================
# Basic API Tests
# ============================================================================


def test_health_check(client):
    """Test GET /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_instruments(client):
    """Test GET /api/instruments endpoint."""
    response = client.get("/api/instruments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_sync_status(client):
    """Test GET /api/sync-status."""
    response = client.get("/api/sync-status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


# ============================================================================
# Model Unit Tests
# ============================================================================


def test_cryogen_reading_model_creation():
    """Test CryogenReading model creation."""
    reading = CryogenReading(
        device="neo600",
        cryogen="N2",
        level=87.5,
        timestamp=datetime.now(),
    )
    assert reading.device == "neo600"
    assert reading.cryogen == "N2"
    assert reading.level == 87.5


def test_instrument_model_creation():
    """Test Instrument model creation."""
    instrument = Instrument(
        name="neo600",
        frequency="600 MHz",
        description="Test",
        cryogens="N2",
    )
    assert instrument.name == "neo600"
    assert instrument.frequency == "600 MHz"


# ============================================================================
# Schema Tests
# ============================================================================


def test_cryogen_reading_schema():
    """Test CryogenReadingSchema."""
    from cryodash.models import CryogenReadingSchema

    data = {
        "id": 1,
        "device": "neo600",
        "cryogen": "N2",
        "level": 87.5,
        "timestamp": datetime.now(),
    }
    schema = CryogenReadingSchema(**data)
    assert schema.device == "neo600"
    assert schema.level == 87.5


def test_instrument_schema():
    """Test InstrumentSchema."""
    from cryodash.models import InstrumentSchema

    data = {
        "id": 1,
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    schema = InstrumentSchema(**data)
    assert schema.name == "neo600"


def test_evaporation_rate_schema():
    """Test EvaporationRateSchema."""
    from datetime import datetime

    from cryodash.models import EvaporationRateSchema

    now = datetime.now()
    data = {
        "device": "neo600",
        "cryogen": "N2",
        "rate_percent_per_day": -2.5,
        "last_24h_change": -1.5,
        "hours_calculated": 24.0,
        "latest_level": 87.5,
        "oldest_level": 89.0,
        "latest_timestamp": now,
        "oldest_timestamp": now,
        "refill_detected": False,
        "last_refill_timestamp": None,
    }
    schema = EvaporationRateSchema(**data)
    assert schema.device == "neo600"
    assert schema.refill_detected is False


# ============================================================================
# Helper Functions Tests
# ============================================================================


def test_alert_status_functions():
    """Test alert status calculation."""
    from cryodash.api.routes import _get_alert_status

    # N2: normal 60-100%, warning 30-59%, critical 10-29%, catastrophic 0-9%
    assert _get_alert_status("neo600", "N2", 80.0) == "ok"
    assert _get_alert_status("neo600", "N2", 45.0) == "warning"
    assert _get_alert_status("neo600", "N2", 15.0) == "critical"
    assert _get_alert_status("neo600", "N2", 5.0) == "catastrophic"
