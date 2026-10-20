"""Lead cap through the Express proxy path.

POST /api/leads is what the browser calls. Express mounts the proxy at /api
and rewrites ^/api to empty, so FastAPI sees POST /leads. The consent 400 is
produced on that route. Express forwards X-Real-IP unchanged. With trust
proxy 1, req.ip is the rightmost X-Forwarded-For hop, and on Railway that hop
is the shared edge. Nine clients behind that edge must not share a bucket.

X-Real-IP is the bucket only when the TCP peer is loopback. A stand-in for
Railway's edge, used only in these tests, overwrites a caller-supplied
X-Real-IP and X-Forwarded-For before Express sees them. Uvicorn is
RecordPeer with --no-proxy-headers, which is how index.ts spawns it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from server.middleware.peer import RecordPeer
from server.middleware.rate_limiter import (
    RateLimiterMiddleware,
    client_ip,
    lead_window_limited,
    socket_host,
)

REPO = Path(__file__).resolve().parents[2]
EDGE = "152.233.10.4"
PROXY_JS = r"""
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const upstream = process.argv[2];
const port = Number(process.argv[3]);
const EDGE = "152.233.10.4";

const app = express();
app.set("trust proxy", 1);

// Test stand-in for Railway's public edge, which is in front of Express.
// X-Edge-Client is the address that edge observed on its socket. Production
// server/index.ts does not do this and does not rewrite X-Real-IP.
app.use((req, _res, next) => {
  const seen = req.headers["x-edge-client"];
  if (seen) {
    req.headers["x-real-ip"] = String(seen).split(",")[0].trim();
    req.headers["x-forwarded-for"] = EDGE;
    delete req.headers["x-edge-client"];
  }
  next();
});

const apiProxy = createProxyMiddleware({
  target: upstream,
  changeOrigin: true,
  pathRewrite: { "^/api": "" },
});
app.use("/api", (req, res, next) => apiProxy(req, res, next));
app.get("/ready", (_req, res) => res.status(200).send("ok"));
app.listen(port, "127.0.0.1");
"""


def _proxy_app():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/leads")
    async def create(request: Request):
        # Stand-in for the consent 400. The limiter has to answer before this.
        key = client_ip(request.headers, socket_host(request))
        return JSONResponse(
            status_code=400,
            content={"detail": "Consent is required"},
            headers={
                "X-Seen-Path": request.url.path,
                "X-Bucket-Key": key,
                "X-Real-IP-Seen": request.headers.get("x-real-ip", ""),
            },
        )

    app.add_middleware(RateLimiterMiddleware)
    return RecordPeer(app)


proxy_asgi = _proxy_app()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _header(headers, name: str) -> str:
    value = headers.get(name)
    if value is None:
        return ""
    return str(value)


def _post(url: str, body: dict, headers: dict) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def _wait_ready(url: str, proc: subprocess.Popen, label: str) -> None:
    deadline = time.time() + 20
    last = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{label} exited {proc.returncode}: {last}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last = str(exc)
        time.sleep(0.1)
    raise RuntimeError(f"{label} did not come up: {last}")


def _ensure_node_modules(dest: Path) -> Path:
    modules = dest / "node_modules"
    express_pkg = modules / "express"
    proxy_pkg = modules / "http-proxy-middleware"
    if express_pkg.exists() and proxy_pkg.exists():
        return modules
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        ["npm", "install", "--silent", "express@4.21.2", "http-proxy-middleware@3.0.5"],
        cwd=dest,
    )
    return modules


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), super().get(key, default))


def test_production_proxy_forwards_x_real_ip_and_records_the_peer():
    index = (REPO / "server/index.ts").read_text()
    start = (REPO / "script/start-production.sh").read_text()
    assert "setProxyClientIp" not in index
    assert 'setHeader("X-Real-IP"' not in index
    assert not (REPO / "server/proxy/clientIp.ts").exists()
    assert 'server.main:asgi_app' in index
    assert "--no-proxy-headers" in index
    assert 'pathRewrite' in index and '"^/api"' in index
    assert "server.main:asgi_app" in start
    assert "--no-proxy-headers" in start
    assert "asgi_app = RecordPeer(app)" in (REPO / "server/main.py").read_text()


def test_x_real_ip_is_trusted_only_from_a_loopback_peer():
    headers = _Headers({
        "x-real-ip": "198.51.100.77",
        "x-forwarded-for": "203.0.113.50",
    })
    assert client_ip(headers, "203.0.113.8") == "203.0.113.8"
    assert client_ip(headers, "198.51.100.77") == "198.51.100.77"
    assert "198.51.100.77" != client_ip(headers, "203.0.113.8")
    for peer in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
        assert client_ip(headers, peer) == "198.51.100.77"

    direct = type(
        "R",
        (),
        {
            "headers": headers,
            "client": type("C", (), {"host": "203.0.113.8"})(),
            "scope": {"extensions": {"peer_host": "203.0.113.8"}},
        },
    )()

    assert socket_host(direct) == "203.0.113.8"
    middleware = RateLimiterMiddleware(MagicMock())
    routed = type(
        "R",
        (),
        {
            "url": type("U", (), {"path": "/leads"})(),
            "method": "POST",
            "headers": headers,
            "client": direct.client,
            "scope": direct.scope,
        },
    )()
    assert middleware._get_identifier(routed) == "203.0.113.8"
    assert middleware._get_category(routed) == ("leads", 8)


def test_lead_window_blocks_the_ninth_when_the_database_fails_open():
    middleware = RateLimiterMiddleware(MagicMock())
    store: dict[str, list[float]] = {}
    calls = {"n": 0}

    async def call_next(request):
        calls["n"] += 1
        return JSONResponse(status_code=400, content={"detail": "Consent is required"})

    def request(real_ip: str):
        return type(
            "R",
            (),
            {
                "url": type("U", (), {"path": "/leads"})(),
                "method": "POST",
                "headers": _Headers({"x-real-ip": real_ip}),
                "client": type("C", (), {"host": "127.0.0.1"})(),
                "scope": {"extensions": {"peer_host": "127.0.0.1"}},
            },
        )()

    async def run():
        with patch("server.middleware.rate_limiter._LEAD_HITS", store), patch.object(
            middleware, "_check_rate_limit", side_effect=RuntimeError("db down")
        ):
            statuses = []
            for _n in range(8):
                response = await middleware.dispatch(request("203.0.113.50"), call_next)
                statuses.append(response.status_code)
            blocked = await middleware.dispatch(request("203.0.113.50"), call_next)
            other = await middleware.dispatch(
                type(
                    "R",
                    (),
                    {
                        "url": type("U", (), {"path": "/leads"})(),
                        "method": "POST",
                        "headers": _Headers({"x-real-ip": "203.0.113.99"}),
                        "client": type("C", (), {"host": "127.0.0.1"})(),
                        "scope": {"extensions": {"peer_host": "127.0.0.1"}},
                    },
                )(),
                call_next,
            )
            return statuses, blocked, other

    statuses, blocked, other = asyncio.run(run())
    assert statuses == [400] * 8
    assert blocked.status_code == 429
    assert json.loads(blocked.body)["detail"].startswith("Rate limit exceeded")
    assert other.status_code == 400
    assert calls["n"] == 9


def test_nine_consent_true_posts_are_limited_before_the_handler(caplog):
    """Consent-true posts use the same bucket and never reach the handler on the 9th."""
    from server.api.leads import LeadCreate

    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware)
    calls = {"n": 0}

    # This module uses postponed annotations, so a local LeadCreate hint is a
    # string and FastAPI would treat it as a query param. Bind the real model
    # before the route is registered.
    def create(data: LeadCreate):
        calls["n"] += 1
        if data.consent is not True:
            raise HTTPException(status_code=400, detail="Consent is required")
        if not (data.source_page or "").strip():
            raise HTTPException(status_code=400, detail="A source page is required")
        return {"status": "ok"}

    create.__annotations__ = {"data": LeadCreate}
    app.post("/leads")(create)

    def allow_db(self, key, endpoint, limit):
        return (True, max(limit - 1, 0), 0)

    false_body = {"email": "a@example.com", "consent": False}
    true_body = {
        "email": "a@example.com",
        "consent": True,
        "source_page": "/runway-calculator",
    }
    with patch("server.middleware.rate_limiter._LEAD_HITS", {}), patch.object(
        RateLimiterMiddleware, "_check_rate_limit", allow_db
    ), caplog.at_level(logging.INFO, logger="server.middleware.rate_limiter"):
        client = TestClient(app)
        statuses = [client.post("/leads", json=false_body).status_code for _ in range(4)]
        statuses += [client.post("/leads", json=true_body).status_code for _ in range(4)]
        ninth = client.post("/leads", json=true_body)
        statuses.append(ninth.status_code)

    assert statuses == [400, 400, 400, 400, 200, 200, 200, 200, 429]
    assert calls["n"] == 8
    assert ninth.json()["detail"].startswith("Rate limit exceeded")
    keys = [
        rec.message.split("lead bucket key=", 1)[1]
        for rec in caplog.records
        if rec.message.startswith("lead bucket key=")
    ]
    assert keys == ["testclient"] * 9


def test_string_window_start_is_not_a_fail_open():
    middleware = RateLimiterMiddleware(MagicMock())

    class _Result:
        def fetchone(self):
            return (9, "2026-10-19T00:00:00")

    class _Conn:
        def execute(self, *args, **kwargs):
            return _Result()

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _Engine:
        def connect(self):
            return _Conn()

    with patch("server.middleware.rate_limiter._get_engine", return_value=_Engine()):
        allowed, remaining, retry_after = middleware._check_rate_limit("203.0.113.50", "leads", 8)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1


class _Proxy:
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.api = None
        self.proxy = None
        self.api_handle = None
        self.proxy_handle = None
        self.url = ""

    def __enter__(self):
        node = _ensure_node_modules(Path("/tmp/lead-proxy-modules"))
        api_port = _free_port()
        proxy_port = _free_port()
        script = self.tmp_path / "proxy.js"
        script.write_text(PROXY_JS)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env["DATABASE_URL"] = f"sqlite:///{self.tmp_path}/leadlimit.db"
        env["PYTHONUNBUFFERED"] = "1"
        self.api_log = self.tmp_path / "api.log"
        self.proxy_log = self.tmp_path / "proxy.log"
        self.api_handle = self.api_log.open("w")
        self.proxy_handle = self.proxy_log.open("w")
        self.api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server.tests.test_lead_proxy_rate_limit:proxy_asgi",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-proxy-headers",
            ],
            cwd=REPO,
            env=env,
            stdout=self.api_handle,
            stderr=subprocess.STDOUT,
        )
        self.proxy = subprocess.Popen(
            ["node", str(script), f"http://127.0.0.1:{api_port}", str(proxy_port)],
            cwd=self.tmp_path,
            env={**env, "NODE_PATH": str(node)},
            stdout=self.proxy_handle,
            stderr=subprocess.STDOUT,
        )
        _wait_ready(f"http://127.0.0.1:{api_port}/health", self.api, "uvicorn")
        _wait_ready(f"http://127.0.0.1:{proxy_port}/ready", self.proxy, "express")
        self.url = f"http://127.0.0.1:{proxy_port}/api/leads"
        return self

    def __exit__(self, *args):
        for proc in (self.proxy, self.api):
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (self.proxy, self.api):
            if proc is None:
                continue
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if self.api_handle is not None:
            self.api_handle.close()
        if self.proxy_handle is not None:
            self.proxy_handle.close()
        return False

    def logs(self) -> str:
        api = self.api_log.read_text() if self.api_log.exists() else ""
        proxy = self.proxy_log.read_text() if self.proxy_log.exists() else ""
        return api + "\n" + proxy

    def lead(self, headers: dict, consent: bool = False):
        return _post(
            self.url,
            {"email": "ada@example.com", "consent": consent, "source_page": "/tools/runway-calculator"},
            headers,
        )


def test_nine_clients_behind_one_edge_each_get_400(tmp_path):
    """Distinct X-Real-IP values behind 152.233.10.4 do not share a bucket."""
    with _Proxy(tmp_path) as proxy:
        for n in range(9):
            client = f"203.0.113.{10 + n}"
            status, headers, body = proxy.lead(
                {
                    "X-Real-IP": client,
                    "X-Forwarded-For": f"198.51.100.1, {EDGE}",
                },
                consent=False,
            )
            assert status == 400, (n, status, body, proxy.logs())
            assert json.loads(body)["detail"] == "Consent is required"
            assert _header(headers, "X-Seen-Path") == "/leads"
            assert _header(headers, "X-Real-IP-Seen") == client
            assert _header(headers, "X-Bucket-Key") == client
            assert _header(headers, "X-Bucket-Key") != EDGE
            assert _header(headers, "X-RateLimit-Category") == "leads"


def test_edge_x_real_ip_keeps_the_ninth_on_one_bucket(tmp_path):
    """A spoofed 9th POST is 429 when the edge sets X-Real-IP. Another network is 400."""
    client = "203.0.113.50"
    other = "198.51.100.20"
    with _Proxy(tmp_path) as proxy:
        for n in range(8):
            status, headers, body = proxy.lead(
                {
                    "X-Edge-Client": client,
                    "X-Real-IP": "198.51.100.77",
                    "X-Forwarded-For": "1.2.3.4",
                },
                consent=(n % 2 == 0),
            )
            assert status == 400, (n, status, body, proxy.logs())
            assert json.loads(body)["detail"] == "Consent is required"
            assert _header(headers, "X-Seen-Path") == "/leads"
            assert _header(headers, "X-Real-IP-Seen") == client
            assert _header(headers, "X-Bucket-Key") == client
            assert _header(headers, "X-Bucket-Key") != EDGE

        status, headers, body = proxy.lead(
            {
                "X-Edge-Client": client,
                "X-Real-IP": "203.0.113.250",
                "X-Forwarded-For": "9.9.9.9, 198.51.100.8",
            },
            consent=False,
        )
        assert status == 429, (status, body, proxy.logs())
        payload = json.loads(body)
        assert "Rate limit exceeded" in payload["detail"]
        assert payload["detail"] != "Consent is required"
        assert _header(headers, "Retry-After")
        assert _header(headers, "X-Seen-Path") == ""

        status, headers, body = proxy.lead(
            {
                "X-Edge-Client": other,
                "X-Real-IP": client,
                "X-Forwarded-For": f"9.9.9.9, {EDGE}",
            },
            consent=False,
        )
        assert status == 400, (status, body, proxy.logs())
        assert json.loads(body)["detail"] == "Consent is required"
        assert _header(headers, "X-Bucket-Key") == other
        assert _header(headers, "X-Real-IP-Seen") == other
        assert _header(headers, "X-Seen-Path") == "/leads"


def test_rejected_lead_does_not_consume_a_later_slot():
    store: dict[str, list[float]] = {}
    for n in range(8):
        blocked, _retry = lead_window_limited("203.0.113.50", now=float(n), store=store)
        assert blocked is False
    blocked, retry = lead_window_limited("203.0.113.50", now=8, store=store)
    assert blocked is True
    assert retry >= 1
    assert len(store["203.0.113.50"]) == 8
    other, _retry = lead_window_limited("203.0.113.99", now=8, store=store)
    assert other is False
