#!/usr/bin/env bash
# Deploy / update FounderConsole on the VPS.
# Usage: bash deploy/deploy.sh          (from the repo root)
#        bash deploy/deploy.sh --no-pull   (deploy current checkout without git pull)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.production ]; then
  echo "ERROR: .env.production not found. Copy deploy/env.production.example and fill it in." >&2
  exit 1
fi

if [ "${1:-}" != "--no-pull" ]; then
  echo "==> Pulling latest code"
  git pull --ff-only
fi

echo "==> Building and starting containers"
docker compose --env-file .env.production up -d --build

echo "==> Waiting for app to become healthy"
for i in $(seq 1 60); do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$(docker compose ps -q app)" 2>/dev/null || echo starting)
  if [ "$status" = "healthy" ]; then
    echo "==> App is healthy ✔"
    break
  fi
  if [ "$i" = 60 ]; then
    echo "ERROR: app did not become healthy in time. Recent logs:" >&2
    docker compose logs --tail=100 app >&2
    exit 1
  fi
  sleep 5
done

echo "==> Cleaning up old images"
docker image prune -f >/dev/null

echo ""
echo "Deployed. Useful commands:"
echo "  docker compose logs -f app      # live logs (Express + FastAPI + worker)"
echo "  docker compose ps               # container status"
echo "  bash deploy/backup-db.sh        # database backup now"
