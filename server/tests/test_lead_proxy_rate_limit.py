"""Lead cap through the Express proxy path.

POST /api/leads is what the browser calls. Express mounts the proxy at /api
and rewrites ^/api to empty, so FastAPI sees POST /leads. The consent 400 is
produced on that route. The 9th call in a minute has to be 429 from
RateLimiterMiddleware before the route runs, including when the caller spoofs
X-Real-IP and the leftmost X-Forwarded-For entry.

The proxy process is the same shape as server/index.ts: trust proxy 1,
pathRewrite {"^/api": ""}, and setProxyClientIp. Uvicorn is
server-side RecordPeer with --no-proxy-headers, which is how index.ts spawns
it. A direct non-loopback peer must ignore X-Real-IP.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.middleware.peer import RecordPeer
from server.middleware.rate_limiter import (
    RateLimiterMiddleware,
    client_ip,
    lead_window_limited,
    socket_host,
)

REPO = Path(__file__).resolve().parents[2]
PROXY_JS = r"""
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const upstream = process.argv[2];
const port = Number(process.argv[3]);

function setProxyClientIp(proxyReq, req) {
  const ip = req.ip || (req.socket && req.socket.remoteAddress) || "";
  if (ip) proxyReq.setHeader("X-Real-IP", ip);
  else proxyReq.removeHeader("X-Real-IP");
}

const app = express();
app.set("trust proxy", 1);
const apiProxy = createProxyMiddleware({
  target: upstream,
  changeOrigin: true,
  pathRewrite: { "^/api": "" },
  on: {
    proxyReq: (proxyReq, req) => setProxyClientIp(proxyReq, req),
  },
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


def test_production_proxy_overwrites_x_real_ip_and_records_the_peer():
    index = (REPO / "server/index.ts").read_text()
    client_ip_ts = (REPO / "server/proxy/clientIp.ts").read_text()
    start = (REPO / "script/start-production.sh").read_text()
    assert "setProxyClientIp(proxyReq, req)" in index
    assert 'server.main:asgi_app' in index
    assert "--no-proxy-headers" in index
    assert 'pathRewrite' in index and '"^/api"' in index
    assert 'proxyReq.setHeader("X-Real-IP", ip)' in client_ip_ts
    assert "proxyReq.removeHeader(\"X-Real-IP\")" in client_ip_ts
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


def test_ninth_proxied_lead_is_429_even_when_consent_is_false(tmp_path):
    node = _ensure_node_modules(Path("/tmp/lead-proxy-modules"))
    api_port = _free_port()
    proxy_port = _free_port()
    script = tmp_path / "proxy.js"
    script.write_text(PROXY_JS)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env["DATABASE_URL"] = f"sqlite:///{tmp_path}/leadlimit.db"
    env["PYTHONUNBUFFERED"] = "1"
    api_log = tmp_path / "api.log"
    proxy_log = tmp_path / "proxy.log"
    api_handle = api_log.open("w")
    proxy_handle = proxy_log.open("w")
    api = subprocess.Popen(
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
        stdout=api_handle,
        stderr=subprocess.STDOUT,
    )
    proxy = subprocess.Popen(
        ["node", str(script), f"http://127.0.0.1:{api_port}", str(proxy_port)],
        cwd=tmp_path,
        env={**env, "NODE_PATH": str(node)},
        stdout=proxy_handle,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_ready(f"http://127.0.0.1:{api_port}/health", api, "uvicorn")
        _wait_ready(f"http://127.0.0.1:{proxy_port}/ready", proxy, "express")
        url = f"http://127.0.0.1:{proxy_port}/api/leads"
        client = "203.0.113.50"

        def lead(forwarded_for: str, real_ip: str, consent: bool):
            return _post(
                url,
                {"email": "ada@example.com", "consent": consent, "source_page": "/tools/runway-calculator"},
                {"X-Forwarded-For": forwarded_for, "X-Real-IP": real_ip},
            )

        for n in range(8):
            status, headers, body = lead("1.2.3.4, " + client, "198.51.100.77", consent=(n % 2 == 0))
            assert status == 400, (status, body, api_log.read_text(), proxy_log.read_text())
            assert json.loads(body)["detail"] == "Consent is required"
            assert _header(headers, "X-Seen-Path") == "/leads"
            assert _header(headers, "X-Real-IP-Seen") == client
            assert _header(headers, "X-Bucket-Key") == client
            assert _header(headers, "X-RateLimit-Category") == "leads"

        status, headers, body = lead("9.9.9.9, " + client, "198.51.100.99", consent=False)
        assert status == 429, (status, body, api_log.read_text(), proxy_log.read_text())
        payload = json.loads(body)
        assert "Rate limit exceeded" in payload["detail"]
        assert payload["detail"] != "Consent is required"
        assert _header(headers, "Retry-After")
        assert _header(headers, "X-Seen-Path") == ""

        status, headers, body = lead("1.2.3.4, 203.0.113.99", "198.51.100.77", consent=False)
        assert status == 400, (status, body)
        assert json.loads(body)["detail"] == "Consent is required"
        assert _header(headers, "X-Bucket-Key") == "203.0.113.99"
        assert _header(headers, "X-Seen-Path") == "/leads"
    finally:
        for proc in (proxy, api):
            if proc.poll() is None:
                proc.terminate()
        for proc in (proxy, api):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        api_handle.close()
        proxy_handle.close()


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
