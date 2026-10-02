"""Resend (Svix) webhook signature: forged events rejected once the secret is set."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import notifications as notifications_api
from server.core.db import get_db
from server.services import resend_webhook

SECRET = "whsec_" + base64.b64encode(b"test-signing-key-32-bytes-long!!").decode()
EVENT = {"type": "email.delivered", "data": {}}


def _signed_headers(body: bytes, secret: str = SECRET, ts: int | None = None) -> dict:
    ts = int(time.time()) if ts is None else ts
    sig = resend_webhook.sign(secret, "msg_1", str(ts), body)
    return {"svix-id": "msg_1", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(notifications_api.router, prefix="/api")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _post(client, body: bytes, headers: dict | None = None):
    return client.post(
        "/api/notifications/resend-webhook",
        content=body,
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def test_verify_accepts_valid_and_rejects_tampered_body():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    assert resend_webhook.verify(SECRET, headers, body)
    assert not resend_webhook.verify(SECRET, headers, body + b" ")


def test_verify_rejects_stale_timestamp_and_wrong_secret():
    body = json.dumps(EVENT).encode()
    stale = _signed_headers(body, ts=int(time.time()) - 3600)
    assert not resend_webhook.verify(SECRET, stale, body)
    other = "whsec_" + base64.b64encode(b"another-key-another-key-another!").decode()
    assert not resend_webhook.verify(SECRET, _signed_headers(body, secret=other), body)


def test_verify_accepts_any_matching_v1_among_several_signatures():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    headers["svix-signature"] = "v1,bogus " + headers["svix-signature"]
    assert resend_webhook.verify(SECRET, headers, body)


def test_endpoint_rejects_unsigned_when_secret_set(monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    resp = _post(_client(), json.dumps(EVENT).encode())
    assert resp.status_code == 401


def test_endpoint_accepts_signed_when_secret_set(monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()
    resp = _post(_client(), body, _signed_headers(body))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_endpoint_stays_open_while_secret_unset(monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    resp = _post(_client(), json.dumps(EVENT).encode())
    assert resp.status_code == 200


def test_endpoint_rejects_non_json(monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    assert _post(_client(), b"not json").status_code == 400
