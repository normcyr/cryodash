"""Configuration for CryoDash application."""

import os
from pathlib import Path

# Project paths - use /app/data in Docker, local cryodash_data otherwise
if os.getenv("DOCKER_ENV", "false").lower() == "true" or os.path.exists("/.dockerenv"):
    DATA_DIR = Path("/app/data")
else:
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "cryodash_data"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/cryodash.db")

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Database configuration
DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"

# Security configuration
API_KEY = os.getenv("API_KEY", "default-dev-key-change-in-production")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"

# CORS configuration - restrict to specific origins
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://testserver",
).split(",")

# Email alerts configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "alerts@cryodash.local")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "").split(",") if os.getenv("ALERT_EMAIL_TO") else []
ALERT_COOLDOWN_HOURS = int(
    os.getenv("ALERT_COOLDOWN_HOURS", 24)
)  # Avoid duplicate alerts within 24h
ENABLE_EMAIL_ALERTS = os.getenv("ENABLE_EMAIL_ALERTS", "false").lower() == "true"

# Application configuration
APP_TITLE = "CryoDash"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Dashboard for monitoring cryogenic levels in NMR instruments"

# Alert thresholds (in percentage)
ALERT_THRESHOLDS = {
    "neo600": {
        "N2": {
            "catastrophic": 10.0,  # Red alert below 10%
            "critical": 30.0,  # Orange alert below 30%
            "warning": 60.0,  # Yellow alert below 60%
        }
    },
    "neo700": {
        "N2": {
            "catastrophic": 10.0,
            "critical": 30.0,
            "warning": 60.0,
        },
        "HE": {
            "catastrophic": 5.0,
            "critical": 15.0,
            "warning": 20.0,
        },
    },
}

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
