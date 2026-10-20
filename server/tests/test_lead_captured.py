"""Server-side lead_captured: payload shape, best-effort send, always queued."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.api.leads import (
    LEAD_CAPTURED_HOSTS,
    LEAD_CAPTURED_PLANS,
    LEAD_CAPTURED_PROPERTIES,
    LEAD_CAPTURED_SOURCE_PAGE_OTHER,
    LEAD_CAPTURED_SOURCE_PAGES,
    LEAD_CAPTURED_SOURCES,
    LeadCreate,
    _LEAD_CAPTURED_FINANCIAL_KEYS,
    _emit_lead_captured,
    _lead_distinct_id,
    create_lead,
)


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


_request_seq = 0


class _Request:
    def __init__(self, host="founderconsole.ai"):
        global _request_seq
        _request_seq += 1
        self.headers = _Headers({"host": host})
        self.url = type("U", (), {"hostname": host.split(":")[0]})()
        self.client = type("C", (), {"host": f"203.0.113.{_request_seq}"})()


from server.services import posthog as posthog_svc


class _FakeUrlOpen:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status":"ok"}'


def test_distinct_id_is_stable_and_not_the_email():
    a = _lead_distinct_id("Founder@Example.com")
    b = _lead_distinct_id("founder@example.com ")
    assert a == b
    assert a.startswith("lead:")
    assert "founder@example.com" not in a


def test_emit_mirrors_location_and_source_without_runway():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        plan="runway-calculator",
        source_page="/tools/runway-calculator",
        runway_months="4",
        runway_date="2027-03-01",
        monthly_burn="40000",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
        capture.assert_called_once()
        event, distinct_id, properties = capture.call_args.args
        assert event == "lead_captured"
        assert distinct_id.startswith("optin:")
        assert distinct_id != _lead_distinct_id("founder@example.com")
        assert "founder@example.com" not in distinct_id
        assert properties["location"] == "runway-calculator"
        assert properties["source"] == "runway-calculator"
        assert properties["plan"] == "runway-calculator"
        assert properties["source_page"] == "/tools/runway-calculator"
        assert "runway_months" not in properties
        assert "runway_date" not in properties
        assert "monthly_burn" not in properties
        assert properties["created"] is True
        assert properties["distinct_id_source"] == "anonymous"


def test_emit_uses_browser_distinct_id_when_the_client_sends_one():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        distinct_id="anon-browser",
    )
    assert data.distinct_id == "anon-browser"
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
        event, distinct_id, properties = capture.call_args.args
        assert event == "lead_captured"
        assert distinct_id == "anon-browser"
        assert properties["distinct_id_source"] == "browser"


def test_emit_uses_anonymous_id_for_email_or_overlong_distinct_id():
    emailed = LeadCreate(email="founder@example.com", distinct_id="founder@example.com")
    too_long = LeadCreate(email="founder@example.com", distinct_id="x" * 201)
    blank = LeadCreate(email="founder@example.com", distinct_id="   ")
    assert emailed.distinct_id is None
    assert too_long.distinct_id is None
    assert blank.distinct_id is None
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(emailed, created=True)
        distinct_id = capture.call_args.args[1]
        assert distinct_id.startswith("optin:")
        assert distinct_id != _lead_distinct_id("founder@example.com")
        assert capture.call_args.args[2]["distinct_id_source"] == "anonymous"


def test_emit_omits_runway_when_absent():
    data = LeadCreate(email="founder@example.com", source="website")
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=False)
        properties = capture.call_args.args[2]
        assert "runway_months" not in properties
        assert properties["location"] == "website"
        assert properties["created"] is False


def test_emit_never_raises():
    data = LeadCreate(email="founder@example.com", source="runway-calculator")
    with patch("server.api.leads.posthog_capture", side_effect=RuntimeError("down")):
        _emit_lead_captured(data, created=True)


def test_capture_posts_event_without_identify():
    captured = {}

    def fake_urlopen(req, timeout=5):
        captured["url"] = req.full_url
        captured["body"] = req.data
        return _FakeUrlOpen(200)

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=fake_urlopen):
        assert posthog_svc.capture("lead_captured", "lead:abc", {"location": "runway-calculator"})

    import json

    body = json.loads(captured["body"])
    assert captured["url"].endswith("/capture/")
    assert body["event"] == "lead_captured"
    assert body["distinct_id"] == "lead:abc"
    assert body["properties"]["location"] == "runway-calculator"
    assert body["properties"]["$process_person_profile"] is False
    assert body["properties"]["$lib"] == "founderconsole-server"
    assert "identify" not in body


def test_capture_swallows_network_errors():
    def boom(*args, **kwargs):
        raise TimeoutError("slow")

    with patch.object(posthog_svc.urllib.request, "urlopen", side_effect=boom):
        assert posthog_svc.capture("lead_captured", "lead:abc") is False


def test_create_lead_queues_capture_after_commit():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
        runway_months="6",
        runway_date="2027-03-01",
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None

    result = create_lead(data, background, _Request(), db)

    assert result == {"status": "ok"}
    db.commit.assert_called_once()
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert _emit_lead_captured in queued


def test_create_lead_keeps_browser_distinct_id_for_the_queued_emit():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
        distinct_id="anon-browser",
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None

    create_lead(data, background, _Request(), db)

    emit_call = next(
        call for call in background.add_task.call_args_list if call.args[0] is _emit_lead_captured
    )
    assert emit_call.args[1].distinct_id == "anon-browser"


def test_create_lead_emits_on_repeat_submission():
    existing = MagicMock()
    existing.consent_status = None
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing

    result = create_lead(data, background, _Request(), db)

    assert result == {"status": "ok"}
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert _emit_lead_captured in queued


def test_create_lead_does_not_emit_when_commit_fails():
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    import pytest

    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        consent=True,
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    db.commit.side_effect = SQLAlchemyError("down")

    with pytest.raises(HTTPException) as exc:
        create_lead(data, background, _Request(), db)

    assert exc.value.status_code == 503
    background.add_task.assert_not_called()


# Founder figures that must not be lead_captured keys. Tool slugs such as
# runway-calculator and burn-multiple are allow-listed values, not these keys.
_FOUNDER_FINANCIAL_KEYS = {
    "arr",
    "burn",
    "burn_rate",
    "cash",
    "cash_balance",
    "cash_on_hand",
    "cash_remaining",
    "expenses",
    "gross_burn",
    "growth",
    "growth_rate",
    "monthly_burn",
    "monthly_expenses",
    "monthly_revenue",
    "mrr",
    "net_burn",
    "notes",
    "revenue",
    "runway",
    "runway_date",
    "runway_months",
    "runway_months_p50",
    "cashBalance",
    "monthly-revenue",
}


def test_property_allow_list_excludes_founder_financials():
    assert _FOUNDER_FINANCIAL_KEYS <= _LEAD_CAPTURED_FINANCIAL_KEYS | {
        "runway_months_p50",
        "cashBalance",
        "monthly-revenue",
    }
    assert LEAD_CAPTURED_PROPERTIES.isdisjoint(_LEAD_CAPTURED_FINANCIAL_KEYS)
    assert LEAD_CAPTURED_PROPERTIES.isdisjoint(_FOUNDER_FINANCIAL_KEYS)
    for key in ("runway_months", "runway", "cash", "burn", "revenue"):
        assert key not in LEAD_CAPTURED_PROPERTIES


def test_emitted_properties_never_contain_runway_months():
    notes = (
        "Cash 100000, revenue 20000, expenses 60000, net burn 40000, "
        "runway 4 months until 2027-03-01"
    )
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        plan="runway-calculator",
        runway_months="4",
        runway_date="2027-03-01",
        monthly_burn="40000",
        notes=notes,
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
    properties = capture.call_args.args[2]
    assert set(properties) <= set(LEAD_CAPTURED_PROPERTIES)
    assert _FOUNDER_FINANCIAL_KEYS.isdisjoint(properties)
    assert {"runway_months", "runway", "cash", "burn", "revenue", "notes"}.isdisjoint(properties)
    values = {str(value) for value in properties.values()}
    assert {"4", "2027-03-01", "40000", "20000", "60000", notes, "100000"}.isdisjoint(values)
    blob = " ".join(values)
    for token in (
        "runway_months",
        "runway_date",
        "monthly_burn",
        "cash_on_hand",
        "monthly_revenue",
        "net_burn",
        "40000",
        "20000",
        "60000",
        "100000",
        "2027-03-01",
        notes,
    ):
        assert token not in blob
    assert properties["plan"] == "runway-calculator"
    assert properties["source"] == "runway-calculator"


def test_post_does_not_forward_founder_financial_fields():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api.leads import get_db, router

    notes = "Cash 500000, revenue 25000, burn 40000, runway 8 months"
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    app = FastAPI()
    app.include_router(router)

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    with patch("server.api.leads.posthog_capture") as capture:
        response = client.post(
            "/leads",
            json={
                "email": "figures@example.com",
                "source": "runway-calculator",
                "source_page": "/tools/runway-calculator",
                "plan": "runway-calculator",
                "consent": True,
                "runway_months": "8",
                "runway_date": "2027-06-01",
                "monthly_burn": "40000",
                "notes": notes,
                "cash": "500000",
                "burn": "40000",
                "revenue": "25000",
                "runway": "8",
                "cash_on_hand": "500000",
                "monthly_revenue": "25000",
                "net_burn": "40000",
            },
            headers={"x-forwarded-host": "founderconsole.ai"},
        )

    assert response.status_code == 200, response.text
    capture.assert_called_once()
    properties = capture.call_args.args[2]
    assert set(properties) <= set(LEAD_CAPTURED_PROPERTIES)
    assert _FOUNDER_FINANCIAL_KEYS.isdisjoint(properties)
    blob = " ".join(str(value) for value in properties.values())
    for token in ("500000", "25000", "40000", "2027-06-01", notes, "runway_months", "cash", "revenue"):
        assert token not in blob
    assert properties["source"] == "runway-calculator"
    assert properties["host"] == "founderconsole.ai"
    lead = db.add.call_args.args[0]
    assert lead.notes == notes


def test_emit_drops_unknown_plan():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator",
        plan="enterprise-secret",
        runway_months="9",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
    properties = capture.call_args.args[2]
    assert "plan" not in properties
    assert "enterprise-secret" not in " ".join(str(value) for value in properties.values())
    assert "runway_months" not in properties

    numbered = LeadCreate(
        email="founder@example.com",
        source="website",
        source_page="/tools/runway-calculator",
        plan="18",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(numbered, created=True)
    assert "plan" not in capture.call_args.args[2]


def test_emit_normalizes_unknown_source_page():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator?runway_months=4&cash=100000",
        plan="runway-calculator",
        runway_months="4",
    )
    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(data, created=True)
    properties = capture.call_args.args[2]
    assert properties["source_page"] == LEAD_CAPTURED_SOURCE_PAGE_OTHER
    assert "runway_months" not in properties["source_page"]
    assert "100000" not in properties["source_page"]
    assert "?" not in properties["source_page"]

    for page in (
        "https://founderconsole.ai/tools/runway-calculator",
        "/tools/runway-calculator/",
        "/admin/leads",
        "/tools/not-a-calculator",
    ):
        leaked = LeadCreate(
            email="founder@example.com",
            source="website",
            source_page=page,
            plan="not-a-plan",
        )
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(leaked, created=False)
        sent = capture.call_args.args[2]
        assert sent["source_page"] == "other"
        assert page not in sent["source_page"]
        assert "plan" not in sent


def test_emit_keeps_each_known_lead_form_plan_and_path():
    for plan, page in (
        ("runway-calculator", "/tools/runway-calculator"),
        ("burn-multiple", "/tools/burn-multiple"),
        ("dilution", "/tools/dilution"),
        ("ltv-cac", "/tools/ltv-cac"),
        ("default-alive", "/default-alive"),
        ("survival-simulator", "/survival-simulator"),
    ):
        data = LeadCreate(
            email="founder@example.com",
            source=plan,
            source_page=f"  {page}  ",
            plan=plan,
            runway_months="12",
            monthly_burn="25000",
        )
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(data, created=True)
        properties = capture.call_args.args[2]
        assert properties["plan"] == plan
        assert properties["source_page"] == page
        assert "runway_months" not in properties
        assert "25000" not in {str(value) for value in properties.values()}


def test_allow_lists_match_the_lead_form_pages():
    root = Path(__file__).resolve().parents[2] / "client" / "src"
    plans: set[str] = set()
    pages: set[str] = set()
    sources: set[str] = set()
    for path in root.rglob("*.tsx"):
        text = path.read_text()
        if "CalculatorEmailOptIn" not in text:
            continue
        plans.update(re.findall(r'\bplan="([^"]+)"', text))
        pages.update(re.findall(r'\bsourcePage="([^"]+)"', text))
        sources.update(re.findall(r'\bsource="([^"]+)"', text))
    assert plans == set(LEAD_CAPTURED_PLANS)
    assert pages == set(LEAD_CAPTURED_SOURCE_PAGES)
    assert sources == set(LEAD_CAPTURED_PLANS)
    assert set(LEAD_CAPTURED_SOURCES) == sources | {"website"}
    assert LEAD_CAPTURED_HOSTS == frozenset({"founderconsole.ai", "www.founderconsole.ai"})
    assert LEAD_CAPTURED_SOURCE_PAGE_OTHER not in LEAD_CAPTURED_SOURCE_PAGES


def test_emit_replaces_arbitrary_source_with_other():
    for raw in ("555-123-4567", "Jane Founder", "utm_source=newsletter"):
        data = LeadCreate(
            email="founder@example.com",
            source=raw,
            source_page="/tools/runway-calculator",
            plan="runway-calculator",
        )
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(data, created=True, host="founderconsole.ai")
        properties = capture.call_args.args[2]
        assert properties["source"] == "other"
        assert properties["location"] == "other"
        assert raw not in properties["source"]
        assert raw not in properties["location"]
        assert raw not in " ".join(str(value) for value in properties.values())


def test_emit_keeps_website_and_the_six_lead_form_sources():
    for source in (
        "website",
        "runway-calculator",
        "burn-multiple",
        "dilution",
        "ltv-cac",
        "default-alive",
        "survival-simulator",
    ):
        data = LeadCreate(
            email="founder@example.com",
            source=f"  {source}  ",
            source_page="/tools/runway-calculator",
        )
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(data, created=True, host="www.founderconsole.ai")
        properties = capture.call_args.args[2]
        assert properties["source"] == source
        assert properties["location"] == source
        assert properties["host"] == "www.founderconsole.ai"


def test_emit_restricts_host_to_the_public_site():
    data = LeadCreate(
        email="founder@example.com",
        source="website",
        source_page="/tools/runway-calculator",
    )
    for host in ("founderconsole.ai", "www.founderconsole.ai"):
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(data, created=True, host=host)
        assert capture.call_args.args[2]["host"] == host

    for host in (
        "app.founderconsole.ai",
        "staging.founderconsole.ai",
        "localhost",
        "localhost:5000",
        "founderconsole.ai:443",
        "FOUNDERCONSOLE.AI",
        "evil.example",
        "555-0100",
        "Jane Founder",
    ):
        with patch("server.api.leads.posthog_capture") as capture:
            _emit_lead_captured(data, created=True, host=host)
        sent = capture.call_args.args[2]
        assert sent["host"] == "other"
        assert host not in sent["host"]
        assert host not in " ".join(str(value) for value in sent.values())


def test_lead_captured_properties_never_include_utm_keys():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api.leads import get_db, router

    utm = {
        "utm_source": "newsletter",
        "utm_medium": "email",
        "utm_campaign": "spring-2026",
        "utm_content": "hero-cta",
        "utm_term": "runway-months",
    }
    existing = MagicMock()
    existing.consent_status = None
    for key, value in utm.items():
        setattr(existing, key, value)
    existing.tags = {"utm_source": "newsletter", "utm_campaign": "spring-2026"}
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = existing

    app = FastAPI()
    app.include_router(router)

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    with patch("server.api.leads.posthog_capture") as capture:
        response = client.post(
            "/leads",
            params=utm,
            json={
                "email": "utm-lead@example.com",
                "source": "runway-calculator",
                "source_page": "/tools/runway-calculator?utm_source=newsletter&utm_campaign=spring-2026",
                "plan": "runway-calculator",
                "consent": True,
                "notes": "utm_source=newsletter utm_campaign=spring-2026",
                **utm,
            },
            headers={"x-forwarded-host": "founderconsole.ai"},
        )

    assert response.status_code == 200, response.text
    capture.assert_called_once()
    assert capture.call_args.args[0] == "lead_captured"
    properties = capture.call_args.args[2]

    def _assert_no_utm(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                assert not str(key).lower().startswith("utm_")
                _assert_no_utm(item)
        elif isinstance(value, list):
            for item in value:
                _assert_no_utm(item)

    _assert_no_utm(properties)
    blob = " ".join(str(value) for value in properties.values())
    for value in (*utm.values(), "utm_source", "utm_campaign", "utm_medium"):
        assert value not in blob
    assert existing.utm_source == "newsletter"
    assert existing.utm_campaign == "spring-2026"
    assert properties["host"] == "founderconsole.ai"
    assert properties["source"] == "runway-calculator"
    assert properties["source_page"] == "other"


def test_successful_save_queues_exactly_one_lead_captured():
    data = LeadCreate(
        email="founder@example.com",
        source="runway-calculator",
        source_page="/tools/runway-calculator?cash=900000",
        plan="not-a-real-plan",
        consent=True,
        runway_months="6",
        runway_date="2027-03-01",
        monthly_burn="40000",
        notes="runway 6 months",
    )
    background = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None

    result = create_lead(data, background, _Request(), db)

    assert result == {"status": "ok"}
    db.commit.assert_called_once()
    lead = db.add.call_args.args[0]
    assert lead.source_page == "/tools/runway-calculator?cash=900000"
    assert lead.plan == "not-a-real-plan"
    assert lead.notes == "runway 6 months"
    queued = [call.args[0] for call in background.add_task.call_args_list]
    assert queued.count(_emit_lead_captured) == 1
    emit_call = next(call for call in background.add_task.call_args_list if call.args[0] is _emit_lead_captured)

    with patch("server.api.leads.posthog_capture") as capture:
        _emit_lead_captured(*emit_call.args[1:])
    capture.assert_called_once()
    assert capture.call_args.args[0] == "lead_captured"
    properties = capture.call_args.args[2]
    assert "runway_months" not in properties
    assert "plan" not in properties
    assert properties["source_page"] == "other"
