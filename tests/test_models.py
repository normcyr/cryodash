"""Test cases for database models."""

from datetime import datetime

from cryodash.models import CryogenReading


def test_cryogen_reading_creation():
    """Test creating a CryogenReading instance."""
    reading = CryogenReading(
        device="Neo600",
        cryogen="N2",
        level=87.5,
        timestamp=datetime.now(),
    )
    assert reading.device == "Neo600"
    assert reading.cryogen == "N2"
    assert reading.level == 87.5
