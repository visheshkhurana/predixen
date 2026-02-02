#!/bin/bash
set -e

echo "[prod] Starting FastAPI backend..."
python -m uvicorn server.main:app --host 0.0.0.0 --port 8001 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "[prod] Waiting for FastAPI..."
for i in {1..30}; do
  if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "[prod] FastAPI is ready"
    break
  fi
  sleep 1
done

echo "[prod] Starting Express frontend..."
NODE_ENV=production node ./dist/index.cjs &
EXPRESS_PID=$!

# Handle shutdown
trap "kill $FASTAPI_PID $EXPRESS_PID 2>/dev/null" EXIT SIGINT SIGTERM

# Wait for either process to exit
wait -n $FASTAPI_PID $EXPRESS_PID
