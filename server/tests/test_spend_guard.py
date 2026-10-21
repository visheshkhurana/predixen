"""Spend guard: 20/minute per user and per company on AI, simulation, Truth Scan.

The window is in-process. A rejected call does not count. The company bucket
is charged only for a caller who may access that company. Templates,
integrations, and notifications are not part of this guard.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from server.core.security import AUTH_COOKIE_NAME, create_access_token
from server.core.spend_guard import (
    MAX_BUFFERED_BODY_BYTES,
    READ_BURST_PER_MINUTE,
    SPEND_BURST_PER_MINUTE,
    SpendGuardMiddleware,
    classify_spend,
    company_id_from_body,
    company_id_from_path,
    company_id_from_query,
    lookup_company_id,
    reset_spend_buckets,
    spend_burst_limited,
    user_may_charge_company,
)

AI_WRITES = [
    "/companies/5/chat",
    "/companies/5/quick-chat",
    "/llm/chat",
    "/llm/quick-chat",
    "/llm/smart-chat",
    "/llm/web-search",
    "/ingest/financials",
    "/ingest/onboarding/extract-deck",
    "/api/companies/5/chat",
]

SIM_WRITES = [
    "/companies/5/simulate",
    "/companies/5/simulate-multi",
    "/companies/5/simulate-enhanced",
    "/companies/5/simulate-scenarios-enhanced",
    "/companies/5/sensitivity-analysis",
    "/companies/5/decision/compare",
    "/companies/5/simulation/agent-run",
    "/scenarios/9/simulate",
    "/scenarios/9/counter-moves",
    "/simulation/v2/run",
    "/simulation-copilot/prompt/5",
    "/simulation-copilot/narrative/5",
    "/simulation-copilot/validate",
    "/simulations/run",
    "/simulations/sensitivity",
    "/simulator/sensitivity/3",
    "/simulator/recommendations/3",
    "/simulator/optimise/constrained/3",
    "/explain-simulation",
    "/survival-sim/run",
    "/api/scenarios/9/simulate",
    "/companies/5/ai-graphics/generate",
    "/companies/5/board-export/generate",
    "/companies/5/board-export/generate-graphic",
    "/companies/5/doc-generator/generate",
    "/companies/5/fundraising/one-pager",
    "/companies/5/strategic-diagnosis",
    "/simulation/4/decisions/generate",
    "/companies/5/smart-alerts/evaluate",
    "/companies/5/smart-alerts/weekly-briefing",
    "/companies/5/competitors/9/scan",
    "/companies/5/web-search",
    "/imports/excel",
    "/imports/pdf",
    "/companies/5/datasets/termina-pdf",
    "/companies/5/datasets/termina-excel",
    "/api/companies/5/ai-graphics/generate",
]

TRUTH_WRITES = [
    "/companies/5/truth/run",
    "/truth-scan/from-import-session",
    "/truth-scan/from-dataset",
    "/truth-scan/from-manual-baseline",
    "/truth-scan/uploads/abc/resolve",
    "/truth-scan/uploads/abc/finalize",
    "/api/companies/5/truth/run",
]

SIM_READS = [
    "/scenarios/9/simulation/latest",
    "/simulation/v2/abc",
    "/simulation/runs",
    "/companies/5/simulation/agent-runs",
    "/survival-sim/abc",
]

TRUTH_READS = [
    "/companies/5/truth/latest",
    "/truth-scan/uploads/abc",
    "/api/companies/5/truth/latest",
]

HELD_LOCKS = [
    ("POST", "/templates/companies/1/apply/baseline"),
    ("POST", "/api/templates/companies/1/bulk-apply"),
    ("POST", "/integrations/companies/1/accounting/sync"),
    ("GET", "/integrations/available"),
    ("POST", "/notifications/feature"),
    ("GET", "/notifications/email-stats"),
    ("POST", "/leads"),
    ("POST", "/auth/login"),
    ("GET", "/llm/models"),
    ("POST", "/companies/5/chat/feedback"),
    ("POST", "/companies/5/smart-alerts/rules"),
    ("GET", "/companies/5/ai-graphics/styles"),
    ("POST", "/companies/5/competitors"),
    ("POST", "/imports/1/verify"),
]


@pytest.fixture(autouse=True)
def _clear_buckets():
    reset_spend_buckets()
    yield
    reset_spend_buckets()


def test_burst_constants_are_modest_and_fixed():
    assert SPEND_BURST_PER_MINUTE == 20
    assert READ_BURST_PER_MINUTE == 60


@pytest.mark.parametrize("path", AI_WRITES + SIM_WRITES + TRUTH_WRITES)
def test_write_routes_are_spend_limited(path):
    assert classify_spend("POST", path) == "write"


@pytest.mark.parametrize("path", SIM_READS + TRUTH_READS)
def test_read_routes_are_read_limited(path):
    assert classify_spend("GET", path) == "read"


def test_strategic_diagnosis_get_is_a_spend_write():
    assert classify_spend("GET", "/companies/5/strategic-diagnosis") == "write"
    assert classify_spend("GET", "/api/companies/5/strategic-diagnosis") == "write"


def test_competitor_digest_get_is_a_spend_write():
    assert classify_spend("GET", "/companies/5/competitors/digest") == "write"
    assert classify_spend("GET", "/api/companies/5/competitors/digest") == "write"


@pytest.mark.parametrize("method,path", HELD_LOCKS)
def test_held_auth_locks_and_other_routes_are_not_spend_limited(method, path):
    assert classify_spend(method, path) is None


def test_user_bucket_blocks_a_second_company_and_rejected_calls_do_not_count():
    store = {}
    limit = SPEND_BURST_PER_MINUTE
    for n in range(limit):
        blocked, _, which = spend_burst_limited(
            [f"user:1:write", "company:1:write"],
            limit=limit,
            now=float(n),
            store=store,
        )
        assert blocked is False
        assert which is None
    blocked, retry, which = spend_burst_limited(
        ["user:1:write", "company:2:write"],
        limit=limit,
        now=float(limit),
        store=store,
    )
    assert blocked is True
    assert which == "user:1:write"
    assert retry >= 1
    assert len(store["user:1:write"]) == limit
    assert "company:2:write" not in store

    blocked_again, _, _ = spend_burst_limited(
        ["user:1:write", "company:2:write"],
        limit=limit,
        now=float(limit),
        store=store,
    )
    assert blocked_again is True
    assert len(store["user:1:write"]) == limit


def test_company_bucket_blocks_a_second_user_and_a_fresh_pair_is_allowed():
    store = {}
    limit = SPEND_BURST_PER_MINUTE
    for n in range(limit):
        blocked, _, _ = spend_burst_limited(
            ["user:1:write", "company:1:write"],
            limit=limit,
            now=1.0,
            store=store,
        )
        assert blocked is False
    blocked, _, which = spend_burst_limited(
        ["user:2:write", "company:1:write"],
        limit=limit,
        now=1.0,
        store=store,
    )
    assert blocked is True
    assert which == "company:1:write"
    assert store.get("user:2:write", []) == []

    allowed, _, _ = spend_burst_limited(
        ["user:2:write", "company:2:write"],
        limit=limit,
        now=1.0,
        store=store,
    )
    assert allowed is False
    assert len(store["user:2:write"]) == 1
    assert len(store["company:2:write"]) == 1


def test_window_expiry_opens_the_bucket_again():
    store = {}
    limit = SPEND_BURST_PER_MINUTE
    for _ in range(limit):
        spend_burst_limited(["user:7:write"], limit=limit, now=0.0, store=store)
    blocked, _, _ = spend_burst_limited(["user:7:write"], limit=limit, now=30.0, store=store)
    assert blocked is True
    opened, _, _ = spend_burst_limited(["user:7:write"], limit=limit, now=61.0, store=store)
    assert opened is False
    assert store["user:7:write"] == [61.0]


def test_read_bucket_does_not_consume_the_spend_bucket():
    store = {}
    for _ in range(READ_BURST_PER_MINUTE):
        blocked, _, _ = spend_burst_limited(
            ["user:1:read", "company:1:read"],
            limit=READ_BURST_PER_MINUTE,
            now=1.0,
            store=store,
        )
        assert blocked is False
    blocked, _, which = spend_burst_limited(
        ["user:1:read"],
        limit=READ_BURST_PER_MINUTE,
        now=1.0,
        store=store,
    )
    assert blocked is True
    assert which == "user:1:read"
    write_blocked, _, _ = spend_burst_limited(
        ["user:1:write", "company:1:write"],
        limit=SPEND_BURST_PER_MINUTE,
        now=1.0,
        store=store,
    )
    assert write_blocked is False


def test_company_id_comes_from_path_query_json_and_multipart():
    assert company_id_from_path("/companies/5/chat") == 5
    assert company_id_from_path("/api/simulation-copilot/prompt/7") == 7
    assert company_id_from_path("/simulator/macros/4") == 4
    assert company_id_from_query("company_id=8") == 8
    assert company_id_from_body(
        "/truth-scan/from-dataset",
        b'{"company_id": 12, "dataset_id": 1}',
        "application/json",
    ) == 12
    multipart = (
        b'--bound\r\nContent-Disposition: form-data; name="companyId"\r\n\r\n42\r\n'
        b'--bound\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\n\r\n'
        b"%PDF\r\n--bound--\r\n"
    )
    assert company_id_from_body("/ingest/financials", multipart, "multipart/form-data; boundary=bound") == 42
    assert company_id_from_path("/llm/smart-chat") is None
    assert company_id_from_path("/simulation/v2/run") is None
    assert company_id_from_path("/ingest/onboarding/extract-deck") is None
    assert company_id_from_path("/simulation-copilot/validate") is None
    assert company_id_from_path("/explain-simulation") is None


def _cookie(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _guarded_app(monkeypatch, membership):
    monkeypatch.setattr(
        "server.core.spend_guard.user_may_charge_company",
        membership,
    )
    app = FastAPI()
    app.add_middleware(SpendGuardMiddleware)

    @app.post("/companies/{company_id}/chat")
    def chat(company_id: int):
        return {"company_id": company_id}

    @app.post("/truth-scan/from-dataset")
    async def from_dataset(request: Request):
        return await request.json()

    @app.post("/ingest/financials")
    async def ingest(request: Request):
        form = await request.form()
        upload = form["file"]
        return {"companyId": int(form["companyId"]), "name": upload.filename, "size": len(await upload.read())}

    @app.post("/companies/{company_id}/simulate")
    def simulate(company_id: int):
        return {"ok": True, "company_id": company_id}

    @app.get("/companies/{company_id}/truth/latest")
    def latest(company_id: int):
        return {"company_id": company_id}

    @app.post("/survival-sim/run")
    def survival():
        return {"ok": True}

    @app.post("/templates/companies/{company_id}/apply/baseline")
    def templates(company_id: int):
        return {"ok": True}

    @app.post("/llm/smart-chat")
    def smart():
        return {"ok": True}

    return TestClient(app)


def test_middleware_blocks_the_21st_write_per_user_and_replays_json(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: True)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    for _ in range(SPEND_BURST_PER_MINUTE):
        response = client.post("/truth-scan/from-dataset", json={"company_id": 4, "dataset_id": 1})
        assert response.status_code == 200, response.text
        assert response.json()["company_id"] == 4
    blocked = client.post("/truth-scan/from-dataset", json={"company_id": 4, "dataset_id": 1})
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] == "user"
    assert blocked.headers["retry-after"]
    other_company = client.post("/companies/9/chat")
    assert other_company.status_code == 429


def test_company_bucket_is_shared_by_members_and_not_by_strangers(monkeypatch):
    def membership(user_id, company_id):
        return (user_id, company_id) in {(1, 1), (2, 1), (2, 2)}

    client = _guarded_app(monkeypatch, membership)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/companies/1/simulate").status_code == 200

    client.cookies.set(AUTH_COOKIE_NAME, _cookie(2))
    blocked = client.post("/companies/1/simulate")
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] == "company"

    allowed = client.post("/companies/2/simulate")
    assert allowed.status_code == 200


def test_stranger_does_not_fill_the_company_bucket(monkeypatch):
    """A caller who cannot access the company does not consume its bucket."""
    monkeypatch.setattr(
        "server.core.spend_guard.user_may_charge_company",
        lambda user_id, company_id: user_id == 2 and company_id == 1,
    )
    app = FastAPI()
    app.add_middleware(SpendGuardMiddleware)

    @app.post("/companies/{company_id}/simulate")
    def simulate(company_id: int):
        return {"ok": True}

    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(3))
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/companies/1/simulate").status_code == 200
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(2))
    assert client.post("/companies/1/simulate").status_code == 200


def test_anonymous_requests_are_rejected_and_do_not_share_one_bucket(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: False)
    for _ in range(SPEND_BURST_PER_MINUTE + 5):
        response = client.post("/companies/1/simulate")
        assert response.status_code == 401, response.text


def test_public_survival_sim_is_limited_per_ip(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: False)
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/survival-sim/run").status_code == 200
    blocked = client.post("/survival-sim/run")
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] == "ip"


def test_multipart_body_reaches_the_handler(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: True)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    response = client.post(
        "/ingest/financials",
        data={"companyId": "6", "fileType": "pdf"},
        files={"file": ("deck.pdf", b"%PDF-1.4 spend", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["companyId"] == 6
    assert body["name"] == "deck.pdf"
    assert body["size"] == len(b"%PDF-1.4 spend")


def test_templates_are_not_burst_limited(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: True)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    for _ in range(SPEND_BURST_PER_MINUTE + 5):
        assert client.post("/templates/companies/1/apply/baseline").status_code == 200


def test_route_without_a_company_is_per_user_only(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: True)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(8))
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/llm/smart-chat", json={"query": "hi"}).status_code == 200
    blocked = client.post("/llm/smart-chat", json={"query": "hi"})
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] == "user"


def _authed_guard(monkeypatch):
    monkeypatch.setattr(
        "server.core.spend_guard.user_may_charge_company",
        lambda user_id, company_id: True,
    )
    app = FastAPI()
    app.add_middleware(SpendGuardMiddleware)

    @app.post("/companies/{company_id}/web-search")
    def web_search(company_id: int):
        return {"company_id": company_id}

    @app.get("/companies/{company_id}/competitors/digest")
    def digest(company_id: int):
        return {"company_id": company_id}

    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    return client


def test_web_search_post_is_rate_limited(monkeypatch):
    client = _authed_guard(monkeypatch)
    for _ in range(SPEND_BURST_PER_MINUTE):
        response = client.post("/companies/4/web-search")
        assert response.status_code == 200, response.text
    blocked = client.post("/companies/4/web-search")
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] in {"user", "company"}


def test_competitor_digest_get_is_rate_limited(monkeypatch):
    client = _authed_guard(monkeypatch)
    for _ in range(SPEND_BURST_PER_MINUTE):
        response = client.get("/companies/4/competitors/digest")
        assert response.status_code == 200, response.text
    blocked = client.get("/companies/4/competitors/digest")
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] in {"user", "company"}
    # The digest GET spends, so it shares the write bucket with web-search.
    assert client.post("/companies/4/web-search").status_code == 429


def test_read_cap_is_independent_on_the_middleware(monkeypatch):
    client = _guarded_app(monkeypatch, lambda user_id, company_id: True)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(4))
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/companies/4/simulate").status_code == 200
    assert client.post("/companies/4/simulate").status_code == 429
    assert client.get("/companies/4/truth/latest").status_code == 200


def test_scenario_lookup_charges_the_company_bucket(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE scenarios (id INTEGER PRIMARY KEY, company_id INTEGER)"))
        conn.execute(text("INSERT INTO scenarios (id, company_id) VALUES (9, 3)"))
    monkeypatch.setattr("server.core.spend_guard._engine", lambda: engine)
    monkeypatch.setattr(
        "server.core.spend_guard.user_may_charge_company",
        lambda user_id, company_id: company_id == 3,
    )
    assert lookup_company_id("scenarios", "9") == 3

    app = FastAPI()
    app.add_middleware(SpendGuardMiddleware)

    @app.post("/scenarios/{scenario_id}/simulate")
    def simulate(scenario_id: int):
        return {"scenario_id": scenario_id}

    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(1))
    for _ in range(SPEND_BURST_PER_MINUTE):
        response = client.post("/scenarios/9/simulate", json={})
        assert response.status_code == 200, response.text
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(2))
    blocked = client.post("/scenarios/9/simulate", json={})
    assert blocked.status_code == 429
    assert blocked.json()["dimension"] == "company"


def test_lookup_failure_still_enforces_the_user_bucket(monkeypatch):
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("server.core.spend_guard._engine", _boom)
    app = FastAPI()
    app.add_middleware(SpendGuardMiddleware)

    @app.post("/scenarios/{scenario_id}/simulate")
    def simulate(scenario_id: int):
        return {"ok": True}

    client = TestClient(app)
    client.cookies.set(AUTH_COOKIE_NAME, _cookie(6))
    for _ in range(SPEND_BURST_PER_MINUTE):
        assert client.post("/scenarios/9/simulate", json={}).status_code == 200
    assert client.post("/scenarios/9/simulate", json={}).status_code == 429


def test_membership_sql_recognizes_owner_and_ignores_a_stranger(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE companies (id INTEGER PRIMARY KEY, user_id INTEGER)"))
        conn.execute(text(
            "CREATE TABLE workspace_members (company_id INTEGER, user_id INTEGER, status VARCHAR)"
        ))
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, is_email_verified BOOLEAN)"))
        conn.execute(text("INSERT INTO companies (id, user_id) VALUES (1, 10), (2, 20)"))
        conn.execute(text(
            "INSERT INTO workspace_members (company_id, user_id, status) VALUES (2, 11, 'active')"
        ))
    monkeypatch.setattr("server.core.spend_guard._engine", lambda: engine)
    assert user_may_charge_company(10, 1) is True
    assert user_may_charge_company(11, 2) is True
    assert user_may_charge_company(10, 2) is False


def test_idle_ip_buckets_are_evicted():
    store = {}
    spend_burst_limited(["ip:203.0.113.5:write"], limit=20, now=0.0, store=store)
    spend_burst_limited(["ip:203.0.113.6:write"], limit=20, now=10.0, store=store)
    spend_burst_limited(["ip:203.0.113.7:write"], limit=20, now=69.0, store=store)
    assert "ip:203.0.113.5:write" not in store
    assert "ip:203.0.113.6:write" in store
    assert store["ip:203.0.113.7:write"] == [69.0]


def _http_scope(path: str, headers: list[tuple[bytes, bytes]]):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }


def _send_once(scope, headers, body: bytes):
    reads = {"n": 0}
    forwarded = {"called": False}

    async def app(inner_scope, receive, send):
        forwarded["called"] = True
        await receive()
        response_started = False

        async def send_ok(message):
            nonlocal response_started
            response_started = True

        from fastapi.responses import JSONResponse
        await JSONResponse({"ok": True})(inner_scope, receive, send)

    guard = SpendGuardMiddleware(app)

    async def receive():
        reads["n"] += 1
        return {"type": "http.request", "body": body, "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    asyncio.run(guard(scope, receive, send))
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    return status, reads["n"], forwarded["called"]


def test_large_body_without_a_token_is_rejected_before_it_is_read():
    payload = b"x" * (MAX_BUFFERED_BODY_BYTES + 50)
    scope = _http_scope(
        "/truth-scan/from-dataset",
        [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
        ],
    )
    status, reads, forwarded = _send_once(scope, scope["headers"], payload)
    assert status == 401
    assert reads == 0
    assert forwarded is False


def test_over_cap_authed_body_is_413_and_is_not_buffered():
    payload = b"y" * (MAX_BUFFERED_BODY_BYTES + 50)
    token = _cookie(1)
    scope = _http_scope(
        "/truth-scan/from-dataset",
        [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
            (b"cookie", f"{AUTH_COOKIE_NAME}={token}".encode()),
        ],
    )
    status, reads, forwarded = _send_once(scope, scope["headers"], payload)
    assert status == 413
    assert reads == 0
    assert forwarded is False


def test_streamed_body_over_the_cap_is_413_without_reaching_the_app():
    """No Content-Length. The guard stops once the buffered total crosses 1 MB."""
    chunk = b"z" * (MAX_BUFFERED_BODY_BYTES + 8)
    token = _cookie(1)
    scope = _http_scope(
        "/truth-scan/from-dataset",
        [
            (b"content-type", b"application/json"),
            (b"cookie", f"{AUTH_COOKIE_NAME}={token}".encode()),
        ],
    )
    status, reads, forwarded = _send_once(scope, scope["headers"], chunk)
    assert status == 413
    assert reads == 1
    assert forwarded is False


def test_app_registers_the_spend_guard():
    from server.main import app

    names = [middleware.cls.__name__ for middleware in app.user_middleware]
    assert "SpendGuardMiddleware" in names
