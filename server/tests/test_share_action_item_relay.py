"""POST /companies/{id}/share-action-item must not be an open mail relay.

Express strips the /api prefix, so the browser calls
/api/companies/{id}/share-action-item and FastAPI serves this route.
A signed-in user may email an action item for a company they can access.
They may not email arbitrary recipients without a per-user cap, and they
may not email another company's item. No session is 401.

Counters are in-process. A limiter error denies the send (fail closed).
Logs must not contain the recipient address or a client IP.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api import decisions
from server.core.db import get_db
from server.core.security import get_current_user

OWNER = SimpleNamespace(
    id=1, email="owner@example.com", is_email_verified=False,
    is_platform_admin=False, role="user",
)
OTHER = SimpleNamespace(
    id=2, email="other@example.com", is_email_verified=False,
    is_platform_admin=False, role="user",
)
COMPANY_B = 20


@pytest.fixture(autouse=True)
def _reset_share_counters():
    decisions._SHARE_SENDS.clear()
    yield
    decisions._SHARE_SENDS.clear()


@pytest.fixture(autouse=True)
def _no_platform_admin(monkeypatch):
    monkeypatch.setattr("server.core.config.settings.ADMIN_MASTER_EMAIL", "")


def _db_for(owner_id: int, company_id: int = 10):
    db = MagicMock()
    company = SimpleNamespace(id=company_id, user_id=owner_id, name="Acme")

    def query(model):
        result = MagicMock()
        if getattr(model, "__name__", "") == "Company":
            result.filter.return_value.first.return_value = company
        else:
            result.filter.return_value.first.return_value = None
        return result

    db.query.side_effect = query
    return db


def _client(db, user=None) -> TestClient:
    app = FastAPI()
    app.include_router(decisions.router)
    app.dependency_overrides[get_db] = lambda: db
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _body(email="friend@example.com", **overrides):
    payload = {
        "to_email": email,
        "subject": "Action item",
        "content_type": "playbook_item",
        "content_data": {"action": "Cut burn"},
        "personal_note": "Please review",
    }
    payload.update(overrides)
    return payload


def _patch_mailer(monkeypatch):
    calls = []

    def send(**kwargs):
        calls.append(kwargs)
        return {"success": True, "message_id": "msg-1"}

    monkeypatch.setattr("server.email.service._send_email_sync", send)
    monkeypatch.setattr(
        "server.email.service.get_transactional_from_email",
        lambda: "FounderConsole <noreply@founderconsole.ai>",
    )
    return calls


def test_limits_are_fixed_code_constants():
    assert decisions.SHARE_SENDS_PER_HOUR == 10
    assert decisions.SHARE_SEND_WINDOW_SECONDS == 3600
    assert decisions.SHARE_DISTINCT_RECIPIENTS_PER_DAY == 5
    assert decisions.SHARE_RECIPIENT_WINDOW_SECONDS == 86400
    source = open(decisions.__file__, encoding="utf-8").read()
    assert "SHARE_SENDS_PER_HOUR = 10" in source
    assert "getenv" not in source
    assert "os.environ" not in source


def test_share_limit_is_enforced(monkeypatch):
    """Ten sends per hour, five distinct recipients per day. The next one is 429 and is not mailed."""
    calls = _patch_mailer(monkeypatch)
    client = _client(_db_for(OWNER.id), OWNER)
    path = "/companies/10/share-action-item"

    for index in range(decisions.SHARE_DISTINCT_RECIPIENTS_PER_DAY):
        resp = client.post(path, json=_body(f"person{index}@example.com"))
        assert resp.status_code == 200, resp.text

    sixth = client.post(path, json=_body("person6@example.com"))
    assert sixth.status_code == 429, sixth.text
    assert sixth.json()["detail"] == "Too many share emails"
    assert len(calls) == decisions.SHARE_DISTINCT_RECIPIENTS_PER_DAY
    assert "person6@example.com" not in sixth.text

    # The same recipient is not a new distinct address, so it still sends.
    repeat = client.post(path, json=_body("person0@example.com"))
    assert repeat.status_code == 200, repeat.text

    # Case differs, recipient does not.
    same = client.post(path, json=_body("Person0@Example.com"))
    assert same.status_code == 200, same.text

    while len(calls) < decisions.SHARE_SENDS_PER_HOUR:
        more = client.post(path, json=_body("person0@example.com"))
        assert more.status_code == 200, more.text

    blocked = client.post(path, json=_body("person0@example.com"))
    assert blocked.status_code == 429, blocked.text
    assert len(calls) == decisions.SHARE_SENDS_PER_HOUR

    # Another user has their own bucket.
    other = _client(_db_for(OTHER.id, company_id=11), OTHER)
    allowed = other.post("/companies/11/share-action-item", json=_body("person6@example.com"))
    assert allowed.status_code == 200, allowed.text
    assert len(calls) == decisions.SHARE_SENDS_PER_HOUR + 1


def test_rejected_send_does_not_extend_the_window_and_the_window_expires():
    store: dict = {}
    for _ in range(decisions.SHARE_SENDS_PER_HOUR):
        decisions.claim_share_send(1, "a@example.com", now=0, store=store)
    with pytest.raises(decisions.ShareSendLimited):
        decisions.claim_share_send(1, "a@example.com", now=1, store=store)
    assert len(store[1]) == decisions.SHARE_SENDS_PER_HOUR

    for index in range(decisions.SHARE_DISTINCT_RECIPIENTS_PER_DAY):
        decisions.claim_share_send(2, f"u{index}@example.com", now=0, store=store)
    with pytest.raises(decisions.ShareSendLimited):
        decisions.claim_share_send(2, "new@example.com", now=10, store=store)
    # Same recipient is still inside the daily distinct cap.
    decisions.claim_share_send(2, "u0@example.com", now=10, store=store)

    # An hour later the send cap has aged out. A day later a new recipient has too.
    decisions.claim_share_send(1, "a@example.com", now=decisions.SHARE_SEND_WINDOW_SECONDS, store=store)
    decisions.claim_share_send(2, "new@example.com", now=decisions.SHARE_RECIPIENT_WINDOW_SECONDS, store=store)

    recorded = " ".join(item[1] for events in store.values() for item in events)
    assert "a@example.com" not in recorded
    assert "@" not in recorded


def test_limit_check_failure_does_not_send(monkeypatch, caplog):
    calls = _patch_mailer(monkeypatch)

    class Boom(dict):
        def get(self, *_args, **_kwargs):
            raise RuntimeError("mailbox person@example.com from 203.0.113.5")

    monkeypatch.setattr(decisions, "_SHARE_SENDS", Boom())
    client = _client(_db_for(OWNER.id), OWNER)
    with caplog.at_level(logging.ERROR):
        resp = client.post("/companies/10/share-action-item", json=_body("person@example.com"))

    assert resp.status_code == 429, resp.text
    assert calls == []
    assert "person@example.com" not in caplog.text
    assert "203.0.113.5" not in caplog.text


def test_other_company_action_item_is_forbidden(monkeypatch):
    calls = _patch_mailer(monkeypatch)
    for _ in range(decisions.SHARE_SENDS_PER_HOUR):
        decisions.claim_share_send(OWNER.id, "a@example.com", now=0)

    client = _client(_db_for(OTHER.id, company_id=COMPANY_B), OWNER)
    resp = client.post(f"/companies/{COMPANY_B}/share-action-item", json=_body("victim@example.com"))

    assert resp.status_code == 403, resp.text
    assert calls == []


def test_missing_company_is_404_and_does_not_send(monkeypatch):
    calls = _patch_mailer(monkeypatch)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    resp = _client(db, OWNER).post("/companies/99/share-action-item", json=_body())
    assert resp.status_code == 404, resp.text
    assert calls == []


def test_unauthenticated_share_is_401(monkeypatch):
    calls = _patch_mailer(monkeypatch)
    db = MagicMock()
    resp = _client(db).post("/companies/10/share-action-item", json=_body("victim@example.com"))
    assert resp.status_code == 401, resp.text
    assert calls == []
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_bad_email_and_oversized_message_are_rejected(monkeypatch):
    calls = _patch_mailer(monkeypatch)
    client = _client(_db_for(OWNER.id), OWNER)
    path = "/companies/10/share-action-item"

    invalid = client.post(path, json=_body("not-an-email"))
    assert invalid.status_code == 422, invalid.text

    newline = client.post(path, json=_body(subject="Hello\nBcc: spam@example.com"))
    assert newline.status_code == 422, newline.text

    note = client.post(path, json=_body(personal_note="n" * (decisions.SHARE_MESSAGE_MAX_CHARS + 1)))
    assert note.status_code == 422, note.text

    content = client.post(
        path,
        json=_body(content_data={"action": "c" * (decisions.SHARE_CONTENT_MAX_CHARS + 1)}),
    )
    assert content.status_code == 422, content.text

    assert calls == []
    assert decisions._SHARE_SENDS == {}


def test_send_failure_is_logged_without_the_address_or_an_ip(monkeypatch, caplog):
    def explode(**kwargs):
        raise RuntimeError(f"rejected {kwargs['to']} via 198.51.100.10")

    monkeypatch.setattr("server.email.service._send_email_sync", explode)
    monkeypatch.setattr(
        "server.email.service.get_transactional_from_email",
        lambda: "FounderConsole <noreply@founderconsole.ai>",
    )
    client = _client(_db_for(OWNER.id), OWNER)
    with caplog.at_level(logging.ERROR):
        resp = client.post("/companies/10/share-action-item", json=_body("person@example.com"))

    assert resp.status_code == 500, resp.text
    assert "person@example.com" not in resp.text
    assert "person@example.com" not in caplog.text
    assert "198.51.100.10" not in caplog.text
