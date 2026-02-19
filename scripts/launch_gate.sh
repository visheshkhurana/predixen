#!/bin/bash
echo "=== LAUNCH GATE CHECK ==="
echo ""
PASS=0
FAIL=0
BASE_URL="${1:-https://founderconsole.ai}"

check() {
  local name="$1" url="$2" pattern="$3"
  if curl -sf "$url" 2>/dev/null | grep -q "$pattern"; then
    echo "  PASS: $name"
    PASS=$((PASS+1))
  else
    echo "  FAIL: $name"
    FAIL=$((FAIL+1))
  fi
}

echo "Target: $BASE_URL"
echo ""
check "/auth serves frontend" "$BASE_URL/auth" "FounderConsole"
check "/api/health returns healthy" "$BASE_URL/api/health" '"healthy"'
check "/demo serves frontend" "$BASE_URL/demo" "FounderConsole"
check "/pricing serves frontend" "$BASE_URL/pricing" "FounderConsole"
check "404 page is branded" "$BASE_URL/nonexistent-xyz-404" "FounderConsole"
check "/scenarios serves frontend" "$BASE_URL/scenarios" "FounderConsole"

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
if [ $FAIL -gt 0 ]; then
  echo "LAUNCH GATE: FAILED"
  exit 1
else
  echo "LAUNCH GATE: PASSED"
  exit 0
fi
