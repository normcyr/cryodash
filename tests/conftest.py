"""Pytest configuration and shared fixtures."""

import os
import sys

# Disable API key requirement for tests BEFORE importing the app
os.environ["REQUIRE_API_KEY"] = "false"
os.environ["ENABLE_EMAIL_ALERTS"] = "false"  # Disable email alerts in tests

# Force reimport of config modules if they were already loaded
if "cryodash.config" in sys.modules:
    del sys.modules["cryodash.config"]
if "cryodash.security" in sys.modules:
    del sys.modules["cryodash.security"]
if "cryodash.main" in sys.modules:
    del sys.modules["cryodash.main"]

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from cryodash.database import Base, get_db  # noqa: E402
from cryodash.main import app  # noqa: E402

# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """Create a FastAPI test client with test database."""
    # TestClient uses http://testserver by default, but CORS is configured
    # to allow localhost. Use appropriate headers or disable CORS checks for tests.
    return TestClient(app)
