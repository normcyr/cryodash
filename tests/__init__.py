"""Test configuration for CryoDash."""

import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def test_db():
    """Create a test database."""
    from cryodash.database import Base, SessionLocal, engine

    # Create test tables
    Base.metadata.create_all(bind=engine)
    yield SessionLocal()
    # Cleanup
    Base.metadata.drop_all(bind=engine)
