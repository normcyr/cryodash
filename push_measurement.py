#!/usr/bin/env python
"""
Script to push latest N2 level from neo600 log file to CryoDash API.
Compatible with Python 2.7.5+ and Python 3.x

This script reads the most recent measurement from neo600_N2logcache.log
and sends it to the CryoDash push API endpoint.

To use with cron, add to crontab:
    */5 * * * * /path/to/push_measurement.py

"""

import json
import re
import sys
from datetime import datetime, timedelta
from typing import Any

# Configuration
API_ENDPOINT = "API_ENDPOINT"  # e.g., "http://localhost:8000/api/data"
API_KEY = "YOUR_API_KEY"  # Replace with actual key from .env
DEVICE = "neo600"
LOCATION = "magnet_room"
LOG_FILE = "/path/to/neo600_N2logcache.log"  # Update this path

# Import appropriate HTTP library (works with both Python 2 and 3)
urllib_request: Any
urllib_error: Any

try:
    import urllib.error as urllib_error  # type: ignore
    import urllib.request as urllib_request  # type: ignore
except ImportError:
    # Python 2
    import urllib2 as urllib_request  # type: ignore

    urllib_error = urllib_request  # type: ignore

# Detect Python version
PYTHON_VERSION = sys.version_info[0]


def parse_iso_timestamp_with_tz(timestamp_str):
    """
    Parse ISO timestamp with timezone offset.

    Example: "2026-02-17T08:09:00.000-0500"
    Returns: datetime in UTC
    """
    # Parse timezone offset from end of string (e.g., "-0500" or "+0530")
    tz_pattern = r"([+-])(\d{2})(\d{2})$"
    tz_match = re.search(tz_pattern, timestamp_str)

    if not tz_match:
        # No timezone info, try to parse as is
        try:
            return datetime.strptime(timestamp_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None

    # Extract timezone offset
    tz_sign = tz_match.group(1)
    tz_hours = int(tz_match.group(2))
    tz_minutes = int(tz_match.group(3))

    # Remove timezone from string and parse datetime
    timestamp_no_tz = timestamp_str[: tz_match.start()]

    try:
        # Handle milliseconds if present
        if "." in timestamp_no_tz:
            dt = datetime.strptime(timestamp_no_tz, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt = datetime.strptime(timestamp_no_tz, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None

    # Calculate UTC offset
    if tz_sign == "-":
        offset = timedelta(hours=tz_hours, minutes=tz_minutes)
    else:
        offset = -timedelta(hours=tz_hours, minutes=tz_minutes)

    # Convert to UTC
    dt_utc = dt + offset

    return dt_utc


def timestamp_to_iso_utc(dt):
    """Convert datetime to ISO format with Z suffix."""
    iso_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    return iso_str + "Z"


def read_latest_measurement(log_path):
    """
    Read the latest timestamp and nitrogen level from log file.

    Returns:
        Tuple of (timestamp_iso_utc, level_value) or None if error
    """
    try:
        with open(log_path) as f:
            lines = f.readlines()
    except OSError as e:
        print(f"Error: Cannot read file: {e}")
        return None

    if not lines:
        print(f"Error: Log file is empty: {log_path}")
        return None

    # Reverse iterate to find last data line
    for line in reversed(lines):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Parse: "2026-02-17T08:09:00.000-0500;95.7"
        parts = line.split(";")
        if len(parts) != 2:
            print(f"Warning: Invalid line format: {line}")
            continue

        timestamp_str = parts[0].strip()
        level_str = parts[1].strip()

        try:
            level = float(level_str)
        except ValueError:
            print(f"Warning: Invalid level value: {level_str}")
            continue

        # Parse timestamp with timezone conversion
        dt_utc = parse_iso_timestamp_with_tz(timestamp_str)

        if dt_utc is None:
            print(f"Warning: Cannot parse timestamp: {timestamp_str}")
            continue

        timestamp_iso = timestamp_to_iso_utc(dt_utc)
        return timestamp_iso, level

    print(f"Error: No valid data lines found in {log_path}")
    return None


def push_measurement(timestamp, level):
    """
    Send measurement to CryoDash API.

    Returns:
        True if successful, False otherwise
    """
    payload = {
        "device": DEVICE,
        "location": LOCATION,
        "timestamp": timestamp,
        "readings": [{"type": "cryogen_level", "cryogen": "N2", "value": level, "unit": "%"}],
    }

    try:
        # Use appropriate method for current Python version
        if PYTHON_VERSION >= 3:
            import urllib.request

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                API_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
            )

            try:
                response = urllib.request.urlopen(req, timeout=15)  # nosec - URL hardcoded, safe
                status_code = response.getcode()
                response_text = response.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                status_code = e.code
                response_text = e.read().decode("utf-8")
        else:
            # Python 2
            import urllib2

            data = json.dumps(payload)
            req = urllib2.Request(
                API_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
            )

            try:
                response = urllib2.urlopen(req, timeout=15)  # nosec - URL hardcoded, safe
                status_code = response.getcode()
                response_text = response.read()
            except urllib2.HTTPError as e:
                status_code = e.code
                response_text = e.read()

        if status_code == 200:
            print(f"SUCCESS: N2 level {level}% sent at {timestamp}")
            return True
        elif status_code == 401:
            print("AUTH ERROR (401): Check your API_KEY")
            print(f"  Response: {response_text}")
            return False
        else:
            print(f"ERROR {status_code}: {response_text}")
            return False

    except Exception as e:
        print(f"REQUEST FAILED: {e}")
        return False


def main():
    """Main execution."""
    print(f"CryoDash Push Measurement (Python {PYTHON_VERSION})")

    # Validate configuration
    if API_KEY == "YOUR_API_KEY":
        print("Error: API_KEY not configured.")
        print("Update the API_KEY variable in this script with your actual API key.")
        sys.exit(1)

    if LOG_FILE == "/path/to/neo600_N2logcache.log":
        print("Error: LOG_FILE path not configured.")
        print("Update the LOG_FILE variable in this script with the actual path.")
        sys.exit(1)

    # Read latest measurement
    result = read_latest_measurement(LOG_FILE)
    if result is None:
        sys.exit(1)

    timestamp, level = result

    # Push to server
    success = push_measurement(timestamp, level)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
