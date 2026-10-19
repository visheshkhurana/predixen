"""Consent opt-in on the public calculators.

POST /api/leads stores consent, a server timestamp, and the source page.
lead_captured includes the request host. Monthly tips stay pending: Resend is
only a transactional sender here, with no lead double opt-in to reuse.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock, patch

from server.api.leads import (
    MARKETING_OPT_IN_CONFIRMED,
    MARKETING_OPT_IN_PENDING,
    LeadCreate,
    _emit_lead_captured,
    _notes_result_html,
    _runway_email_html,
    _send_runway_email,
    create_lead,
    get_db,
    lead_may_receive_founder_tips,
    list_leads,
)
from server.core.migrations import ensure_lead_consent_columns
from server.models.lead import Lead

REPO = Path(__file__).resolve().parents[2]
OPT_IN = REPO / "client/src/components/marketing/CalculatorEmailOptIn.tsx"


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


_request_seq = 0


class _Request:
    def __init__(self, host="founderconsole.ai", forwarded=None):
        global _request_seq
        _request_seq += 1
        headers = {"host": host}
        if forwarded:
            headers["x-forwarded-host"] = forwarded
        self.headers = _Headers(headers)
        self.url = type("U", (), {"hostname": host.split(":")[0]})()
        self.client = type("C", (), {"host": f"198.51.100.{_request_seq}"})()


def _consented(**overrides) -> LeadCreate:
    payload = dict(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
        plan="runway-calculator",
    )
    payload.update(overrides)
    return LeadCreate(**payload)


def _db_for_new_lead():
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    return db


def test_opt_in_copy_is_unchecked_and_names_privacy_and_unsubscribe():
    src = OPT_IN.read_text()
    assert 'Email me this result + monthly founder finance tips' in src
    assert "useState(false)" in src
    assert "defaultChecked" not in src
    assert 'checked={consented}' in src
    assert 'disabled={sendState === "sending" || !consented}' in src
    assert 'href="/privacy"' in src
    assert "Unsubscribe any time" in src
    assert "consent: true" in src
    assert "consent_at:" in src
    assert "source_page: sourcePage" in src
    assert "host: window.location.host" in src
    assert 'trackFunnel(\n        "lead_captured"' in src or 'trackFunnel("lead_captured"' in src


def test_each_public_calculator_offers_the_opt_in_after_a_result():
    runway = (REPO / "client/src/pages/runway-calculator.tsx").read_text()
    assert runway.index('data-testid="text-runway-months"') < runway.index("<CalculatorEmailOptIn")
    assert 'sourcePage="/tools/runway-calculator"' in runway

    burn = (REPO / "client/src/pages/burn-multiple.tsx").read_text()
    assert burn.index('data-testid="text-bm-multiple"') < burn.index("<CalculatorEmailOptIn")
    assert 'visible={result.outcome !== "invalid"}' in burn
    assert 'sourcePage="/tools/burn-multiple"' in burn

    dilution = (REPO / "client/src/pages/dilution.tsx").read_text()
    assert 'visible={result.outcome !== "invalid"}' in dilution
    assert 'sourcePage="/tools/dilution"' in dilution

    ltv = (REPO / "client/src/pages/ltv-cac.tsx").read_text()
    assert "result.outcome !== \"invalid\"" in ltv
    assert 'sourcePage="/tools/ltv-cac"' in ltv

    alive = (REPO / "client/src/pages/default-alive.tsx").read_text()
    assert alive.index('data-testid="text-da-verdict"') < alive.index("<CalculatorEmailOptIn")
    assert 'sourcePage="/default-alive"' in alive

    survival = (REPO / "client/src/pages/survival-simulator.tsx").read_text()
    results_at = survival.index("{results && (")
    email_at = survival.index("<EmailResultPanel results={results} />")
    assert results_at != -1 and email_at > results_at
    assert 'sourcePage="/survival-simulator"' in survival


def test_missing_or_false_consent_is_rejected_before_save():
    background = MagicMock()
    db = _db_for_new_lead()
    for consent in (False,):
        data = _consented(consent=consent)
        with pytest.raises(HTTPException) as exc:
            create_lead(data, background, _Request(), db)
        assert exc.value.status_code == 400
    db.commit.assert_not_called()
    background.add_task.assert_not_called()


def test_missing_source_page_is_rejected():
    background = MagicMock()
    db = _db_for_new_lead()
    data = _consented(source_page="   ")
    with pytest.raises(HTTPException) as exc:
        create_lead(data, background, _Request(), db)
    assert exc.value.status_code == 400
    assert "source page" in exc.value.detail.lower()
    db.add.assert_not_called()


def test_consent_timestamp_and_source_page_are_stored_pending():
    data = _consented(consent_at=datetime(1999, 1, 1))
    background = MagicMock()
    db = _db_for_new_lead()
    before = datetime.utcnow()

    result = create_lead(data, background, _Request("founderconsole.ai"), db)

    lead = db.add.call_args.args[0]
    assert isinstance(lead, Lead)
    assert lead.consent is True
    assert lead.source_page == "/tools/runway-calculator"
    assert lead.consent_status == MARKETING_OPT_IN_PENDING
    assert lead.consent_at is not None
    assert lead.consent_at >= before
    assert lead.consent_at.year != 1999
    assert result == {"status": "ok"}
    assert "created" not in result
    assert "consent_status" not in result
    assert lead_may_receive_founder_tips(lead) is False


def test_confirmed_opt_in_is_not_downgraded_on_a_repeat_result():
    existing = MagicMock()
    existing.consent_status = MARKETING_OPT_IN_CONFIRMED
    data = _consented()
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing

    create_lead(data, background, _Request(), db)

    assert existing.consent is True
    assert existing.consent_status == MARKETING_OPT_IN_CONFIRMED
    assert existing.source_page == "/tools/runway-calculator"
    assert lead_may_receive_founder_tips(existing) is True


def test_lead_captured_includes_the_request_host():
    data = _consented(runway_months="4")
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True, host="founderconsole.ai")
    properties = capture.call_args.args[2]
    assert capture.call_args.args[0] == "lead_captured"
    assert properties["host"] == "founderconsole.ai"
    assert properties["source_page"] == "/tools/runway-calculator"
    assert properties["location"] == "runway-calculator"


def test_forwarded_host_is_what_gets_queued():
    data = _consented(runway_months="6", runway_date="2027-03-01")
    background = MagicMock()
    db = _db_for_new_lead()
    request = _Request(host="internal:8000", forwarded="founderconsole.ai, proxy.internal")

    create_lead(data, background, request, db)

    emit = next(call for call in background.add_task.call_args_list if call.args[0] is _emit_lead_captured)
    assert emit.args[3] == "founderconsole.ai"
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert _send_runway_email in queued
    assert queued.count(_send_runway_email) == 1


def test_pending_note_is_on_the_result_email_and_tips_are_not_a_second_send():
    data = _consented(runway_months="8", runway_date="June 2027", monthly_burn="$40K/mo")
    html = _runway_email_html(data)
    assert "pending" in html
    assert "Unsubscribe" in html
    assert "hello@founderconsole.ai" in html


def test_list_leads_returns_consent_fields():
    lead = MagicMock()
    lead.id = 1
    lead.email = "founder@example.com"
    lead.company = ""
    lead.plan = "runway-calculator"
    lead.source = "runway-calculator"
    lead.notes = "4 months"
    lead.consent = True
    lead.consent_at = datetime(2026, 10, 19, 12, 0, 0)
    lead.source_page = "/tools/runway-calculator"
    lead.consent_status = MARKETING_OPT_IN_PENDING
    lead.created_at = datetime(2026, 10, 19, 12, 0, 0)
    db = MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [lead]

    rows = list_leads(50, db, None)

    assert rows[0]["consent"] is True
    assert rows[0]["consent_at"] == "2026-10-19T12:00:00"
    assert rows[0]["source_page"] == "/tools/runway-calculator"
    assert rows[0]["consent_status"] == "pending"


def test_lead_consent_migration_is_idempotent():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE leads (id INTEGER PRIMARY KEY, email VARCHAR)"))
    ensure_lead_consent_columns(engine)
    ensure_lead_consent_columns(engine)
    cols = {col["name"] for col in inspect(engine).get_columns("leads")}
    assert {"consent", "consent_at", "source_page", "consent_status"} <= cols


def test_post_route_stores_consent_and_emits_host():
    app = FastAPI()
    from server.api.leads import router

    app.include_router(router)
    db = _db_for_new_lead()

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    with patch("server.api.leads.posthog_capture") as capture:
        response = client.post(
            "/leads",
            json={
                "email": "founder@example.com",
                "source": "burn-multiple",
                "source_page": "/tools/burn-multiple",
                "plan": "burn-multiple",
                "consent": True,
                "consent_at": "1999-01-01T00:00:00",
                "notes": "2.3x",
            },
            headers={"x-forwarded-host": "founderconsole.ai"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"status": "ok"}
    lead = db.add.call_args.args[0]
    assert lead.consent is True
    assert lead.source_page == "/tools/burn-multiple"
    assert lead.consent_status == "pending"
    assert capture.call_args.args[0] == "lead_captured"
    assert capture.call_args.args[2]["host"] == "founderconsole.ai"


def test_post_route_rejects_consent_false():
    app = FastAPI()
    from server.api.leads import router

    app.include_router(router)
    db = _db_for_new_lead()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    response = client.post(
        "/leads",
        json={
            "email": "founder@example.com",
            "consent": False,
            "source_page": "/tools/runway-calculator",
        },
    )
    assert response.status_code == 400
    db.add.assert_not_called()


def test_response_body_is_identical_for_new_pending_and_confirmed():
    def run(existing_status, email):
        if existing_status is None:
            db = _db_for_new_lead()
        else:
            existing = MagicMock()
            existing.consent_status = existing_status
            db = MagicMock()
            db.query.return_value.filter.return_value.one_or_none.return_value = existing
        return create_lead(_consented(email=email), MagicMock(), _Request(), db)

    new = run(None, "new-lead@example.com")
    pending = run(MARKETING_OPT_IN_PENDING, "pending-lead@example.com")
    confirmed = run(MARKETING_OPT_IN_CONFIRMED, "confirmed-lead@example.com")
    assert new == pending == confirmed == {"status": "ok"}
    assert "created" not in new
    assert "consent" not in new
    assert "consent_status" not in new


def test_four_calculators_queue_an_escaped_result_email():
    pages = {
        "burn-multiple": "/tools/burn-multiple",
        "dilution": "/tools/dilution",
        "ltv-cac": "/tools/ltv-cac",
        "default-alive": "/default-alive",
    }
    for source, page in pages.items():
        background = MagicMock()
        db = _db_for_new_lead()
        notes = f"{source} result 2 < 3 <img src=x onerror=alert(1)>"
        result = create_lead(
            _consented(
                email=f"{source}@example.com",
                source=source,
                source_page=page,
                plan=source,
                notes=notes,
            ),
            background,
            _Request(),
            db,
        )
        assert result == {"status": "ok"}
        queued = [call.args[0] for call in background.add_task.call_args_list]
        assert queued.count(_send_runway_email) == 1
        html = _notes_result_html(
            _consented(source=source, source_page=page, notes=notes)
        )
        assert "<img" not in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html
        assert "pending" in html
        assert "hello@founderconsole.ai" in html
        assert "?" not in "".join(re.findall(r'href="([^"]*)"', html))


def test_commit_failure_still_hides_the_database_error():
    data = _consented()
    background = MagicMock()
    db = _db_for_new_lead()
    db.commit.side_effect = SQLAlchemyError("down")
    with pytest.raises(HTTPException) as exc:
        create_lead(data, background, _Request(), db)
    assert exc.value.status_code == 503
    background.add_task.assert_not_called()
