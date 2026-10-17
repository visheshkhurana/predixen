"""FastAPI's security headers must match the Express gateway's policy."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.middleware.security_headers import SecurityHeadersMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_hsts_is_two_years_like_express():
    res = _client().get("/api/ping")
    assert res.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains; preload"


def test_csp_has_no_leftover_dev_host_entries():
    csp = _client().get("/api/ping").headers["Content-Security-Policy"]
    assert "replit" not in csp
    assert "ws:" not in csp.split() and "wss:" not in csp.split()
