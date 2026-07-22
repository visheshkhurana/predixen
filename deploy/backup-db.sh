#!/usr/bin/env bash
# Nightly-safe Postgres backup with 14-day rotation.
# Usage:  bash deploy/backup-db.sh
# Cron (as the deploy user):  crontab -e
#   15 2 * * * cd /home/app/founderconsole && bash deploy/backup-db.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)
FILE="backups/fundflow-${STAMP}.sql.gz"

docker compose exec -T db pg_dump -U fundflow fundflow | gzip > "$FILE"

# sanity check: a real dump is never tiny
SIZE=$(stat -c%s "$FILE")
if [ "$SIZE" -lt 1024 ]; then
  echo "ERROR: backup looks too small (${SIZE} bytes) — check the database container." >&2
  exit 1
fi

echo "Backup written: $FILE ($(numfmt --to=iec "$SIZE"))"

# keep 14 most recent
ls -1t backups/fundflow-*.sql.gz | tail -n +15 | xargs -r rm --

# Restore reference:
#   gunzip -c backups/fundflow-YYYYMMDD-HHMMSS.sql.gz | docker compose exec -T db psql -U fundflow fundflow
