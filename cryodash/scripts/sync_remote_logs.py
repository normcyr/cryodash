"""Script to sync cryogenic log files from remote HTTP server."""

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from sqlalchemy.orm import Session

from cryodash.database import SessionLocal, init_db
from cryodash.models import SyncHistory
from cryodash.scripts.import_logs import ensure_instrument_exists, import_readings, parse_log_file

logger = logging.getLogger(__name__)

# Timezone for Eastern Time
EASTERN = ZoneInfo("America/Toronto")


def get_local_time():
    """Get current time in Eastern timezone."""
    return datetime.now(EASTERN)


# Remote server URL
REMOTE_LOG_URL = "http://airen.bcm.umontreal.ca/biostruct/logs/"

# Log files to download and their metadata
LOG_FILES = [
    {"filename": "neo600_N2logcache.log", "device": "neo600", "cryogen": "N2"},
    {"filename": "neo700_N2logcache.log", "device": "neo700", "cryogen": "N2"},
    {"filename": "neo700_Helogcache.log", "device": "neo700", "cryogen": "He"},
]


def download_log_file(filename: str, local_path: Path) -> bool:
    """Download a log file from remote server."""
    url = f"{REMOTE_LOG_URL}{filename}"
    logger.debug(f"Attempting to download {filename} from {url}")
    try:
        logger.debug(f"Sending request to {url} with 30s timeout")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(local_path, "w") as f:
            f.write(response.text)

        logger.debug(f"File saved to {local_path} ({len(response.text)} bytes)")
        logger.info(f"Downloaded {filename} from {url}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to download {filename}: {e}", exc_info=True)
        logger.debug(f"Download error type: {type(e).__name__}")
        return False


def sync_logs(db: Session | None = None) -> dict:
    """
    Download and import all log files from remote server.

    Returns:
        dict: Summary of import results with counts
    """
    logger.debug("sync_logs() called")
    start_time = get_local_time()
    logger.debug(f"Sync started at {start_time}")

    # Initialize database if needed
    if db is None:
        logger.debug("No database session provided, initializing...")
        init_db()
        db = SessionLocal()
        logger.debug("Database session created")

    # Create temp directory for log files
    temp_dir = Path(__file__).parent.parent.parent / "temp_logs"
    logger.debug(f"Using temp directory: {temp_dir}")
    temp_dir.mkdir(exist_ok=True)
    logger.debug("Temp directory ready")

    results = {
        "timestamp": start_time.isoformat(),
        "total_imported": 0,
        "files_processed": 0,
        "files_failed": 0,
        "details": [],
    }

    try:
        for log_config in LOG_FILES:
            filename = log_config["filename"]
            device = log_config["device"]
            cryogen = log_config["cryogen"]

            local_path = temp_dir / filename
            logger.debug(f"Processing {filename} ({device}/{cryogen})")

            # Download the file
            if not download_log_file(filename, local_path):
                logger.debug(f"Skipping {filename} due to download failure")
                results["files_failed"] += 1
                results["details"].append({"file": filename, "status": "download_failed"})
                continue

            # Parse and import
            try:
                logger.debug(f"Parsing {filename}...")
                readings = parse_log_file(local_path, device, cryogen)
                logger.debug(f"Parsed {len(readings)} readings from {filename}")

                if not readings:
                    logger.warning(f"No readings found in {filename}")
                    results["details"].append(
                        {"file": filename, "status": "no_readings", "count": 0}
                    )
                    results["files_processed"] += 1
                    continue

                # Ensure instrument exists
                logger.debug(f"Ensuring instrument {device} exists in DB")
                ensure_instrument_exists(db, device, readings)
                logger.debug(f"Instrument {device} ready")

                # Import readings
                logger.debug(f"Importing {len(readings)} readings...")
                imported_count = import_readings(db, readings)
                logger.debug(f"Successfully imported {imported_count} readings")

                results["total_imported"] += imported_count
                results["files_processed"] += 1
                results["details"].append(
                    {
                        "file": filename,
                        "status": "success",
                        "count": imported_count,
                        "total_in_file": len(readings),
                    }
                )

                logger.info(f"Imported {imported_count} readings from {filename}")

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                results["files_failed"] += 1
                results["details"].append(
                    {"file": filename, "status": "processing_failed", "error": str(e)}
                )

        # Record sync in database
        sync_record = SyncHistory(
            started_at=start_time,
            completed_at=get_local_time(),
            status=(
                "success"
                if results["files_failed"] == 0
                else "partial"
                if results["files_processed"] > 0
                else "failed"
            ),
            total_imported=results["total_imported"],
            files_processed=results["files_processed"],
            files_failed=results["files_failed"],
            details=json.dumps(results["details"]),
        )
        db.add(sync_record)
        db.commit()

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sync_record = SyncHistory(
            started_at=start_time,
            completed_at=get_local_time(),
            status="failed",
            total_imported=results.get("total_imported", 0),
            files_processed=results.get("files_processed", 0),
            files_failed=results.get("files_failed", 0),
            error_message=str(e),
            details=json.dumps(results.get("details", [])),
        )
        db.add(sync_record)
        db.commit()
        raise

    finally:
        db.close()

    logger.info(
        f"Sync complete: {results['total_imported']} readings imported from {results['files_processed']} files"
    )
    return results


def main():
    """Run the sync process."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    results = sync_logs()

    print("\n" + "=" * 60)
    print("SYNC RESULTS")
    print("=" * 60)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Total Imported: {results['total_imported']}")
    print(f"Files Processed: {results['files_processed']}")
    print(f"Files Failed: {results['files_failed']}")

    for detail in results["details"]:
        status = detail["status"]
        filename = detail["file"]
        if status == "success":
            count = detail["count"]
            total = detail["total_in_file"]
            print(f"  ✓ {filename}: {count}/{total} new readings")
        elif status == "no_readings":
            print(f"  ⚠ {filename}: no readings found")
        else:
            print(f"  ✗ {filename}: {status}")

    print("=" * 60)


if __name__ == "__main__":
    main()
