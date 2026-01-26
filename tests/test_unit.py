"""Unit tests for models and schemas."""

from datetime import datetime, timezone

from cryodash.models import (
    CryogenReading,
    CryogenReadingSchema,
    Instrument,
    InstrumentSchema,
)


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

    def test_default_timestamp(self):
        """Test CryogenReading with explicit timestamp."""
        now = datetime.now(timezone.utc)
        reading = CryogenReading(
            device="neo600",
            cryogen="N2",
            level=87.5,
            timestamp=now,
        )
        assert reading.timestamp is not None
        assert reading.timestamp == now

    def test_various_levels(self):
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
        assert instrument.description == "Test"

    def test_optional_description(self):
        """Test instrument without description."""
        instrument = Instrument(
            name="neo700",
            frequency="700 MHz",
            cryogens="N2,He",
        )
        assert instrument.description is None
        assert instrument.cryogens == "N2,He"


class TestSchemas:
    """Test Pydantic schemas."""

    def test_cryogen_reading_schema(self):
        """Test CryogenReadingSchema."""
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
        assert schema.level == 87.5

    def test_instrument_schema(self):
        """Test InstrumentSchema."""
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
        assert schema.frequency == "600 MHz"


class TestAlertStatus:
    """Test alert status calculation."""

    def test_status_ok(self):
        """Test OK status."""
        from cryodash.api.routes import _get_alert_status

        # N2: normal 60-100%
        status = _get_alert_status("neo600", "N2", 80.0)
        assert status == "ok"

    def test_status_warning(self):
        """Test warning status."""
        from cryodash.api.routes import _get_alert_status

        # N2: warning 30-59%
        status = _get_alert_status("neo600", "N2", 45.0)
        assert status == "warning"

    def test_status_critical(self):
        """Test critical status."""
        from cryodash.api.routes import _get_alert_status

        # N2: critical 10-29%
        status = _get_alert_status("neo600", "N2", 15.0)
        assert status == "critical"

    def test_status_catastrophic(self):
        """Test catastrophic status."""
        from cryodash.api.routes import _get_alert_status

        # N2: catastrophic 0-9%
        status = _get_alert_status("neo600", "N2", 5.0)
        assert status == "catastrophic"

    def test_status_neo700_he(self):
        """Test Neo700 He thresholds."""
        from cryodash.api.routes import _get_alert_status

        # HE: normal 20-100%, warning 15-19%, critical 5-14%, catastrophic 0-4%
        assert _get_alert_status("neo700", "HE", 30.0) == "ok"
        assert _get_alert_status("neo700", "HE", 17.0) == "warning"
        assert _get_alert_status("neo700", "HE", 10.0) == "critical"
        assert _get_alert_status("neo700", "HE", 3.0) == "catastrophic"
