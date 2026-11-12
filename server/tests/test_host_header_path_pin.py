"""HAG-637 — the Host header must not be able to move `request.url.path`.

GHSA-86qp-5c8j-p5mr (CVE-2026-48710), affected starlette <= 1.0.0: starlette
rebuilt `request.url` from the Host header, so a Host containing `/` shifted the
parsed path while the router still dispatched the real raw path. Two middlewares
in this repo make a security decision from `request.url.path`:

  csrf_protection.py:54   `_is_path_exempt(request.url.path)`
  security_headers.py:66  `request.url.path.startswith("/api/")`

so one crafted Host could exempt a request from CSRF and strip `no-store` from an
API response. Both are measured in Sentinel's review of the bump.

The bump to starlette 1.3.1 / fastapi 0.133.0 is what fixes it, and these tests
are what keep it fixed: fastapi 0.133.0 declares `starlette>=0.40.0` with **no
upper bound**, so a later relock can take any starlette and nothing else in this
suite would notice.

These two rows are red on a stale venv, and that is expected. They need the
starlette `uv.lock` pins (1.3.1); a machine still on starlette <= 1.0.0 fails
them on the patched and the unpatched tree alike, which is the vulnerability
showing through, not the test. CI installs `uv.lock` with `--frozen` and then
runs these tests, so a lock that lands starlette at or below 1.0.0 turns CI red on
the two rows that measure the vulnerability; a relock that simply takes the newest
starlette stays green, because newest is already fixed. What these tests cannot
tell you is anything about a developer machine whose venv is older than the lock:
that is the case where red is expected and correct. The three rows below that are
not about the Host header (fixture pin, exempt-path positive, control) are
starlette-independent.

What each test kills:

  test_the_exempt_fixture_matches_what_main_registers
      - main.py gaining, losing or renaming an exemption while this file keeps
        its own hand-written copy. The list below was a hand copy that had
        already drifted: main.py registered 9, this file said 7 and claimed they
        were "the same exemptions server/main.py registers". Adding the two
        missing entries would have been the same copy with a fresh drift clock,
        so the equality is now asserted against main.py's own source.
  test_a_crafted_host_cannot_exempt_itself_from_csrf
      - a starlette that rebuilds request.url from the Host header: the crafted
        Host makes the path read `/health/companies/1/memo/export`, which is
        exempt, so the 403 becomes a 200 with the endpoint reached.
  test_a_crafted_host_cannot_strip_no_store_from_api_responses
      - the same regression seen through the other consumer: the path no longer
        starts with `/api/`, so the `no-store` branch is skipped.
  test_an_exempt_path_is_still_allowed
      - an exemption list that has stopped exempting: empty `EXEMPT_PATHS`, or
        only `/health` removed. Without this row the two refusals above cannot
        tell "a crafted host is refused" from "nothing is exempt any more" —
        both read 403.
  test_control_a_normal_host_still_works
      - control. Same requests, same middleware, one extra header nothing asserts
        on. If this goes red the tests above are measuring the request shape, not
        the host validation.

The tests supply the hostile Host and never supply or assert a path: the app is
left to compute `request.url.path` for itself, which is the value under test.
"""
import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.middleware.csrf_protection import CSRFProtectionMiddleware
from server.middleware.security_headers import SecurityHeadersMiddleware

MAIN_PY = Path(__file__).resolve().parents[1] / "main.py"

# A copy of what server/main.py registers, in the same order — and a copy is only
# safe while something measures it, which is what
# test_the_exempt_fixture_matches_what_main_registers is for. Used here rather
# than read at import time so each row below runs against a list written out in
# this file, where a change to it is visible in the diff that made it.
EXEMPT_PATHS = [
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/admin/login",
    "/auth/refresh",
    "/companies/*/seed-sample",
    "/billing/webhook",  # Stripe webhook — authenticated by signature, not session
    # RFC 8058 one-click POST has no session and no CSRF header.
    "/email/unsubscribe",
    "/api/email/unsubscribe",
]

AUTH = {"authorization": "Bearer x", "origin": "https://app.local"}


def _registered_exempt_paths():
    """The exemption list main.py actually hands `CSRFProtectionMiddleware`.

    Parsed, not imported: importing server.main builds the whole app, opens the
    database engine and reads the environment, none of which this test is about,
    and a failure in any of it would read as "the exemptions drifted". The call
    is the source of truth either way — this returns the literal main.py passes.
    """
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "add_middleware"):
            continue
        if not node.args:
            continue
        target = node.args[0]
        name = getattr(target, "id", None) or getattr(target, "attr", None)
        if name != "CSRFProtectionMiddleware":
            continue
        for keyword in node.keywords:
            if keyword.arg != "exempt_paths":
                continue
            assert isinstance(keyword.value, ast.List), (
                f"{MAIN_PY} registers CSRF exemptions with something other than a "
                "list literal; this test cannot pin it — pin it differently rather "
                "than deleting the test"
            )
            found.append([element.value for element in keyword.value.elts])
    assert len(found) == 1, (
        f"expected exactly one CSRFProtectionMiddleware registration in {MAIN_PY}, "
        f"found {len(found)}"
    )
    return found[0]


def _app() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFProtectionMiddleware, exempt_paths=EXEMPT_PATHS)

    @app.post("/companies/1/memo/export")
    async def export_memo():
        return {"reached": True}

    @app.get("/api/companies")
    async def api_companies():
        return {"reached": True}

    @app.post("/health")
    async def health_post():
        return {"reached": True}

    return TestClient(app)


def test_the_exempt_fixture_matches_what_main_registers():
    # The drift guard. Both sides can move and this goes red: main.py adding or
    # dropping an exemption, or the list above changing without main.py.
    registered = _registered_exempt_paths()

    assert len(registered) == len(set(registered)), (
        f"server/main.py registers the same exemption twice: {registered}"
    )
    fixture = set(EXEMPT_PATHS)
    assert fixture == set(registered), (
        "the exemptions in this file have drifted from the ones server/main.py "
        "registers — update the list above in the same commit.\n"
        f"  in this file, not registered: {sorted(fixture - set(registered))}\n"
        f"  registered, not in this file: {sorted(set(registered) - fixture)}"
    )


def test_a_crafted_host_cannot_exempt_itself_from_csrf():
    r = _app().post("/companies/1/memo/export", headers={**AUTH, "host": "app.local/health"})
    assert r.status_code == 403, r.text


def test_a_crafted_host_cannot_strip_no_store_from_api_responses():
    r = _app().get("/api/companies", headers={"host": "app.local/decoy"})
    assert "no-store" in (r.headers.get("cache-control") or ""), r.headers


def test_an_exempt_path_is_still_allowed():
    # Authorization is what makes this row mean anything: the middleware lets an
    # unauthenticated POST through whatever the exemption list says, so a request
    # without it would pass on an emptied list too.
    r = _app().post("/health", headers=AUTH)
    assert r.status_code == 200, r.text
    assert r.json() == {"reached": True}, r.text


def test_control_a_normal_host_still_works():
    r = _app().get("/api/companies", headers={"host": "app.local", "x-harmless": "1"})
    assert r.status_code == 200 and "no-store" in r.headers["cache-control"]
