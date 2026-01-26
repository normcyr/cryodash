"""Test cases for database models and schemas."""

from datetime import datetime

from cryodash.models import (
    CryogenReading,
    CryogenReadingSchema,
    EvaporationRateSchema,
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

    def test_evaporation_rate_schema_basic(self):
        """Test EvaporationRateSchema basic."""
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
        assert schema.rate_percent_per_day == -2.5
        assert schema.refill_detected is False

    def test_evaporation_rate_schema_with_refill(self):
        """Test EvaporationRateSchema with refill."""
        now = datetime.now()
        data = {
            "device": "neo700",
            "cryogen": "HE",
            "rate_percent_per_day": -1.8,
            "last_24h_change": -2.0,
            "hours_calculated": 120.0,
            "latest_level": 85.0,
            "oldest_level": 87.0,
            "latest_timestamp": now,
            "oldest_timestamp": now,
            "refill_detected": True,
            "last_refill_timestamp": now,
        }
        schema = EvaporationRateSchema(**data)
        assert schema.refill_detected is True
        assert schema.last_refill_timestamp is not None
