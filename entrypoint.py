#!/usr/bin/env python3
"""
Entrypoint script for CryoDash.

Handles dynamic PORT assignment (Railway, etc.) without shell evaluation.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_temp_logs():
    """Remove temp logs older than 7 days to prevent disk space issues."""
    temp_logs_dir = Path("/app/data/temp_logs")

    if not temp_logs_dir.exists():
        return

    cutoff_time = datetime.now() - timedelta(days=7)

    try:
        for log_file in temp_logs_dir.glob("*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_time:
                log_file.unlink()
                print(f"Cleaned up old temp log: {log_file.name}")
    except Exception as e:
        print(f"Warning: Could not cleanup temp logs: {e}")


def main():
    # Cleanup old temp logs on startup
    cleanup_old_temp_logs()

    # Get PORT from environment, default to 8000
    port = os.getenv("PORT", "8000")

    print(f"Starting CryoDash on port {port}...")

    # Build and execute uvicorn command
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "cryodash.main:create_app",
        "--host",
        "0.0.0.0",  # nosec B104 - intentional: Docker/Railway need to bind all interfaces
        "--port",
        port,
        "--factory",
    ]

    # Replace current process with uvicorn
    os.execvp(cmd[0], cmd)  # nosec B606 - intentional: exec without shell is best practice


if __name__ == "__main__":
    main()
