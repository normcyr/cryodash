"""Test cases for API routes."""

import pytest
from fastapi.testclient import TestClient

from cryodash.main import app


@pytest.fixture
def client():
    """Create a test client."""
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
    assert "status" in data
    assert data["status"] == "ok"
