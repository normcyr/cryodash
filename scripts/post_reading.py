#!/usr/bin/env python3
"""
Example script for instruments to POST cryogenic readings to CryoDash.

This script demonstrates how to:
1. Read current cryogenic levels from the instrument
2. POST readings to CryoDash API
3. Handle errors and retries
4. Log the submissions

Usage:
    python post_reading.py --device neo600 --cryogen N2 --level 87.5

Or as a cron job:
    */10 * * * * /usr/bin/python3 /app/post_reading.py --device neo600 --cryogen N2 --level <read_from_instrument>
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def post_reading(
    device: str,
    cryogen: str,
    level: float,
    cryodash_url: str = "http://localhost:8000",
    max_retries: int = 3,
    timeout: int = 5,
) -> bool:
    """
    POST a cryogenic reading to CryoDash.

    Args:
        device: Instrument name (e.g., "neo600")
        cryogen: Cryogen type ("N2" or "He")
        level: Current level percentage (0-100)
        cryodash_url: CryoDash server URL
        max_retries: Number of retries on failure
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    endpoint = f"{cryodash_url}/api/readings"

    payload = {
        "device": device,
        "cryogen": cryogen,
        "level": level,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Attempt {attempt}/{max_retries}: POST {endpoint}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                endpoint,
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )

            # Check if successful
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✓ Reading posted successfully: {device}/{cryogen} = {level}% "
                    f"(ID: {result['id']})"
                )
                return True

            # Handle errors
            elif response.status_code == 404:
                logger.error(
                    f"✗ Instrument '{device}' not found in CryoDash. "
                    f"Check instrument configuration."
                )
                return False

            elif response.status_code == 400:
                error = response.json()
                logger.error(
                    f"✗ Invalid request: {error.get('detail', 'Unknown error')}. "
                    f"Check device and cryogen values."
                )
                return False

            else:
                logger.warning(f"✗ HTTP {response.status_code}: {response.text}. Will retry...")

        except requests.exceptions.Timeout:
            logger.warning(
                f"✗ Request timeout ({timeout}s). Attempt {attempt}/{max_retries}. Will retry..."
            )

        except requests.exceptions.ConnectionError as e:
            logger.warning(
                f"✗ Connection failed: {e}. Attempt {attempt}/{max_retries}. Will retry..."
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Request failed: {e}")
            return False

    logger.error(f"✗ Failed to post reading after {max_retries} attempts")
    return False


def read_level_from_instrument(device: str, cryogen: str) -> Optional[float]:
    """
    Read the current level from the physical instrument.

    This is a placeholder - replace with actual instrument communication.

    Args:
        device: Instrument name
        cryogen: Cryogen type

    Returns:
        Current level percentage, or None if read fails
    """
    # Example: This would connect to your actual instrument interface
    # For now, this is just a placeholder that you'd customize
    logger.warning(
        f"Using placeholder level reading. "
        f"Implement read_level_from_instrument() for {device}/{cryogen}"
    )

    # Replace this with actual instrument communication
    # Example for Bruker NMR:
    #   return read_bruker_cryogen_level(device, cryogen)
    # Example for JEOL NMR:
    #   return read_jeol_cryogen_level(device, cryogen)

    return None  # Return None if unable to read


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="POST cryogenic readings to CryoDash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Post a single reading
  python post_reading.py --device neo600 --cryogen N2 --level 87.5

  # Post with custom CryoDash URL
  python post_reading.py --device neo600 --cryogen N2 --level 87.5 \\
    --url http://cryodash.example.com:8000

  # Use as cron job (read from instrument)
  */10 * * * * /usr/bin/python3 /app/post_reading.py --device neo600 --cryogen N2
        """,
    )

    parser.add_argument(
        "--device",
        required=True,
        help='Instrument name (e.g., "neo600", "neo700")',
    )
    parser.add_argument(
        "--cryogen",
        required=True,
        help='Cryogen type ("N2" or "He")',
    )
    parser.add_argument(
        "--level",
        type=float,
        help="Current level percentage (0-100). If omitted, will try to read from instrument.",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="CryoDash server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retries on failure (default: 3)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    # Get level
    level = args.level
    if level is None:
        logger.info(f"Level not provided, attempting to read from {args.device}...")
        level = read_level_from_instrument(args.device, args.cryogen)

        if level is None:
            logger.error(
                "Could not read level from instrument. "
                "Provide --level argument or implement read_level_from_instrument()."
            )
            sys.exit(1)

    # Validate level
    if not 0 <= level <= 100:
        logger.error(f"Invalid level: {level}%. Must be between 0 and 100.")
        sys.exit(1)

    # Post reading
    success = post_reading(
        device=args.device,
        cryogen=args.cryogen,
        level=level,
        cryodash_url=args.url,
        max_retries=args.retries,
        timeout=args.timeout,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
