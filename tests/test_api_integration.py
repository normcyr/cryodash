"""Integration tests for API endpoints with database."""

from datetime import datetime, timedelta


def test_get_instruments_empty(client, test_db):
    """Test GET /api/instruments when empty."""
    response = client.get("/api/instruments")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_instrument(client, test_db):
    """Test creating and retrieving instrument."""
    # Create
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "description": "600 MHz NMR",
        "cryogens": "N2",
    }
    response = client.post("/api/instruments", json=instrument_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "neo600"

    # Get all
    response = client.get("/api/instruments")
    assert response.status_code == 200
    instruments = response.json()
    assert len(instruments) == 1
    assert instruments[0]["name"] == "neo600"


def test_get_instrument_detail(client, test_db):
    """Test getting detailed instrument info."""
    # Create instrument through API
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "description": "Test",
        "cryogens": "N2",
    }
    create_resp = client.post("/api/instruments", json=instrument_data)
    assert create_resp.status_code == 200

    response = client.get("/api/instruments/neo600")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "neo600"


def test_get_instrument_not_found(client, test_db):
    """Test getting non-existent instrument."""
    response = client.get("/api/instruments/nonexistent")
    assert response.status_code == 404


def test_create_reading(client, test_db):
    """Test creating a reading."""
    reading_data = {
        "device": "neo600",
        "cryogen": "N2",
        "level": 85.5,
        "timestamp": datetime.now().isoformat(),
    }
    response = client.post("/api/readings", json=reading_data)
    assert response.status_code == 200
    data = response.json()
    assert data["device"] == "neo600"
    assert data["level"] == 85.5


def test_get_history(client, test_db):
    """Test getting reading history."""
    # Create instrument first
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
    }
    client.post("/api/instruments", json=instrument_data)

    # Add readings via API
    base_time = datetime.now() - timedelta(hours=24)
    for i in range(10):
        reading_data = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 90.0 - (i * 0.5),
            "timestamp": (base_time + timedelta(hours=i * 2)).isoformat(),
        }
        client.post("/api/readings", json=reading_data)

    response = client.get("/api/instruments/neo600/history?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all("level" in item for item in data)


def test_get_current_levels(client, test_db):
    """Test getting current cryogenic levels."""
    # Create instrument first
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
    }
    client.post("/api/instruments", json=instrument_data)

    # Add readings
    reading = {
        "device": "neo600",
        "cryogen": "N2",
        "level": 87.5,
    }
    client.post("/api/readings", json=reading)

    response = client.get("/api/instruments/neo600/current")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["level"] == 87.5


def test_get_stats(client, test_db):
    """Test GET /api/stats."""
    # Create instrument via API
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
    }
    client.post("/api/instruments", json=instrument_data)

    # Add readings
    for i in range(5):
        reading = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 90.0 - i,
        }
        client.post("/api/readings", json=reading)

    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_readings"] == 5
    assert data["total_instruments"] == 1


def test_get_evaporation_rate(client, test_db):
    """Test GET /api/evaporation-rate."""
    # Create instrument first
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
    }
    client.post("/api/instruments", json=instrument_data)

    # Add readings with gradual decrease (evaporation)
    base_time = datetime.now() - timedelta(hours=24)
    for i in range(24):
        reading = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 90.0 - (i * 0.5),  # Lose 0.5% per hour = 12% per day
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
        }
        client.post("/api/readings", json=reading)

    response = client.get("/api/evaporation-rate?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "rate_percent_per_day" in data[0]
    # Should show negative rate (evaporation)
    assert data[0]["rate_percent_per_day"] < 0


def test_evaporation_rate_with_refill(client, test_db):
    """Test evaporation rate with refill detection."""
    # Create instrument
    instrument_data = {
        "name": "neo600",
        "frequency": "600 MHz",
        "cryogens": "N2",
    }
    client.post("/api/instruments", json=instrument_data)

    base_time = datetime.now() - timedelta(hours=24)

    # Gradual decrease
    for i in range(20):
        reading = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 90.0 - (i * 0.5),
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
        }
        client.post("/api/readings", json=reading)

    # Refill event (jump from ~80 to 95)
    refill_reading = {
        "device": "neo600",
        "cryogen": "N2",
        "level": 95.0,
        "timestamp": (base_time + timedelta(hours=20)).isoformat(),
    }
    client.post("/api/readings", json=refill_reading)

    # Continue after refill
    for i in range(4):
        reading = {
            "device": "neo600",
            "cryogen": "N2",
            "level": 95.0 - (i * 0.5),
            "timestamp": (base_time + timedelta(hours=21 + i)).isoformat(),
        }
        client.post("/api/readings", json=reading)

    response = client.get("/api/evaporation-rate?hours=24&device=neo600")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # Should detect refill
    assert data[0]["refill_detected"] is True
    assert data[0]["last_refill_timestamp"] is not None


def test_sync_status(client, test_db):
    """Test GET /api/sync-status."""
    response = client.get("/api/sync-status")
    assert response.status_code == 200
    assert "status" in response.json()


def test_get_sync_history(client, test_db):
    """Test GET /api/sync-history."""
    response = client.get("/api/sync-history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_check(client):
    """Test GET /api/health."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
