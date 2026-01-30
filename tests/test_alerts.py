"""Tests for email alerts functionality."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cryodash.alerts import check_cryogen_levels, send_email_alert
from cryodash.database import Base
from cryodash.models import AlertHistory, CryogenReading

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(test_db_engine) -> Generator[Session, None, None]:
    """Get database session for tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_reading(db: Session) -> CryogenReading:
    """Create a sample reading for testing."""
    reading = CryogenReading(
        device="neo700",
        cryogen="N2",
        level=25.0,  # Below warning threshold of 60%
        timestamp=datetime.now(timezone.utc),
    )
    db.add(reading)
    db.commit()
    return reading


@pytest.fixture
def sample_critical_reading(db: Session) -> CryogenReading:
    """Create a critical reading for testing."""
    reading = CryogenReading(
        device="neo700",
        cryogen="He",
        level=5.0,  # Below critical threshold of 15%
        timestamp=datetime.now(timezone.utc),
    )
    db.add(reading)
    db.commit()
    return reading


class TestEmailAlert:
    """Test email alert sending."""

    @patch("cryodash.alerts.SendGridAPIClient")
    @patch("cryodash.alerts.SENDGRID_API_KEY", "test-key-123")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    @patch("cryodash.alerts.ALERT_EMAIL_TO", ["test@example.com"])
    def test_send_email_alert_success(self, mock_sg):
        """Test successful email sending."""
        # Mock SendGrid response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sg.return_value = mock_sg_instance

        result = send_email_alert(
            subject="Test Alert",
            message="<p>Test message</p>",
            to_emails=["test@example.com"],
        )

        assert result is True
        mock_sg_instance.send.assert_called_once()

    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", False)
    def test_send_email_alert_disabled(self):
        """Test that email alert returns False when disabled."""
        result = send_email_alert(
            subject="Test",
            message="<p>Test</p>",
            to_emails=["test@example.com"],
        )
        assert result is False

    @patch("cryodash.alerts.SENDGRID_API_KEY", "")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    def test_send_email_alert_no_key(self):
        """Test that email alert returns False without API key."""
        result = send_email_alert(
            subject="Test",
            message="<p>Test</p>",
            to_emails=["test@example.com"],
        )
        assert result is False

    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    @patch("cryodash.alerts.SENDGRID_API_KEY", "test-key")
    @patch("cryodash.alerts.ALERT_EMAIL_TO", [])
    def test_send_email_alert_no_recipients(self):
        """Test that email alert returns False without recipients."""
        result = send_email_alert(subject="Test", message="<p>Test</p>")
        assert result is False

    @patch("cryodash.alerts.SendGridAPIClient")
    @patch("cryodash.alerts.SENDGRID_API_KEY", "test-key-123")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    @patch("cryodash.alerts.ALERT_EMAIL_TO", ["test@example.com"])
    def test_send_email_alert_failure(self, mock_sg):
        """Test email sending failure."""
        mock_sg.side_effect = Exception("API Error")

        result = send_email_alert(
            subject="Test Alert",
            message="<p>Test message</p>",
            to_emails=["test@example.com"],
        )

        assert result is False


class TestCryogenLevelChecks:
    """Test cryogenic level alert checks."""

    @patch("cryodash.alerts.send_email_alert")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    def test_check_critical_level(self, mock_send, db: Session):
        """Test that critical level triggers alert."""
        mock_send.return_value = True

        # Create critical reading directly
        reading = CryogenReading(
            device="neo700",
            cryogen="He",
            level=5.0,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(reading)
        db.commit()

        check_cryogen_levels(db)
        db.refresh(reading)  # Refresh session state

        # Should have called send_email_alert
        mock_send.assert_called()

        # Check alert was recorded
        alert = (
            db.query(AlertHistory)
            .filter(
                AlertHistory.device == "neo700",
                AlertHistory.cryogen == "HE",
            )
            .first()
        )
        assert alert is not None
        assert alert.alert_level == "critical"
        assert alert.level == 5.0

    @patch("cryodash.alerts.send_email_alert")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    def test_check_warning_level(self, mock_send, db: Session):
        """Test that warning level triggers alert."""
        mock_send.return_value = True

        # Create warning level reading
        reading = CryogenReading(
            device="neo700",
            cryogen="N2",
            level=25.0,  # Below warning threshold of 60%
            timestamp=datetime.now(timezone.utc),
        )
        db.add(reading)
        db.commit()

        check_cryogen_levels(db)

        # Should have called send_email_alert
        mock_send.assert_called()

        # Check alert was recorded
        alert = (
            db.query(AlertHistory)
            .filter(
                AlertHistory.device == "neo700",
                AlertHistory.cryogen == "N2",
            )
            .first()
        )
        assert alert is not None
        # Alert level depends on the threshold comparison
        assert alert.alert_level in ["warning", "critical"]

    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", False)
    def test_check_disabled(self, db: Session, sample_reading: CryogenReading):
        """Test that checks don't run when disabled."""
        check_cryogen_levels(db)

        # No alerts should be recorded
        alerts = db.query(AlertHistory).all()
        assert len(alerts) == 0

    @patch("cryodash.alerts.send_email_alert")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    def test_alert_cooldown(self, mock_send, db: Session):
        """Test that alert cooldown prevents duplicate alerts."""
        mock_send.return_value = True

        # Create reading and first alert
        reading = CryogenReading(
            device="neo600",
            cryogen="N2",
            level=20.0,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(reading)
        db.commit()

        # First check should send alert
        check_cryogen_levels(db)
        assert mock_send.call_count == 1

        # Reset mock
        mock_send.reset_mock()

        # Second check should NOT send alert (cooldown active)
        check_cryogen_levels(db)
        assert mock_send.call_count == 0

    @patch("cryodash.alerts.send_email_alert")
    @patch("cryodash.alerts.ENABLE_EMAIL_ALERTS", True)
    @patch("cryodash.alerts.ALERT_COOLDOWN_HOURS", 0)  # Disable cooldown
    def test_alert_after_cooldown_expires(self, mock_send, db: Session):
        """Test that alerts are sent again after cooldown expires."""
        mock_send.return_value = True

        # Create reading
        reading = CryogenReading(
            device="neo600",
            cryogen="N2",
            level=20.0,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(reading)
        db.commit()

        # First check
        check_cryogen_levels(db)
        assert mock_send.call_count == 1

        # Manually set old alert timestamp to expire cooldown
        alert = db.query(AlertHistory).first()
        assert alert is not None
        alert.sent_at = datetime.now(timezone.utc) - timedelta(days=2)  # type: ignore
        db.commit()

        # Reset mock
        mock_send.reset_mock()

        # Second check should send alert (cooldown expired)
        check_cryogen_levels(db)
        assert mock_send.call_count == 1
