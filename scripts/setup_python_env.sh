#!/usr/bin/env bash
# Create the local Python environment used by the golden path (pytest + QA lab).
# Idempotent: safe to re-run.
#
#   bash scripts/setup_python_env.sh
#
# Uses the dependencies declared in pyproject.toml, so there is no second list
# to keep in sync. Override the interpreter with PYTHON=python3.11 if needed.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3.12}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: $PYTHON not found. Set PYTHON=<interpreter> (>=3.11) and re-run." >&2
  exit 1
fi

echo "Using $("$PYTHON" -V) at $(command -v "$PYTHON")"

if [ ! -d .venv ]; then
  echo "Creating .venv ..."
  "$PYTHON" -m venv .venv
else
  echo "Reusing existing .venv"
fi

# uv is much faster when present; plain pip otherwise.
if command -v uv >/dev/null 2>&1; then
  VIRTUAL_ENV="$PWD/.venv" uv pip install -e .
else
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e .
fi

echo
echo "Done. Run the checks with:"
echo "  .venv/bin/python -m pytest server/tests"
echo "  .venv/bin/python qa-lab/runner/qa_runner.py    # needs a migrated database"
