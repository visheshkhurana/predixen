#!/usr/bin/env bash
# Compare `npm run check` (tsc) error count to TSC_ERROR_BUDGET.
#
# The gate is "must not get worse", not "must be clean". Main still has a
# known pile of pre-existing diagnostics; failing CI solely because of those
# would block the first test-CI PR. Zero is better — if the count drops,
# lower TSC_ERROR_BUDGET in .github/workflows/pr-checks.yml.
set -euo pipefail

BUDGET="${TSC_ERROR_BUDGET:?set TSC_ERROR_BUDGET to the recorded baseline}"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

set +e
npm run check -- --pretty false --incremental false >"$OUT" 2>&1
TSC_EXIT=$?
set -e

# Count compiler diagnostics, not the optional "Found N errors." summary
# (tsc omits that line when N=0).
COUNT="$(grep -cE ': error TS[0-9]+' "$OUT" || true)"

echo "tsc exit=${TSC_EXIT} errors=${COUNT} budget=${BUDGET}"

if [[ "${COUNT}" -eq 0 && "${TSC_EXIT}" -ne 0 ]]; then
  echo "::error::tsc failed without emitting error TS diagnostics (exit ${TSC_EXIT})."
  cat "$OUT"
  exit 1
fi

if [[ "${COUNT}" -gt "${BUDGET}" ]]; then
  echo "::error::TypeScript error count rose from ${BUDGET} to ${COUNT}. Gate is must-not-get-worse."
  grep -E ': error TS[0-9]+' "$OUT" || true
  exit 1
fi

if [[ "${COUNT}" -lt "${BUDGET}" ]]; then
  echo "::notice::tsc errors dropped to ${COUNT} (budget ${BUDGET}). Lower TSC_ERROR_BUDGET in pr-checks.yml."
fi

if [[ "${COUNT}" -gt 0 ]]; then
  echo "Within budget (${COUNT} <= ${BUDGET}). Pre-existing errors; not a new regression."
fi

exit 0
