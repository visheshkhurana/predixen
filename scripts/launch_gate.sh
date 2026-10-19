#!/bin/bash
# === LAUNCH GATE CHECK ===
#
# WHAT THIS CAN PROVE, AND WHAT IT STRUCTURALLY CANNOT (read before trusting a PASS)
#
# The app is a single-page app. server/static.ts answers an unmatched path with
# the same index.html shell at status 200, so every client route and every
# nonsense path return the same bytes. Measured 2026-10-17 against
# https://founderconsole.ai:
#
#   /auth                 200  4558B  sha256 c65523ff280e85bf...
#   /scenarios            200  4558B  sha256 c65523ff280e85bf...
#   /nonexistent-xyz-404  200  4558B  sha256 c65523ff280e85bf...
#
# Those three are BYTE-IDENTICAL. So a body grep for "FounderConsole" passes for
# any URL that reaches the shell, existing route or not, and an app whose routes
# are all unmounted returns exactly the same bytes as one whose routes work.
# That is the blind spot this script cannot close from the outside: it can tell
# you the server answered and the shell was served, not that React mounted and
# rendered a page. Proving routes work needs a browser (or the prerendered
# routes below, whose bodies are larger and distinct because they are rendered
# on the server at build time).
#
# What each check therefore asserts, and no more:
#   - the exact HTTP status, so a redirect, a 5xx or a dropped connection FAILS
#     instead of quietly matching the shell;
#   - a body marker, so an empty or error body FAILS even at status 200;
#   - for /api/health, a real 200 from the API, which is the ONE check here that
#     goes red when the app itself is down rather than merely routing.
#
# The unknown-path check asserts 200, because 200 is the documented behaviour:
# server/seo-prerender.ts says "Unknown app routes stay 200 (the SPA shell)" and
# only unknown /tools/*, /runway/* and /blog/* carry a real 404. Asserting 404
# here would encode a wish, not the product. See HAG-406 and HAG-279.

echo "=== LAUNCH GATE CHECK ==="
echo ""
PASS=0
FAIL=0
BASE_URL="${1:-https://founderconsole.ai}"

# One request per check: prints the body, then a final line with the status.
# Redirects are NOT followed (-L off), so a 301/302 is reported as such instead
# of being silently promoted to the target's 200.
REPLY_STATUS=""
REPLY_BODY=""
REPLY_CURL_RC=0
# Name the failure a nonzero curl exit means, so a FAIL says which one happened.
curl_reason() {
  case "$1" in
    6)  echo "could not resolve host" ;;
    7)  echo "connection refused" ;;
    18) echo "partial file: response truncated" ;;
    28) echo "timed out" ;;
    35) echo "TLS handshake failed" ;;
    52) echo "empty reply from server" ;;
    56) echo "failure receiving network data" ;;
    *)  echo "transfer error" ;;
  esac
}
fetch() {
  local out rc
  out="$(curl -s --max-time 20 -w $'\n%{http_code}' "$1" 2>/dev/null)"
  # curl's exit status is the only signal that the transfer completed. A server
  # that sends 200 and the marker and then truncates still prints %{http_code}
  # 200 while curl exits 18 (partial file), so the status alone would PASS a
  # response that never fully arrived. -f is deliberately NOT used: without it
  # curl exits 0 on a real 4xx/5xx and the status assertion catches those.
  rc=$?
  REPLY_CURL_RC="$rc"
  REPLY_STATUS="${out##*$'\n'}"
  REPLY_BODY="${out%$'\n'*}"
  [ -n "$REPLY_STATUS" ] || REPLY_STATUS="000"
}

# check NAME URL EXPECTED_STATUS [BODY_PATTERN]
check() {
  local name="$1" url="$2" want="$3" pattern="$4"
  fetch "$url"
  if [ "$REPLY_CURL_RC" -ne 0 ]; then
    echo "  FAIL: $name (curl exit $REPLY_CURL_RC: $(curl_reason "$REPLY_CURL_RC"))"
    FAIL=$((FAIL+1))
    return
  fi
  if [ "$REPLY_STATUS" != "$want" ]; then
    echo "  FAIL: $name (status $REPLY_STATUS, wanted $want)"
    FAIL=$((FAIL+1))
    return
  fi
  if [ -n "$pattern" ] && ! printf '%s' "$REPLY_BODY" | grep -q "$pattern"; then
    echo "  FAIL: $name (status $REPLY_STATUS ok, body does not contain '$pattern')"
    FAIL=$((FAIL+1))
    return
  fi
  echo "  PASS: $name (status $REPLY_STATUS)"
  PASS=$((PASS+1))
}

echo "Target: $BASE_URL"
echo ""
check "/auth serves frontend"            "$BASE_URL/auth"                200 "FounderConsole"
check "/api/health returns healthy"      "$BASE_URL/api/health"          200 '"healthy"'
check "/demo serves frontend"            "$BASE_URL/demo"                200 "Demo | FounderConsole"
check "/pricing serves frontend"         "$BASE_URL/pricing"             200 "Pricing | FounderConsole"
echo "  NOTE: the next two are SPA-shell checks. They prove the shell was"
echo "        served at 200, not that the route mounted. See the header."
check "/scenarios serves frontend"       "$BASE_URL/scenarios"           200 "FounderConsole"
check "unknown path serves the SPA shell (200 by design, NOT a 404)" \
                                         "$BASE_URL/nonexistent-xyz-404" 200 "FounderConsole"

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
if [ $FAIL -gt 0 ]; then
  echo "LAUNCH GATE: FAILED"
  exit 1
else
  echo "LAUNCH GATE: PASSED"
  exit 0
fi
