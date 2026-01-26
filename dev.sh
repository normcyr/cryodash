#!/bin/bash
# Development server launcher

cd "$(dirname "$0")" || exit

# Activate venv
source .venv/bin/activate

# Launch uvicorn with reload
python -m uvicorn cryodash.main:app --reload --host 0.0.0.0 --port 8000
