"""Resend (Svix) webhooks: both receivers fail CLOSED with no signing secret.

Two routes accept Resend events and both write an EmailEvent row for any body:

    POST /api/notifications/resend-webhook
    POST /api/email-tracking/webhooks/resend

Neither has a session, so the Svix signature is the only thing separating a real
Resend event from a forged one. With RESEND_WEBHOOK_SECRET unset we cannot check
it, so both refuse the request (503) rather than record it unverified. The check
runs before the body is parsed and before any DB write.
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
EVENT = {"type": "email.delivered", "data": {"email_id": "msg_1"}}

NOTIFICATIONS_PATH = "/api/notifications/resend-webhook"
EMAIL_TRACKING_PATH = "/api/email-tracking/webhooks/resend"
RECEIVERS = ["notifications", "email-tracking"]


def _signed_headers(body: bytes, secret: str = SECRET, ts: int | None = None) -> dict:
    ts = int(time.time()) if ts is None else ts
    sig = resend_webhook.sign(secret, "msg_1", str(ts), body)
    return {"svix-id": "msg_1", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


def _db() -> MagicMock:
    db = MagicMock()
    # No existing EmailEvent row, so both handlers take their insert path.
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _wire(monkeypatch, receiver: str):
    """Mount one receiver on a bare app with its DB replaced by a MagicMock.

    The two handlers reach the session differently: notifications takes it as a
    FastAPI dependency, email-tracking calls ``next(get_db())`` itself. Both end
    up holding the same mock, so "no row written" is checkable the same way.
    """
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


# --- the signature module itself -------------------------------------------


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


def test_verify_returns_false_for_a_secret_that_is_not_base64():
    """A malformed secret must refuse the event, not raise a 500."""
    body = json.dumps(EVENT).encode()
    assert not resend_webhook.verify("whsec_not base64!!", _signed_headers(body), body)


def test_webhook_secret_is_empty_when_unset_and_trimmed_when_set(monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    assert resend_webhook.webhook_secret() == ""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", f"  {SECRET}  ")
    assert resend_webhook.webhook_secret() == SECRET


# --- both receivers: unset secret is 503, and nothing is written ------------


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_receiver_fails_closed_when_secret_unset(monkeypatch, receiver):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, json.dumps(EVENT).encode())

    assert resp.status_code == 503, (receiver, resp.status_code, resp.text)
    assert "RESEND_WEBHOOK_SECRET" in resp.json()["detail"]
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_unset_secret_is_checked_before_the_body_is_parsed(monkeypatch, receiver):
    """A body that is not JSON at all still gets 503, not 400 and not 422.

    That is the ordering proof: the secret check runs before ``json.loads`` /
    ``request.json()``, so an unauthenticated caller cannot reach a parser.
    """
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    client, path, _ = _wire(monkeypatch, receiver)

    resp = _post(client, path, b"not json")

    assert resp.status_code == 503, (receiver, resp.status_code, resp.text)


# --- both receivers: a bad signature is 401, and nothing is written ---------


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_receiver_rejects_unsigned_when_secret_set(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, json.dumps(EVENT).encode())

    assert resp.status_code == 401, (receiver, resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("receiver", RECEIVERS)
@pytest.mark.parametrize(
    "tamper",
    ["wrong-secret", "stale-timestamp", "tampered-body", "unparseable-timestamp"],
)
def test_receiver_rejects_bad_signature(monkeypatch, receiver, tamper):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()

    if tamper == "wrong-secret":
        other = "whsec_" + base64.b64encode(b"another-key-another-key-another!").decode()
        headers = _signed_headers(body, secret=other)
    elif tamper == "stale-timestamp":
        headers = _signed_headers(body, ts=int(time.time()) - 3600)
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


# --- both receivers: a valid signature is 200 and writes exactly one row ----


@pytest.mark.parametrize("receiver", RECEIVERS)
def test_receiver_accepts_valid_signature_and_writes_one_row(monkeypatch, receiver):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = json.dumps(EVENT).encode()
    client, path, db = _wire(monkeypatch, receiver)

    resp = _post(client, path, body, _signed_headers(body))

    assert resp.status_code == 200, (receiver, resp.status_code, resp.text)
    assert resp.json() == {"status": "ok"}
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_notifications_signed_body_that_is_not_json_is_400(monkeypatch):
    """With the secret set and the signature valid, a malformed body is 400."""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    body = b"not json"
    client, path, db = _wire(monkeypatch, "notifications")

    resp = _post(client, path, body, _signed_headers(body))

    assert resp.status_code == 400, (resp.status_code, resp.text)
    db.add.assert_not_called()
    db.commit.assert_not_called()
