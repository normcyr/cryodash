"""Test cases for API routes - Basic integration tests."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from cryodash.main import app


@pytest.fixture
def client(test_db):
    """Create a test client with test database."""
    return TestClient(app)


def test_get_instruments(client):
    """Test GET /api/instruments endpoint."""
    response = client.get("/api/instruments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_check(client):
    """Test GET /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_create_instrument(client):
    """Test POST /api/instruments."""
    instrument_data = {
        "name": "test-instrument",
        "frequency": "600 MHz",
        "description": "Test instrument",
        "cryogens": "N2",
    }
    response = client.post("/api/instruments", json=instrument_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-instrument"


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


def test_sync_status(client):
    """Test GET /api/sync-status."""
    response = client.get("/api/sync-status")
    assert response.status_code == 200
    assert "status" in response.json()


def test_sync_history(client):
    """Test GET /api/sync-history."""
    response = client.get("/api/sync-history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_stats(client):
    """Test GET /api/stats."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_readings" in data
    assert "total_instruments" in data


def test_evaporation_rate(client):
    """Test GET /api/evaporation-rate."""
    response = client.get("/api/evaporation-rate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
