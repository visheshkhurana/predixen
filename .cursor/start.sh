#!/usr/bin/env bash
# Cloud Agent start phase for FounderConsole.
# Per-boot reconciliation: bring up PostgreSQL + Redis and ensure the app's
# role/database exist. Idempotent and safe to re-run. Returns once services are
# ready (it does not block); the dev server runs as a terminal.
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="${DB_NAME:-founderconsole}"
DB_USER="${DB_USER:-founderconsole}"
DB_PASS="${DB_PASS:-founderconsole}"

# --- PostgreSQL ------------------------------------------------------------
PG_VER="$(ls /etc/postgresql 2>/dev/null | sort -V | tail -1 || true)"
if [ -z "${PG_VER}" ]; then
  echo "[start] ERROR: no PostgreSQL cluster config found under /etc/postgresql" >&2
  exit 1
fi

if ! sudo pg_isready -q 2>/dev/null; then
  echo "[start] Starting PostgreSQL ${PG_VER} cluster..."
  sudo pg_ctlcluster "${PG_VER}" main start || sudo pg_ctlcluster "${PG_VER}" main restart
fi

# Wait for PostgreSQL to accept connections.
for _ in $(seq 1 30); do
  if sudo pg_isready -q; then break; fi
  sleep 1
done

echo "[start] Ensuring role and database exist..."
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  END IF;
END \$\$;
SQL
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
fi
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

# --- Redis -----------------------------------------------------------------
if ! redis-cli ping >/dev/null 2>&1; then
  echo "[start] Starting Redis..."
  sudo redis-server /etc/redis/redis.conf --daemonize yes
fi

echo "[start] Services ready (PostgreSQL + Redis)."
