"""Configuration for CryoDash application."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "cryodash_data"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/cryodash.db")

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Database configuration
DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"

# Application configuration
APP_TITLE = "CryoDash"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Dashboard for monitoring cryogenic levels in NMR instruments"

# Alert thresholds (in percentage)
ALERT_THRESHOLDS = {
    "neo600": {
        "N2": {
            "warning": 25.0,  # Yellow alert below 25%
            "critical": 10.0,  # Red alert below 10%
        }
    },
    "neo700": {
        "N2": {
            "warning": 25.0,
            "critical": 10.0,
        },
        "He": {
            "warning": 20.0,
            "critical": 5.0,
        },
    },
}

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
