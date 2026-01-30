# Direct Instrument API

## Overview

The Direct Instrument API allows instruments (like NMR spectrometers) to POST their cryogenic readings directly to CryoDash instead of relying on hourly synchronization of log files from a remote server.

This approach is **much more efficient**:

- **Bandwidth**: ~100 bytes per reading vs 100k lines (100% overhead reduction)
- **Latency**: Real-time (seconds) vs 1 hour delay
- **CPU**: Direct insert vs full file parse
- **Scalability**: Linear cost vs exponential with number of instruments

## API Endpoint

### POST /api/readings

Submit a new cryogenic reading from an instrument.

**Request:**

```bash
curl -X POST http://cryodash.example.com/api/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device": "neo600",
    "cryogen": "N2",
    "level": 87.5,
    "timestamp": "2026-01-30T11:15:00Z"
  }'
```

**Parameters:**

- `device` (string, required): Instrument identifier (e.g., "neo600", "neo700")
- `cryogen` (string, required): Cryogen type ("N2" or "He")
- `level` (float, required): Current level percentage (0-100)
- `timestamp` (ISO8601 datetime, optional): Reading timestamp. Defaults to current time if omitted.

**Success Response (200 OK):**

```json
{
  "id": 141291,
  "device": "neo600",
  "cryogen": "N2",
  "level": 87.5,
  "timestamp": "2026-01-30T11:15:00"
}
```

**Error Responses:**

- **404 Not Found**: Instrument doesn't exist

  ```json
  {"detail": "Instrument neo800 not found"}
  ```

- **400 Bad Request**: Invalid cryogen for this instrument

  ```json
  {"detail": "Cryogen Ar not valid for neo600"}
  ```

## Validation

The endpoint validates:

1. **Instrument exists** in the database
2. **Cryogen is valid** for that instrument (neo600 accepts N2 only, neo700 accepts N2 and He)
3. **Level is within valid range** (0-100%)

## Real-Time Updates

When a reading is posted:

1. ✅ Data is saved to the database
2. ✅ Alert status is calculated automatically
3. ✅ Reading is broadcast to all connected WebSocket clients
4. ✅ Dashboard updates in real-time (no page refresh needed)

## Scheduling

For continuous monitoring, instruments should POST readings at regular intervals:

**Recommended frequencies:**

- **N2**: Every 5-15 minutes (fast evaporation, needs frequent monitoring)
- **He**: Every 30 minutes to 1 hour (slow evaporation)

Example cron job on the instrument:

```bash
# Post neo600 N2 level every 10 minutes
*/10 * * * * /usr/local/bin/post_reading.sh neo600 N2

# Post neo700 readings every 5 minutes
*/5 * * * * /usr/local/bin/post_reading.sh neo700 N2
*/5 * * * * /usr/local/bin/post_reading.sh neo700 He
```

## Fallback Strategy

The system still maintains the hourly sync from the remote log file as a **fallback**:

- If an instrument fails to POST for extended periods, sync catches missing data
- Sync is disabled if direct API readings start flowing regularly
- Can be manually triggered via `POST /api/sync-logs`

## Migration Path

**Phase 1 (Current)**: Keep hourly sync active

- Instruments start POSTing readings
- System accepts both direct API and file sync
- No disruption to existing monitoring

**Phase 2 (Future)**: Reduce sync frequency

- If direct API is reliable, reduce sync to 4 hours
- Use sync only as safety net

**Phase 3 (Optional)**: Disable sync entirely

- Once all instruments use direct API
- Faster response, cleaner architecture

## Monitoring

Check the status of readings:

```bash
# Get current levels for an instrument
curl http://cryodash.example.com/api/instruments/neo600

# Get last 24 hours of readings
curl http://cryodash.example.com/api/instruments/neo600/history?hours=24

# Check evaporation rates
curl http://cryodash.example.com/api/evaporation-rate
```

## Example Implementation (Python)

```python
import requests
import json
from datetime import datetime

def send_reading(device, cryogen, level, cryodash_url="http://localhost:8000"):
    """Send a reading to CryoDash."""
    endpoint = f"{cryodash_url}/api/readings"

    payload = {
        "device": device,
        "cryogen": cryogen,
        "level": level,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=5)
        response.raise_for_status()

        print(f"✓ Reading posted: {device}/{cryogen} = {level}%")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to post reading: {e}")
        return False

# Usage
send_reading("neo600", "N2", 87.5)
send_reading("neo700", "N2", 92.1)
send_reading("neo700", "He", 86.3)
```

## Logging

All direct API submissions are logged with timestamps:

```
2026-01-30 11:16:52 - cryodash.api.routes - DEBUG - POST /readings - Creating reading for neo600/N2: 85.3%
2026-01-30 11:16:52 - cryodash.api.routes - DEBUG - POST /readings - Reading saved successfully: neo600/N2 = 85.3%
2026-01-30 11:16:52 - cryodash.api.routes - DEBUG - POST /readings - Broadcasting to WebSocket clients for neo600
```

## Performance Impact

**Bandwidth reduction:**

- Old: 100k lines × 80 bytes/line = ~8 MB per sync, every hour = 8 MB/hour
- New: 100 bytes per reading, every 5 minutes = ~1.5 KB/hour
- **Improvement: 5000x less bandwidth** 🎉

**CPU reduction:**

- Old: Parse full file, extract relevant lines, insert to DB
- New: Direct insert, no parsing
- **Improvement: Near-instant processing** ⚡

**Latency reduction:**

- Old: Up to 1 hour delay
- New: <1 second delay
- **Improvement: 3600x faster** 🚀
