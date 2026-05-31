#!/usr/bin/env bash
# Stop the demo cleanly.
set -u
echo "Stopping gateway..."
pkill -9 -f 'gateway.py' 2>/dev/null || true
echo "Stopping backend..."
pkill -9 -f 'uvicorn app.main:app' 2>/dev/null || true
echo "Stopping Postgres container (data preserved)..."
docker stop pcs-pg 2>/dev/null || true
echo "Done."
