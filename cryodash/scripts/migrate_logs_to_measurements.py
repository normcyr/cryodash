"""Script to migrate historical log data to Measurement table."""

import json
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from cryodash.database import SessionLocal
from cryodash.models import Measurement
from cryodash.scripts.import_logs import parse_log_file

logger = logging.getLogger(__name__)

# Log files configuration
LOG_FILES = [
    {"filename": "neo600_N2logcache.log", "device": "neo600", "cryogen": "N2"},
    {"filename": "neo700_N2logcache.log", "device": "neo700", "cryogen": "N2"},
    {"filename": "neo700_Helogcache.log", "device": "neo700", "cryogen": "He"},
]


def migrate_logs_to_measurements(db: Session, log_dir: Optional[Path] = None) -> dict:
    """
    Migrate historical cryogenic log data to Measurement table.

    Converts legacy CryogenReading schema to new Measurement schema with flexible format.

    Args:
        db: Database session
        log_dir: Directory containing log files (defaults to temp_logs/)

    Returns:
        Migration statistics dictionary
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "temp_logs"

    stats = {
        "total_records": 0,
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "files_processed": 0,
    }

    # Process each log file
    for log_file_config in LOG_FILES:
        try:
            filename = log_file_config["filename"]
            device = log_file_config["device"]
            cryogen = log_file_config["cryogen"]

            log_path = log_dir / filename

            if not log_path.exists():
                logger.warning(f"Log file not found: {log_path}")
                continue

            logger.info(f"Processing {filename}...")

            # Parse the log file
            readings = parse_log_file(log_path, device, cryogen)
            stats["total_records"] += len(readings)

            # Convert to Measurement records
            for reading in readings:
                try:
                    # Check if this measurement already exists (prevent duplicates)
                    existing = (
                        db.query(Measurement)
                        .filter(
                            Measurement.device == reading["device"],
                            Measurement.measurement_type == "cryogen_level",
                            Measurement.timestamp == reading["timestamp"],
                        )
                        .first()
                    )

                    if existing:
                        stats["skipped"] += 1
                        continue

                    # Create metadata with cryogen info
                    metadata = {"cryogen": reading["cryogen"]}
                    metadata_json = json.dumps(metadata)

                    # Create Measurement record
                    measurement = Measurement(
                        device=reading["device"],
                        location=None,  # Legacy logs don't have location info
                        measurement_type="cryogen_level",
                        value=reading["level"],
                        unit="%",
                        timestamp=reading["timestamp"],
                        data=metadata_json,
                    )

                    db.add(measurement)
                    stats["imported"] += 1

                except Exception as e:
                    logger.error(f"Error importing reading {reading}: {e}")
                    stats["errors"] += 1
                    continue

            stats["files_processed"] += 1
            db.commit()
            logger.info(f"Completed {filename}: {len(readings)} readings processed")

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            stats["errors"] += 1
            db.rollback()
            continue

    logger.info(f"Migration complete: {stats}")
    return stats


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run migration
    db = SessionLocal()
    try:
        stats = migrate_logs_to_measurements(db)
        print("\nMigration Statistics:")
        print(f"  Total records read: {stats['total_records']}")
        print(f"  Successfully imported: {stats['imported']}")
        print(f"  Skipped (duplicates): {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Files processed: {stats['files_processed']}")
    finally:
        db.close()
