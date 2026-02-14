#!/bin/bash
cd "$(dirname "$0")/.."
python qa-lab/runner/qa_runner.py "$@"
QA_EXIT=$?

if [ -f qa-lab/latest-report.md ]; then
  echo ""
  echo "--- Pushing report to Notion ---"
  node qa-lab/runner/push-to-notion.js qa-lab/latest-report.md || echo "Warning: Notion push failed (non-fatal)"
else
  echo "No report file found, skipping Notion push."
fi

exit $QA_EXIT
