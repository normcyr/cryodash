"""Test configuration for CryoDash."""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def test_db():
    """Create a test database."""
    from cryodash.database import Base, engine, SessionLocal

    # Create test tables
    Base.metadata.create_all(bind=engine)
    yield SessionLocal()
    # Cleanup
    Base.metadata.drop_all(bind=engine)
