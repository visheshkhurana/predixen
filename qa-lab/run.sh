#!/bin/bash
cd "$(dirname "$0")/.."
python qa-lab/runner/qa_runner.py "$@"
QA_EXIT=$?

# The same override qa_runner.py honours (HAG-392): if the run wrote its report
# somewhere else, push THAT file, or this would quietly ship the stale tracked copy.
REPORT="${QA_LAB_REPORT:-qa-lab/latest-report.md}"

if [ -f "$REPORT" ]; then
  echo ""
  echo "--- Pushing report to Notion ---"
  node qa-lab/runner/push-to-notion.js "$REPORT" || echo "Warning: Notion push failed (non-fatal)"
else
  echo "No report file found, skipping Notion push."
fi

exit $QA_EXIT
