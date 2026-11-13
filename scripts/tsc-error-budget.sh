#!/usr/bin/env bash
# Compare `npm run check` (tsc) error count to TSC_ERROR_BUDGET.
#
# The gate is "must not get worse", not "must be clean". Main still has a
# known pile of pre-existing diagnostics; failing CI solely because of those
# would block the first test-CI PR. Zero is better — if the count drops,
# lower TSC_ERROR_BUDGET in .github/workflows/pr-checks.yml.
#
# THREE verdicts, not two: WITHIN BUDGET, OVER BUDGET, and UNKNOWN. A gate that
# cannot read its input has no verdict, and must not report a pass — "0 errors"
# counted from output that was never captured is the same string a clean
# codebase produces, so a blind read would be indistinguishable from success.
#
# Exit codes: 0 within budget, 1 over budget or the checker failed,
#             2 UNKNOWN (no verdict — the diagnostics could not be read).
set -euo pipefail

BUDGET="${TSC_ERROR_BUDGET:?set TSC_ERROR_BUDGET to the recorded baseline}"
UNKNOWN_EXIT=2

report_unknown() {
  echo "UNKNOWN: $1"
  echo "tsc exit=unreadable errors=UNKNOWN budget=${BUDGET}"
  echo "::error::tsc error-budget gate has no verdict: $1"
  exit "${UNKNOWN_EXIT}"
}

# Capture the compiler's output somewhere we can prove we can read. If the temp
# file cannot be created there is nothing to count, so there is no verdict.
OUT=""
if ! OUT="$(mktemp 2>/dev/null)"; then
  report_unknown "mktemp failed (TMPDIR=${TMPDIR:-unset}); compiler output cannot be captured"
fi
if [[ -z "${OUT}" || ! -f "${OUT}" || ! -r "${OUT}" ]]; then
  report_unknown "mktemp returned a path that is not a readable file: '${OUT}'"
fi
trap 'rm -f "${OUT}"' EXIT

set +e
npm run check -- --pretty false --incremental false >"${OUT}" 2>&1
TSC_EXIT=$?
set -e

# The file existed before the run; re-check it, because a run that removed it
# or filled it with an unreadable file leaves us with no diagnostics either.
if [[ ! -f "${OUT}" || ! -r "${OUT}" ]]; then
  report_unknown "the output file ${OUT} is not readable after the check ran"
fi

# Count compiler diagnostics, not the optional "Found N errors." summary
# (tsc omits that line when N=0).
COUNT="$(grep -cE ': error TS[0-9]+' "${OUT}" || true)"
SIZE="$(wc -c <"${OUT}" | tr -d ' ')"

echo "tsc exit=${TSC_EXIT} errors=${COUNT} output_bytes=${SIZE} budget=${BUDGET}"

# Non-zero exit with no diagnostics: the checker stopped before it could report.
# The count is not a measurement, so it is not a pass either.
if [[ "${COUNT}" -eq 0 && "${TSC_EXIT}" -ne 0 ]]; then
  report_unknown "the checker exited ${TSC_EXIT} without emitting any error TS diagnostics"
fi

# Zero diagnostics from an empty read is exactly the case this gate cannot
# decide: a genuinely clean tree and a checker that never ran produce the same
# output. Report UNKNOWN rather than PASS. It cannot fire while the tree has
# pre-existing errors; if the count ever reaches 0 and this blocks a real clean
# run, lower TSC_ERROR_BUDGET or make `npm run check` emit a completion marker.
if [[ "${COUNT}" -eq 0 && "${SIZE}" -eq 0 ]]; then
  report_unknown "zero diagnostics from an empty read; a clean tree and a silent checker are indistinguishable"
fi

if [[ "${COUNT}" -gt "${BUDGET}" ]]; then
  echo "::error::TypeScript error count rose from ${BUDGET} to ${COUNT}. Gate is must-not-get-worse."
  grep -E ': error TS[0-9]+' "${OUT}" || true
  exit 1
fi

if [[ "${COUNT}" -lt "${BUDGET}" ]]; then
  echo "::notice::tsc errors dropped to ${COUNT} (budget ${BUDGET}). Lower TSC_ERROR_BUDGET in pr-checks.yml."
fi

if [[ "${COUNT}" -gt 0 ]]; then
  echo "Within budget (${COUNT} <= ${BUDGET}). Pre-existing errors; not a new regression."
fi

exit 0
