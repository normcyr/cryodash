#!/bin/sh
# Healthcheck script for Railway/Docker
# Railway runs container on dynamic PORT but healthcheck should use localhost
PORT=${PORT:-8000}
TIMEOUT=5
RETRIES=3

for i in $(seq 1 $RETRIES); do
  if curl -f -s -m $TIMEOUT "http://127.0.0.1:$PORT/api/health" > /dev/null; then
    echo "Health check passed on attempt $i"
    exit 0
  fi
  if [ $i -lt $RETRIES ]; then
    sleep 1
  fi
done

exit 1
