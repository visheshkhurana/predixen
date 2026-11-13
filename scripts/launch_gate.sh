#!/bin/bash
# === LAUNCH GATE CHECK ===
#
# WHAT THIS CAN PROVE, AND WHAT IT STRUCTURALLY CANNOT (read before trusting a PASS)
#
# A SNAPSHOT OF ONE AFTERNOON, measured 2026-10-19 against
# https://founderconsole.ai. It is here to show the shape, NOT as a property
# this file asserts or that has to stay true. Nothing below compares a byte
# count or a hash, so when these numbers move — and they will, on the next
# deploy — no check here is wrong and nothing needs editing. Re-stamp the date
# if you re-measure; do not promote any of them into an assertion.
#
#   /auth                 200  4513B  sha256 6a71ba3c352b...
#   /scenarios            200  4513B  sha256 6a71ba3c352b...
#   /nonexistent-xyz-404  404  3787B  sha256 2d01769a89a3...
#
# server/static.ts answers a path it does not know with the index.html shell, so
# /auth and /scenarios are BYTE-IDENTICAL: that is the shell, not a page. A body
# grep for "FounderConsole" therefore passes for any URL that reaches the
# shell, existing route or not, and an app whose routes are all unmounted
# returns the same bytes as one whose routes work. That is the blind spot this
# script cannot close from the outside: it can tell you the server answered and
# the shell was served, not that React mounted and rendered a page. Proving
# routes work needs a browser (or the prerendered routes below, whose bodies are
# larger and distinct because they are rendered on the server at build time).
#
# The unknown path is no longer one of those. HAG-162 (#86, 81d93a85) replaced
# the 200-shell fall-through with a real 404 and its own body, so that row
# differs from the shell in all three columns — status, size and hash. This
# paragraph said the opposite for a week, and the check below argued from it.
#
# What each check therefore asserts, and no more:
#   - the exact HTTP status, so a redirect, a 5xx or a dropped connection FAILS
#     instead of quietly matching the shell;
#   - a body marker, so an empty or error body FAILS even at status 200;
#   - for /api/health, a real 200 from the API, which is the ONE check here that
#     goes red when the app itself is down rather than merely routing.
#
# The unknown-path check asserts 404, and the marker moves with the status.
# server/static.ts returns { status: 404, html: injectNotFoundShell(...) } for a
# path it does not know, so 404 is the documented behaviour now. The sentence
# this comment used to argue from — "Unknown app routes stay 200 (the SPA
# shell)" in server/seo-prerender.ts — describes htmlStatus() for KNOWN app
# routes; it never described the unknown path, which is why this file asserted
# 200 against a product that had begun answering 404 and went red without
# anyone noticing: nothing in CI runs this script (see
# .github/workflows/pr-checks.yml, "Out of scope"). "Page not found" is the 404
# body's own title, so a 404 that serves the shell instead of a not-found page
# still FAILS here — the status alone would not catch that. See HAG-406,
# HAG-279 and HAG-162.
#
# HAG-471. A status plus a marker every page carries is still not an assertion.
# "FounderConsole" is in the shell, so it passes on a blank app, on a dead route
# and on the wrong page served by a routing mistake. Each row below therefore
# asserts a string only that page emits, taken from server/seo-prerender.ts and
# confirmed by rendering that module directly rather than by eyeballing the
# source, and every marker is ASCII so none of them depends on an em dash
# surviving the locale.
#
# And a page that answers 200 must not be the not-found document. That is the
# error-state check: each row forbids "Page not found" unless it is the row
# whose whole job is to expect it. So a proxy that rewrites a 404 to 200, or a
# route that renders the error page under the wrong URL, FAILS here even though
# its status and its title look healthy.
#
# /auth and /scenarios get no marker, because there is none to give them: both
# render as the bare shell with nothing server-rendered in the body, so a curl
# assertion on either can only assert that the deployment answered. They stay
# as status rows and are labelled as deployment checks, not page checks.
# /scenarios redirects to /auth in the browser and /simulate is auth-gated;
# those facts exist only after JavaScript runs, which is a Playwright job.

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

# check NAME URL EXPECTED_STATUS [BODY_PATTERN] [FORBIDDEN_PATTERN]
#
# FORBIDDEN_PATTERN defaults to ERROR_MARKER: a page that answers 200 must not be
# the not-found document. Pass "" only on the row that expects a 404, because
# that body is where the marker legitimately lives.
ERROR_MARKER="Page not found"
check() {
  local name="$1" url="$2" want="$3" pattern="$4" forbid="${5-$ERROR_MARKER}"
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
  # -F: the marker is a FIXED STRING. Under BRE a marker containing [ ] * ^ $
  # or a backslash is silently a regular expression, and 'Demo | FounderConsole'
  # only works because a bare | is literal in BRE. -F makes every marker mean
  # exactly the characters it is written with.
  if [ -n "$pattern" ] && ! printf '%s' "$REPLY_BODY" | grep -qF "$pattern"; then
    echo "  FAIL: $name (status $REPLY_STATUS ok, body does not contain '$pattern')"
    FAIL=$((FAIL+1))
    return
  fi
  if [ -n "$forbid" ] && printf '%s' "$REPLY_BODY" | grep -qF "$forbid"; then
    echo "  FAIL: $name (status $REPLY_STATUS ok, but the body is the error page: it contains '$forbid')"
    FAIL=$((FAIL+1))
    return
  fi
  echo "  PASS: $name (status $REPLY_STATUS)"
  PASS=$((PASS+1))
}

echo "Target: $BASE_URL"
echo ""
check "/ serves frontend"                "$BASE_URL/"                   200 "The Flight Simulator for Founders"
check "/demo serves frontend"            "$BASE_URL/demo"                200 "See FounderConsole in action"
check "/pricing serves frontend"         "$BASE_URL/pricing"             200 "What is included"
check "/signup serves the register page" "$BASE_URL/signup"              200 "Get started with FounderConsole"
# The document title, which the body rows above do NOT cover: "Demo | FounderConsole"
# and "Pricing | FounderConsole" are the tab text and the search-result headline, and
# until now the only assertion on either was this file's old body-only rows. Nothing
# in CI pins them (grep 'Demo | FounderConsole' over server/tests and client finds the
# two source strings and no test), so a deploy serving the wrong tab title used to
# leave both this gate and CI green. check() takes one marker, so these are two rows
# rather than two arguments.
#
# The marker carries the <title> tags, not just the words. The bare string is not a
# title assertion: measured on the live bodies it appears 3 times on /demo and 4 times
# on /pricing (og:title, twitter:title, and for /pricing the JSON-LD "name"), so a
# deploy that changed only <title> would still match a bare-string row. Matching the
# whole element is what makes "the tab title changed" a FAIL.
check "/demo title"    "$BASE_URL/demo"    200 "<title>Demo | FounderConsole</title>"
check "/pricing title" "$BASE_URL/pricing" 200 "<title>Pricing | FounderConsole</title>"
echo "  NOTE: /auth and /scenarios below are DEPLOYMENT checks, not page"
echo "        checks. Both render as the bare shell with no server-rendered"
echo "        body, so all this can prove is that the server answered at 200"
echo "        and did not send the error page. That the route mounts and that"
echo "        /scenarios redirects to /auth are browser facts - see the header."
check "/auth is served (deployment check, shell only)" \
                                         "$BASE_URL/auth"               200 "FounderConsole"
check "/scenarios is served (deployment check, shell only)" \
                                         "$BASE_URL/scenarios"          200 "FounderConsole"
check "unknown path is a real 404 (HAG-162), NOT the SPA shell" \
                                         "$BASE_URL/nonexistent-xyz-404" 404 "Page not found" ""

# The word "healthy" is not an assertion: {"status":"healthy","database":
# "disconnected"} contains it and is a dead app. These four are the fields that
# actually have to hold, one request each because check() takes one marker.
check "health: database connected"       "$BASE_URL/api/health"          200 '"database":"connected"'
check "health: redis connected"          "$BASE_URL/api/health"          200 '"redis":"connected"'
check "health: ready"                    "$BASE_URL/api/health"          200 '"ready":true'
check "health: no startup error"         "$BASE_URL/api/health"          200 '"startup_error":null'

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
if [ $FAIL -gt 0 ]; then
  echo "LAUNCH GATE: FAILED"
  exit 1
else
  echo "LAUNCH GATE: PASSED"
  exit 0
fi
