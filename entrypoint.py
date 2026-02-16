#!/usr/bin/env python3
"""
Entrypoint script for CryoDash.

Handles dynamic PORT assignment (Railway, etc.) without shell evaluation.
"""

import os
import sys


def main():
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
