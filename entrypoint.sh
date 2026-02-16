#!/bin/sh
set -e

# Use PORT env variable if available, otherwise default to 8000
PORT=${PORT:-8000}

echo "Starting CryoDash on port $PORT..."

exec uvicorn cryodash.main:create_app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --factory
