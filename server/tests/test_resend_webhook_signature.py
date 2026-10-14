"""Svix verification for both Resend receivers.

    POST /api/notifications/resend-webhook
    POST /api/email-tracking/webhooks/resend

Neither route has a session. With RESEND_WEBHOOK_SECRET unset the receiver
returns 503 and writes nothing — including when NODE_ENV/ENVIRONMENT says
production. With the secret set, a missing, wrong, or stale signature is 401
and writes nothing. A fresh v1 signature is 200 and writes one row.
"""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import email_tracking as email_tracking_api
from server.api import notifications as notifications_api
from server.core.db import get_db
from server.services import resend_webhook

SECRET = "whsec_" + base64.b64encode(b"test-signing-key-32-bytes-long!!").decode()
OTHER = "whsec_" + base64.b64encode(b"another-key-another-key-another!").decode()
EVENT = {"type": "email.delivered", "data": {"email_id": "msg_1", "to": ["a@example.com"]}}

NOTIFICATIONS_PATH = "/api/notifications/resend-webhook"
EMAIL_TRACKING_PATH = "/api/email-tracking/webhooks/resend"
RECEIVERS = ["notifications", "email-tracking"]


def _signed_headers(
    body: bytes,
    secret: str = SECRET,
    ts: int | None = None,
    *,
    prefix: str = "svix",
) -> dict:
    ts = int(time.time()) if ts is None else ts
    sig = resend_webhook.sign(secret, "msg_1", str(ts), body)
    return {
        f"{prefix}-id": "msg_1",
        f"{prefix}-timestamp": str(ts),
        f"{prefix}-signature": f"v1,{sig}",
    }


def _db() -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _wire(monkeypatch, receiver: str):
    """Mount one receiver. Notifications takes the session via Depends; email
    tracking calls next(get_db()) after the signature check."""
    db = _db()
    if receiver == "notifications":
        app = FastAPI()
        app.include_router(notifications_api.router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: db
        return TestClient(app), NOTIFICATIONS_PATH, db

    monkeypatch.setattr(email_tracking_api, "get_db", lambda: iter([db]))
    app = FastAPI()
    app.include_router(email_tracking_api.router, prefix="/api")
    return TestClient(app), EMAIL_TRACKING_PATH, db


def _post(client, path: str, body: bytes, headers: dict | None = None):
    return client.post(
        path,
        content=body,
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def _clear_env(monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


# --- verifier ----------------------------------------------------------------


def test_verify_accepts_valid_and_rejects_tampered_body():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    assert resend_webhook.verify(SECRET, headers, body)
    assert not resend_webhook.verify(SECRET, headers, body + b" ")


def test_verify_rejects_stale_future_and_wrong_secret():
    body = json.dumps(EVENT).encode()
    now = 1_700_000_000
    assert resend_webhook.verify(SECRET, _signed_headers(body, ts=now), body, now=now)
    assert resend_webhook.verify(
        SECRET,
        _signed_headers(body, ts=now - resend_webhook.TOLERANCE_SECONDS),
        body,
        now=now,
    )
    assert not resend_webhook.verify(
        SECRET,
        _signed_headers(body, ts=now - resend_webhook.TOLERANCE_SECONDS - 1),
        body,
        now=now,
    )
    assert not resend_webhook.verify(
        SECRET,
        _signed_headers(body, ts=now + resend_webhook.TOLERANCE_SECONDS + 1),
        body,
        now=now,
    )
    assert not resend_webhook.verify(SECRET, _signed_headers(body, secret=OTHER, ts=now), body, now=now)


def test_verify_accepts_any_matching_v1_and_ignores_a_short_bogus_one():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    headers["svix-signature"] = "v1,bogus v0,also-ignored " + headers["svix-signature"]
    assert resend_webhook.verify(SECRET, headers, body)


def test_verify_accepts_standard_webhooks_header_aliases_and_mixed_case():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body, prefix="webhook")
    assert resend_webhook.verify(SECRET, headers, body)
    titled = {key.title(): value for key, value in _signed_headers(body).items()}
    assert resend_webhook.verify(SECRET, titled, body)


@pytest.mark.parametrize("missing", ["svix-id", "svix-timestamp", "svix-signature"])
def test_verify_rejects_a_missing_header(missing):
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    del headers[missing]
    assert not resend_webhook.verify(SECRET, headers, body)


def test_verify_returns_false_for_a_secret_that_is_not_base64():
    body = json.dumps(EVENT).encode()
    assert not resend_webhook.verify("whsec_not base64!!", _signed_headers(body), body)


def test_verify_rejects_a_non_integer_timestamp():
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    headers["svix-timestamp"] = "not-a-number"
    assert not resend_webhook.verify(SECRET, headers, body)


def test_webhook_secret_and_production_flag(monkeypatch):
    _clear_env(monkeypatch)
    assert resend_webhook.webhook_secret() == ""
    assert resend_webhook.is_production() is False

    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", f"  {SECRET}  ")
    assert resend_webhook.webhook_secret() == SECRET

    monkeypatch.setenv("ENVIRONMENT", "production")
    assert resend_webhook.is_production() is True

    # NODE_ENV wins, matching server.core.config.Settings.
    monkeypatch.setenv("NODE_ENV", "development")
    assert resend_webhook.is_production() is False
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert resend_webhook.is_production() is True


# --- missing secret: 503, no row, checked before the body is parsed ---------


@pytest.mark.parametrize("receiver", RECEIVERS)
@pytest.mark.parametrize(
    "env",
    [
        {},
        {"ENVIRONMENT": "production"},
        {"NODE_ENV": "production", "ENVIRONMENT": "development"},
    ],
)
def test_receiver_fails_closed_when_secret_unset(monkeypatch, receiver, env):
    _clear_env(monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, json.dumps(EVENT).encode())

    assert resp.status_code == 503, (receiver, env, resp.status_code, resp.text)
    assert resp.json()["detail"] == "RESEND_WEBHOOK_SECRET is not configured"
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_unset_secret_is_checked_before_the_body_is_parsed(monkeypatch, receiver):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NODE_ENV", "production")
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, b"not json")

    assert resp.status_code == 503, (receiver, resp.status_code, resp.text)
    db.add.assert_not_called()


def test_email_tracking_does_not_open_a_session_when_secret_unset(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")

    def _explode():
        raise AssertionError("get_db was called before the signature check")

    monkeypatch.setattr(email_tracking_api, "get_db", _explode)
    app = FastAPI()
    app.include_router(email_tracking_api.router, prefix="/api")
    resp = _post(TestClient(app), EMAIL_TRACKING_PATH, b"not json")
    assert resp.status_code == 503


# --- bad or missing signature: 401, no row ----------------------------------


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_receiver_rejects_unsigned_when_secret_set(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("NODE_ENV", "production")
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, json.dumps(EVENT).encode())

    assert resp.status_code == 401, (receiver, resp.status_code, resp.text)
    assert resp.json()["detail"] == "Invalid webhook signature"
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("receiver", RECEIVERS)
@pytest.mark.parametrize(
    "tamper",
    ["wrong-secret", "stale-timestamp", "future-timestamp", "tampered-body", "unparseable-timestamp"],
)
def test_receiver_rejects_bad_signature(monkeypatch, receiver, tamper):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()
    now = int(time.time())

    if tamper == "wrong-secret":
        headers = _signed_headers(body, secret=OTHER)
    elif tamper == "stale-timestamp":
        headers = _signed_headers(body, ts=now - resend_webhook.TOLERANCE_SECONDS - 5)
    elif tamper == "future-timestamp":
        headers = _signed_headers(body, ts=now + resend_webhook.TOLERANCE_SECONDS + 5)
    elif tamper == "tampered-body":
        headers = _signed_headers(body)
        body = body + b" "
    else:
        headers = _signed_headers(body)
        headers["svix-timestamp"] = "not-a-number"

    client, path, db = _wire(monkeypatch, receiver)
    resp = _post(client, path, body, headers)

    assert resp.status_code == 401, (receiver, tamper, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("missing", ["svix-id", "svix-timestamp", "svix-signature"])
def test_receiver_rejects_a_request_missing_any_svix_header(monkeypatch, missing):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()
    headers = _signed_headers(body)
    del headers[missing]
    client, path, db = _wire(monkeypatch, "notifications")

    resp = _post(client, path, body, headers)

    assert resp.status_code == 401, (missing, resp.status_code, resp.text)
    db.add.assert_not_called()


# --- valid signature: 200 and one row ---------------------------------------


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_receiver_accepts_valid_signature_and_writes_one_row(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("NODE_ENV", "production")
    body = json.dumps(EVENT).encode()
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, body, _signed_headers(body))

    assert resp.status_code == 200, (receiver, resp.status_code, resp.text)
    assert resp.json() == {"status": "ok"}
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_receiver_accepts_webhook_prefixed_headers(monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()
    client, path, db = _wire(monkeypatch, "email-tracking")

    resp = _post(client, path, body, _signed_headers(body, prefix="webhook"))

    assert resp.status_code == 200, resp.text
    db.add.assert_called_once()


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_signed_body_that_is_not_json_is_400(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = b"not json"
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, body, _signed_headers(body))

    assert resp.status_code == 400, (receiver, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_signed_json_that_is_not_an_object_is_400(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = b"[1, 2, 3]"
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, body, _signed_headers(body))

    assert resp.status_code == 400, (receiver, resp.status_code, resp.text)
    db.add.assert_not_called()
