"""Comprehensive tests for CryoDash."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from cryodash.main import app
from cryodash.models import CryogenReading, Instrument


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Basic Endpoint Tests
# ============================================================================


def test_health_check(client):
    """Test GET /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_instruments_empty(client):
    """Test GET /api/instruments when empty."""
    response = client.get("/api/instruments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_instrument(client):
    """Test POST /api/instruments."""
    instrument_data = {
        "name": "test-neo600",
        "frequency": "600 MHz",
        "description": "Test instrument",
        "cryogens": "N2",
    }
    response = client.post("/api/instruments", json=instrument_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-neo600"
    assert data["frequency"] == "600 MHz"


def test_sync_status(client):
    """Test GET /api/sync-status."""
    response = client.get("/api/sync-status")
    assert response.status_code == 200
    assert "status" in response.json()


def test_get_sync_history(client):
    """Test GET /api/sync-history."""
    response = client.get("/api/sync-history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_stats(client):
    """Test GET /api/stats."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_readings" in data
    assert "total_instruments" in data
    assert "devices" in data


def test_get_evaporation_rate(client):
    """Test GET /api/evaporation-rate."""
    response = client.get("/api/evaporation-rate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_reading(client):
    """Test POST /api/readings."""
    reading_data = {
        "device": "test-device",
        "cryogen": "N2",
        "level": 85.5,
        "timestamp": datetime.now().isoformat(),
    }
    response = client.post("/api/readings", json=reading_data)
    assert response.status_code == 200
    data = response.json()
    assert data["device"] == "test-device"
    assert data["level"] == 85.5


# ============================================================================
# Model Tests
# ============================================================================


class TestCryogenReadingModel:
    """Test CryogenReading model."""

    def test_creation(self):
        """Test creating CryogenReading."""
        reading = CryogenReading(
            device="neo600",
            cryogen="N2",
            level=87.5,
            timestamp=datetime.now(),
        )
        assert reading.device == "neo600"
        assert reading.cryogen == "N2"
        assert reading.level == 87.5

    def test_level_range(self):
        """Test various level values."""
        for level in [0.0, 50.0, 100.0]:
            reading = CryogenReading(
                device="neo600",
                cryogen="N2",
                level=level,
            )
            assert reading.level == level


class TestInstrumentModel:
    """Test Instrument model."""

    def test_creation(self):
        """Test creating Instrument."""
        instrument = Instrument(
            name="neo600",
            frequency="600 MHz",
            description="Test",
            cryogens="N2",
        )
        assert instrument.name == "neo600"
        assert instrument.frequency == "600 MHz"

    def test_without_description(self):
        """Test creating instrument without description."""
        instrument = Instrument(
            name="neo700",
            frequency="700 MHz",
            cryogens="N2,He",
        )
        assert instrument.description is None
        assert instrument.cryogens == "N2,He"


# ============================================================================
# Schema Tests
# ============================================================================


class TestSchemas:
    """Test Pydantic schemas."""

    def test_cryogen_reading_schema(self):
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

    def test_cryogen_reading_create_schema(self):
        """Test CryogenReadingCreateSchema."""
        from cryodash.models import CryogenReadingCreateSchema

        data = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 87.5,
        }
        schema = CryogenReadingCreateSchema(**data)
        assert schema.device == "neo600"

    def test_instrument_schema(self):
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

    def test_evaporation_rate_schema(self):
        """Test EvaporationRateSchema."""
        from cryodash.models import EvaporationRateSchema

        data = {
            "device": "neo600",
            "cryogen": "N2",
            "rate_percent_per_day": -2.5,
        }
        schema = EvaporationRateSchema(**data)
        assert schema.device == "neo600"
        assert schema.rate_percent_per_day == -2.5
        assert schema.refill_detected is False


# ============================================================================
# Alert Status Tests
# ============================================================================


def test_alert_status_ok(client):
    """Test alert status calculation."""
    from cryodash.api.routes import _get_alert_status

    status = _get_alert_status("neo600", "N2", 50.0)
    assert status == "ok"


def test_alert_status_warning(client):
    """Test warning level."""
    from cryodash.api.routes import _get_alert_status

    status = _get_alert_status("neo600", "N2", 15.0)
    assert status == "warning"


def test_alert_status_critical(client):
    """Test critical level."""
    from cryodash.api.routes import _get_alert_status

    status = _get_alert_status("neo600", "N2", 5.0)
    assert status == "critical"
