"""Script to import cryogenic level data from log files into the database."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from cryodash.database import SessionLocal, init_db
from cryodash.models import CryogenReading, Instrument


def parse_iso_datetime(datetime_str: str) -> datetime:
    """
    Parse ISO 8601 datetime string from log files.
    Format: 2017-11-22T17:26:00.000-0500
    """
    # Remove the timezone part for parsing
    if "+" in datetime_str:
        dt_part = datetime_str.split("+")[0]
    elif "-" in datetime_str:
        # Find the last occurrence of '-' which is the timezone
        parts = datetime_str.rsplit("-", 1)
        dt_part = parts[0]
    else:
        dt_part = datetime_str

    # Parse the datetime part
    return datetime.fromisoformat(dt_part)


def parse_log_file(file_path: Path, device: str, cryogen: str) -> list:
    """
    Parse a cryogenic log file.

    Expected format:
    # timestamp ; nitrogen level [%]
    2017-11-22T17:26:00.000-0500;86.6
    """
    readings = []

    try:
        with open(file_path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                try:
                    # Split by semicolon
                    parts = line.split(";")
                    if len(parts) != 2:
                        print(f"Warning: Line {line_num} has unexpected format: {line}")
                        continue

                    timestamp_str, level_str = parts
                    timestamp_str = timestamp_str.strip()
                    level_str = level_str.strip()

                    # Parse timestamp
                    timestamp = parse_iso_datetime(timestamp_str)

                    # Parse level
                    level = float(level_str)

                    # Clamp level to 0-100 range (handle sensor errors)
                    if level < 0:
                        level = 0
                    elif level > 100:
                        level = 100

                    readings.append(
                        {
                            "device": device.lower(),
                            "cryogen": cryogen.upper(),
                            "level": level,
                            "timestamp": timestamp,
                        }
                    )

                except (ValueError, IndexError) as e:
                    print(f"Warning: Error parsing line {line_num}: {line}")
                    print(f"  Error: {e}")
                    continue

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

    return readings


def ensure_instrument_exists(db: Session, device: str, readings: list) -> None:
    """Ensure the instrument exists in the database."""
    existing = db.query(Instrument).filter(Instrument.name == device).first()

    if existing:
        return

    # Determine instrument config based on device name
    config = {
        "neo600": {
            "frequency": "600 MHz",
            "description": "Imageur 600 MHz",
            "cryogens": "N2",
        },
        "neo700": {
            "frequency": "700 MHz",
            "description": "Imageur 700 MHz",
            "cryogens": "N2,He",
        },
    }

    # Get the first cryogen from readings if available
    cryogens_in_file = set(r["cryogen"] for r in readings)
    cryogens_str = ",".join(sorted(cryogens_in_file)) if cryogens_in_file else "N2"

    device_config = config.get(device, {})

    instrument = Instrument(
        name=device,
        frequency=device_config.get("frequency", "Unknown MHz"),
        description=device_config.get("description", f"NMR Instrument {device}"),
        cryogens=cryogens_str,
    )

    db.add(instrument)
    db.commit()
    print(f"Created instrument: {device} with cryogens: {cryogens_str}")


def import_readings(db: Session, readings: list) -> int:
    """Import readings into the database."""
    if not readings:
        print("No readings to import")
        return 0

    # Check for duplicates
    existing_count = 0
    imported_count = 0

    for reading_data in readings:
        # Check if this reading already exists
        existing = (
            db.query(CryogenReading)
            .filter(
                CryogenReading.device == reading_data["device"],
                CryogenReading.cryogen == reading_data["cryogen"],
                CryogenReading.timestamp == reading_data["timestamp"],
            )
            .first()
        )

        if existing:
            existing_count += 1
            continue

        # Create new reading
        reading = CryogenReading(
            device=reading_data["device"],
            cryogen=reading_data["cryogen"],
            level=reading_data["level"],
            timestamp=reading_data["timestamp"],
        )
        db.add(reading)
        imported_count += 1

    db.commit()

    if existing_count > 0:
        print(f"  Skipped {existing_count} duplicate readings")

    return imported_count


def main():
    """Main entry point for the import script."""
    parser = argparse.ArgumentParser(
        description="Import cryogenic level data from log files into the database"
    )
    parser.add_argument(
        "--device",
        required=True,
        choices=["neo600", "neo700"],
        help="Device name (neo600 or neo700)",
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        help="Path to the log file",
    )
    parser.add_argument(
        "--cryogen",
        default="N2",
        choices=["N2", "He"],
        help="Cryogen type (N2 or He, default: N2)",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables before import",
    )

    args = parser.parse_args()

    # Initialize database if requested
    if args.init_db:
        print("Initializing database...")
        init_db()
        print("Database initialized")

    # Check file exists
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Parse log file
    print(f"Parsing log file: {args.file}")
    readings = parse_log_file(args.file, args.device, args.cryogen)
    print(f"  Found {len(readings)} readings")

    if not readings:
        print("No readings found in file")
        sys.exit(0)

    # Import into database
    db = SessionLocal()
    try:
        # Ensure instrument exists
        ensure_instrument_exists(db, args.device, readings)

        # Import readings
        print("Importing readings into database...")
        imported = import_readings(db, readings)
        print(f"  Imported {imported} new readings")
        print("Import complete!")

    except Exception as e:
        db.rollback()
        print(f"Error during import: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
