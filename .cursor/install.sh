#!/usr/bin/env bash
# Cloud Agent install phase for FounderConsole.
# Idempotent, non-interactive dependency refresh run after the repo is checked out.
# System packages are installed here (once, into the build baseline); per-boot
# service startup lives in start.sh.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"
echo "[install] Repo root: ${REPO_ROOT}"

# --- System packages -------------------------------------------------------
# PostgreSQL (required DB), Redis (cache/job queue), poppler-utils (pdf2image/
# pdfplumber document ingestion), plus curl/ca-certificates.
if ! command -v pg_ctlcluster >/dev/null 2>&1 || ! command -v redis-server >/dev/null 2>&1 || ! command -v pdftoppm >/dev/null 2>&1; then
  echo "[install] Installing system packages (postgresql, redis, poppler-utils)..."
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends \
    postgresql postgresql-contrib redis-server poppler-utils curl ca-certificates
else
  echo "[install] System packages already present, skipping apt."
fi

# --- uv (Python package/venv manager) -------------------------------------
if ! command -v uv >/dev/null 2>&1 && [ ! -x "${HOME}/.local/bin/uv" ]; then
  echo "[install] Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="${HOME}/.local/bin:${PATH}"

# --- Node dependencies -----------------------------------------------------
echo "[install] Installing Node dependencies (npm ci)..."
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

# --- Python dependencies (exact versions from uv.lock) --------------------
echo "[install] Syncing Python dependencies into .venv..."
export UV_PROJECT_ENVIRONMENT="${REPO_ROOT}/.venv"
if [ ! -x "${REPO_ROOT}/.venv/bin/python" ]; then
  uv venv "${REPO_ROOT}/.venv" --python "$(command -v python3)"
fi
uv sync --frozen --no-dev --no-install-project

# --- Local dev environment file (non-secret dev defaults) ------------------
# .env is gitignored; generate a dev-only one if the agent has not provided it.
if [ ! -f .env ]; then
  echo "[install] Writing dev .env (no secrets; safe local defaults)..."
  cat > .env <<'ENV'
# Auto-generated dev defaults for Cloud Agent. Not for production.
DATABASE_URL=postgresql://founderconsole:founderconsole@localhost:5432/founderconsole
REDIS_URL=redis://localhost:6379/0
SESSION_SECRET=dev-only-session-secret-not-for-production-use-change-me
NODE_ENV=development
ENVIRONMENT=development
PORT=5000
FASTAPI_PORT=8001
PYTHON_BIN=./.venv/bin/python
CREATE_SCHEMA=true
RUN_MIGRATIONS=true
SEED_BENCHMARKS=true
SEED_DEMO_DATA=true
CORS_ORIGINS=http://localhost:5000,http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
ENV
else
  echo "[install] .env already exists, leaving it untouched."
fi

echo "[install] Done."
