"""Zoho CRM connector and CRM pipeline snapshots. No network: httpx MockTransport."""

import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.connectors import hubspot, pipedrive, zoho_crm
from server.connectors.base import ConnectorConfig, SyncResult
from server.connectors.registry import ConnectorRegistry
from server.models.company import Company
from server.models.crm_pipeline import CRMPipelineSnapshot
from server.models.financial import FinancialRecord
from server.models.user import User
from server.models.workspace import WorkspaceMember
from server.services import crm_pipeline

TODAY = datetime.now(timezone.utc).date()


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_http(monkeypatch):
    seen = []
    state = {}
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(lambda r: (seen.append(r), state["handler"](r))[1])
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)

    def install(handler):
        state["handler"] = handler
        return seen

    return install


def _zoho(**creds):
    base = {"client_id": "cid", "client_secret": "sec", "refresh_token": "rt", "access_token": "at", "dc": "in"}
    base.update(creds)
    return zoho_crm.ZohoCRMConnector(ConnectorConfig(provider_id="zoho_crm", company_id=1, credentials=base))


def _deal(id_, amount, stage, prob, closed, currency=None):
    d = {"id": id_, "Deal_Name": f"Deal {id_}", "Amount": amount, "Stage": stage, "Probability": prob,
         "Closing_Date": closed.isoformat(), "Account_Name": {"name": f"Acme {id_}", "id": "9"}}
    if currency:
        d["Currency"] = currency
    return d


DEALS = [
    _deal(1, 1000, "Qualification", 10, TODAY + timedelta(days=20)),
    _deal(2, 3000, "Proposal/Price Quote", 75, TODAY + timedelta(days=10)),
    _deal(3, 5000, "Closed Won", 100, TODAY),
    _deal(4, 2000, "Closed Lost", 0, TODAY - timedelta(days=3)),
    _deal(5, 900, "Closed-Lost to Competition", 0, TODAY - timedelta(days=60)),
    _deal(6, 400, "Qualification", 10, TODAY, currency="EUR"),
]


def _zoho_handler(deals=DEALS, org_status=200, more_pages=False):
    def handler(req):
        path = req.url.path
        if path.endswith("/oauth/v2/token"):
            return httpx.Response(200, json={"access_token": "fresh"})
        if path == "/crm/v8/org":
            return httpx.Response(org_status, json={"org": [{"company_name": "Acme Pvt", "iso_code": "INR"}]})
        if path == "/crm/v8/Deals":
            return httpx.Response(200, json={"data": deals, "info": {"more_records": more_pages}})
        if path.endswith("/actions/count"):
            return httpx.Response(200, json={"count": 42})
        return httpx.Response(404)
    return handler


# --- Zoho CRM connector ------------------------------------------------------

def test_registered_as_crm():
    assert ConnectorRegistry.get_connector_class("zoho_crm") is zoho_crm.ZohoCRMConnector


@pytest.mark.parametrize("stage,prob,status", [
    ("Closed Won", 100, "won"), ("Closed Lost", 0, "lost"), ("Closed-Lost to Competition", 0, "lost"),
    ("Negotiation", 90, "open"), ("Signed (custom)", 100, "won"), ("Closed - Dropped", 0, "lost"),
    ("Qualification", 0, "open"),
])
def test_deal_status(stage, prob, status):
    assert zoho_crm.deal_status({"Stage": stage, "Probability": prob}) == status


def test_sync_uses_user_data_centre_and_builds_snapshot(mock_http):
    seen = mock_http(_zoho_handler())
    result = _run(_zoho().sync_all())
    assert result.success, result.errors
    assert {r.url.host for r in seen} == {"www.zohoapis.in"}
    assert seen[0].headers["Authorization"] == "Zoho-oauthtoken at"

    snap = result.metadata["crm_pipeline"]
    assert snap["currency"] == "INR"
    assert snap["open_count"] == 2 and snap["open_value"] == 4000
    assert snap["weighted_value"] == 1000 * 0.1 + 3000 * 0.75
    assert snap["won_count_30d"] == 1 and snap["won_value_30d"] == 5000
    assert snap["lost_count_30d"] == 1
    assert snap["win_rate_90d"] == round(1 / 3, 4)
    assert snap["other_currencies"] == {"EUR": {"count": 1, "value": 400.0}}
    assert [s["stage"] for s in snap["stages"]] == ["Proposal/Price Quote", "Qualification"]
    assert any("EUR" in w for w in result.warnings)

    fin = result.metadata["financials"]
    assert fin["revenue"] == 5000 and fin["deals_won"] == 1
    assert fin["period_start"] == TODAY.replace(day=1).isoformat()
    assert result.metadata["accounts_count"] == 42


def test_won_deals_from_earlier_months_are_not_this_months_revenue(mock_http):
    old = _deal(7, 9999, "Closed Won", 100, TODAY.replace(day=1) - timedelta(days=1))
    mock_http(_zoho_handler(deals=[old]))
    fin = _run(_zoho().sync_all()).metadata["financials"]
    assert "revenue" not in fin


def test_expired_token_refreshes_once(mock_http):
    calls = {"org": 0}

    def handler(req):
        if req.url.path == "/crm/v8/org":
            calls["org"] += 1
            if req.headers["Authorization"] == "Zoho-oauthtoken at":
                return httpx.Response(401)
        return _zoho_handler()(req)

    seen = mock_http(handler)
    conn = _zoho()
    assert _run(conn.authenticate())
    assert calls["org"] == 2
    assert any(r.url.host == "accounts.zoho.in" for r in seen)
    assert conn.rotated_credentials()["access_token"] == "fresh"


def test_no_crm_access_fails_with_reconnect_hint(mock_http):
    mock_http(_zoho_handler(org_status=403))
    result = _run(_zoho().sync_all())
    assert not result.success
    assert "can't read Zoho CRM" in result.errors[0]


def test_empty_crm_is_a_successful_sync(mock_http):
    def handler(req):
        if req.url.path == "/crm/v8/Deals":
            return httpx.Response(204)
        return _zoho_handler()(req)
    mock_http(handler)
    result = _run(_zoho().sync_all())
    assert result.success and result.metadata["crm_pipeline"]["open_count"] == 0
    assert "no deals" in result.warnings[-1]


def test_more_than_page_cap_is_flagged(mock_http):
    mock_http(_zoho_handler(more_pages=True))
    result = _run(_zoho().sync_all())
    assert result.metadata["crm_pipeline"]["truncated"] is True
    assert any("first 2000 deals" in w for w in result.warnings)


# --- HubSpot and Pipedrive normalisation -------------------------------------

def test_hubspot_deal_mapping():
    won = hubspot.hubspot_deal_for_snapshot({"properties": {
        "amount": "500", "dealstage": "closedwon", "hs_is_closed_won": "true", "hs_is_closed": "true",
        "closedate": "2026-11-01T10:00:00Z", "hs_deal_stage_probability": "1"}})
    open_ = hubspot.hubspot_deal_for_snapshot({"properties": {
        "amount": "200", "dealstage": "appointmentscheduled", "hs_is_closed_won": "false",
        "hs_is_closed": "false", "hs_deal_stage_probability": "0.2"}})
    lost = hubspot.hubspot_deal_for_snapshot({"properties": {"dealstage": "closedlost"}})
    assert won["status"] == "won" and won["close_date"].startswith("2026-11-01")
    assert open_["status"] == "open" and open_["probability"] == 0.2
    assert lost["status"] == "lost"


def test_pipedrive_deal_mapping_uses_stage_names():
    d = pipedrive.pipedrive_deal_for_snapshot(
        {"value": 100, "currency": "USD", "status": "won", "won_time": "2026-11-02T00:00:00Z", "stage_id": 3, "probability": None},
        {"3": "Negotiation"},
    )
    assert d == {"amount": 100.0, "currency": "USD", "stage": "Negotiation", "status": "won",
                 "close_date": "2026-11-02T00:00:00Z", "probability": None}
    assert pipedrive.pipedrive_deal_for_snapshot({"stage_id": 9, "status": "open"})["stage"] == "Stage 9"


def test_parse_day_and_probability():
    assert crm_pipeline.parse_day("2026-11-03") == date(2026, 11, 3)
    assert crm_pipeline.parse_day(1762128000000) == date(2025, 11, 3)
    assert crm_pipeline.parse_day("garbage") is None
    assert crm_pipeline.probability(75) == 0.75 and crm_pipeline.probability("0.3") == 0.3
    assert crm_pipeline.probability(None) is None


def test_no_probabilities_leaves_weighted_empty():
    snap = crm_pipeline.build_snapshot([{"amount": 10, "status": "open", "stage": "A"}], "USD", today=TODAY)
    assert snap["weighted_value"] is None and snap["win_rate_90d"] is None


# --- storage, route and view -------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[
        User.__table__, Company.__table__, WorkspaceMember.__table__,
        CRMPipelineSnapshot.__table__, FinancialRecord.__table__,
    ])
    session = sessionmaker(bind=engine)()
    owner = User(email="owner@startup.io", is_active=True)
    session.add(owner)
    session.flush()
    session.add(Company(id=1, name="Startup", user_id=owner.id, currency="INR"))
    session.commit()
    return session


def _snap(open_value, day):
    return crm_pipeline.build_snapshot([{"amount": open_value, "status": "open", "stage": "A"}], "INR", today=day)


def test_same_day_resync_replaces_and_new_day_adds_trend_point(db):
    crm_pipeline.store_snapshot(db, 1, "zoho_crm", _snap(100, TODAY - timedelta(days=7)))
    crm_pipeline.store_snapshot(db, 1, "zoho_crm", _snap(200, TODAY))
    crm_pipeline.store_snapshot(db, 1, "zoho_crm", _snap(300, TODAY))
    crm_pipeline.store_snapshot(db, 1, "hubspot", _snap(50, TODAY))
    db.commit()
    assert db.query(CRMPipelineSnapshot).count() == 3
    view = crm_pipeline.summary(db, 1)
    assert [c["source"] for c in view["crms"]] == ["zoho_crm", "hubspot"]
    assert view["crms"][0]["open_value"] == 300
    assert [p["open_value"] for p in view["crms"][0]["trend"]] == [100, 300]
    assert crm_pipeline.store_snapshot(db, 1, "x", None) is False


def test_route_stores_snapshot_and_serves_view(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import connectors as connectors_api
    from server.core.db import get_db
    from server.core.security import get_current_user

    company = db.query(Company).one()
    company.metadata_json = {"connectors": {"zoho_crm": {"connected": True, "credentials": {"refresh_token": "rt"}}}}
    db.commit()

    result = SyncResult(success=True, provider_id="zoho_crm", sync_type="full", records_synced=3,
                        metadata={"crm_pipeline": _snap(4000, TODAY), "financials": {}})

    async def fake_sync(self):
        return result

    monkeypatch.setattr(zoho_crm.ZohoCRMConnector, "sync_all", fake_sync)
    app = FastAPI()
    app.include_router(connectors_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.query(User).one()
    client = TestClient(app)

    res = client.post("/api/connectors/companies/1/sync/zoho_crm")
    assert res.status_code == 200, res.text
    view = client.get("/api/connectors/companies/1/crm-pipeline").json()
    assert view["crms"][0]["source"] == "zoho_crm" and view["crms"][0]["open_value"] == 4000
    assert client.get("/api/connectors/companies/999/crm-pipeline").status_code == 404


def test_zoho_crm_oauth_provider_shares_zoho_client(monkeypatch):
    from server.api.connector_oauth import PROVIDERS

    monkeypatch.setenv("ZOHO_CLIENT_ID", "cid")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "sec")
    p = PROVIDERS["zoho_crm"]
    assert p.configured() and PROVIDERS["zoho_books"].configured()
    assert "ZohoCRM.modules.deals.READ" in p.app()["scopes"] and p.scope_separator == ","
