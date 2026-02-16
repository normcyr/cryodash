#!/bin/sh
# Healthcheck script for Railway/Docker
PORT=${PORT:-8000}
curl -f "http://localhost:$PORT/api/health" || exit 1
