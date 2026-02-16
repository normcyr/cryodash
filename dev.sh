#!/bin/bash
# Development server launcher

cd "$(dirname "$0")" || exit

# Activate venv
source .venv/bin/activate

# Launch uvicorn with reload (excluding tests folder)
python -m uvicorn cryodash.main:app --reload --reload-exclude="tests/*" --host 0.0.0.0 --port 8001
