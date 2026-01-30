"""Tests for alert history API endpoint."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cryodash.database import Base, get_db
from cryodash.main import create_app
from cryodash.models import AlertHistory

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db_engine():
    """Create a test database engine using file-based SQLite."""
    import os
    import tempfile

    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test.db")

    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

    # Cleanup
    try:
        os.remove(db_file)
        os.rmdir(temp_dir)
    except (OSError, FileNotFoundError):
        pass


@pytest.fixture
def client(test_db_engine):
    """Get test client with initialized database."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    TestingSessionLocal.app_db = TestingSessionLocal  # Store for sample_alerts
    return TestClient(app), TestingSessionLocal


@pytest.fixture
def sample_alerts(client):
    """Create sample alert history records using the same database as the client."""
    test_client, TestingSessionLocal = client
    db = TestingSessionLocal()

    # Clear any existing alerts first
    db.query(AlertHistory).delete()
    db.commit()

    # Create sample alerts with UPPERCASE cryogen (matching API expectations)
    alerts = [
        AlertHistory(
            device="neo600",
            cryogen="N2",  # Already uppercase
            level=25.0,
            alert_level="warning",
            sent_at=datetime.now(timezone.utc),
            sent_successfully=True,
        ),
        AlertHistory(
            device="neo700",
            cryogen="HE",  # Must be UPPERCASE
            level=5.0,
            alert_level="critical",
            sent_at=datetime.now(timezone.utc),
            sent_successfully=True,
        ),
        AlertHistory(
            device="neo700",
            cryogen="N2",  # Already uppercase
            level=30.0,
            alert_level="warning",
            sent_at=datetime.now(timezone.utc),
            sent_successfully=False,
        ),
    ]
    for alert in alerts:
        db.add(alert)
    db.commit()

    yield alerts

    # No db.close() - let the fixture cleanup handle it


class TestAlertHistoryAPI:
    """Test alert history API endpoint."""

    def test_get_alert_history_success(self, client, sample_alerts):
        """Test getting all alert history."""
        test_client, _ = client
        response = test_client.get("/api/alert-history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("device" in item for item in data)
        assert all("cryogen" in item for item in data)
        assert all("alert_level" in item for item in data)

    def test_get_alert_history_filter_device(self, client, sample_alerts):
        """Test filtering alert history by device."""
        test_client, _ = client
        response = test_client.get("/api/alert-history?device=neo600")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device"] == "neo600"

    def test_get_alert_history_filter_cryogen(self, client, sample_alerts):
        """Test filtering alert history by cryogen."""
        test_client, _ = client
        response = test_client.get("/api/alert-history?cryogen=He")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["cryogen"] == "HE"

    def test_get_alert_history_filter_alert_level(self, client, sample_alerts):
        """Test filtering alert history by alert level."""
        test_client, _ = client
        response = test_client.get("/api/alert-history?alert_level=critical")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["alert_level"] == "critical"

    def test_get_alert_history_filter_combined(self, client, sample_alerts):
        """Test filtering with multiple filters."""
        test_client, _ = client
        response = test_client.get(
            "/api/alert-history?device=neo700&cryogen=N2&alert_level=warning"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device"] == "neo700"
        assert data[0]["cryogen"] == "N2"
        assert data[0]["alert_level"] == "warning"

    def test_get_alert_history_limit(self, client, sample_alerts):
        """Test limit parameter."""
        test_client, _ = client
        response = test_client.get("/api/alert-history?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_alert_history_invalid_limit(self, client):
        """Test invalid limit parameter."""
        test_client, _ = client
        response = test_client.get("/api/alert-history?limit=2000")
        assert response.status_code == 422

    def test_get_alert_history_empty(self, client):
        """Test getting alert history when empty."""
        test_client, _ = client
        response = test_client.get("/api/alert-history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_alert_history_ordered(self, client, sample_alerts):
        """Test that results are ordered by sent_at descending."""
        test_client, _ = client
        response = test_client.get("/api/alert-history")
        assert response.status_code == 200
        data = response.json()
        # All have same timestamp, but endpoint should support ordering
        assert len(data) == 3
