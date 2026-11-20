"""Software spend: card classification, storage, the sync route and the view."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.connectors import onepassword, ramp
from server.connectors.base import LedgerEntry, SyncResult
from server.models.company import Company
from server.models.exchange_rate import ExchangeRate
from server.models.financial import FinancialRecord
from server.models.software_spend import SoftwareSpend
from server.models.user import User
from server.models.workspace import WorkspaceMember
from server.services import software_spend

NOV = date(2026, 11, 1)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[
        User.__table__, Company.__table__, WorkspaceMember.__table__,
        SoftwareSpend.__table__, ExchangeRate.__table__, FinancialRecord.__table__,
    ])
    session = sessionmaker(bind=engine)()
    owner = User(email="owner@startup.io", is_active=True)
    session.add(owner)
    session.flush()
    session.add(Company(id=1, name="Startup", user_id=owner.id, currency="USD"))
    session.commit()
    return session


def _card(merchant, amount, category, when=datetime(2026, 11, 5), currency=None, credit=0.0):
    meta = {"merchant_name": merchant, "type": "card_transaction"}
    if currency:
        meta["currency"] = currency
    return LedgerEntry(external_id=f"{merchant}-{amount}", date=when, account_code="card",
                       account_name="Card", debit=amount, credit=credit, description=merchant,
                       category=category, metadata=meta)


# --- classification ----------------------------------------------------------

@pytest.mark.parametrize("category", ["Software", "SaaS / Software", "SOFTWARE", "Subscriptions", "5734", "7372", "Cloud hosting"])
def test_software_categories_match(category):
    assert software_spend.is_software_category(category)


@pytest.mark.parametrize("category", [None, "", "Travel", "Meals", "Advertising", "5812", "Uncategorized"])
def test_other_categories_do_not_match(category):
    assert not software_spend.is_software_category(category)


def test_card_spend_groups_by_month_and_merchant_and_nets_refunds():
    payload = software_spend.card_software_months([
        _card("Notion", 96, "Software"),
        _card("Notion", 0, "Software", credit=16),
        _card("Figma", 45, "SaaS / Software"),
        _card("Figma", 45, "SaaS / Software", when=datetime(2026, 10, 5)),
        _card("Uber", 30, "Travel"),
        _card("Refunded", 0, "Software", credit=20),
        LedgerEntry(external_id="r1", date=datetime(2026, 11, 3), account_code="x", account_name="x",
                    debit=50, category="Software", metadata={"type": "reimbursement"}),
    ])
    assert [m["period"] for m in payload["months"]] == ["2026-10-01", "2026-11-01"]
    nov = payload["months"][1]["vendors"]
    assert nov == [
        {"vendor": "Notion", "amount": 80.0, "currency": "USD", "basis": "card", "transactions": 2},
        {"vendor": "Figma", "amount": 45.0, "currency": "USD", "basis": "card", "transactions": 1},
    ]


# --- storage -----------------------------------------------------------------

def test_resync_replaces_only_that_sources_month(db):
    software_spend.replace_month(db, 1, NOV, "ramp", [{"vendor": "Notion", "amount": 96, "currency": "USD"}])
    software_spend.replace_month(db, 1, NOV, "onepassword", [{"vendor": "1Password", "amount": 80, "currency": "USD", "basis": "seats", "seats": 10}])
    software_spend.replace_month(db, 1, NOV, "ramp", [{"vendor": "Notion", "amount": 100, "currency": "USD"}])
    db.commit()
    view = software_spend.summary(db, 1)
    assert view["months"][0]["total_company"] == 180
    assert {v["vendor"]: v["amount"] for v in view["months"][0]["vendors"]} == {"Notion": 100, "1Password": 80}


def test_other_currency_without_a_rate_is_listed_not_summed(db):
    software_spend.replace_month(db, 1, NOV, "brex", [
        {"vendor": "Linear", "amount": 50, "currency": "USD"},
        {"vendor": "Miro", "amount": 40, "currency": "EUR"},
    ])
    db.commit()
    month = software_spend.summary(db, 1)["months"][0]
    assert month["total_company"] == 50
    assert month["unconverted"] == [{"vendor": "Miro", "amount": 40, "currency": "EUR"}]


def test_other_currency_with_a_stored_rate_is_converted(db):
    db.add(ExchangeRate(base_currency="EUR", quote_currency="USD", rate=1.1, rate_date=date(2026, 11, 30)))
    db.commit()
    software_spend.replace_month(db, 1, NOV, "brex", [{"vendor": "Miro", "amount": 40, "currency": "EUR"}])
    db.commit()
    assert software_spend.summary(db, 1)["months"][0]["total_company"] == 44


def test_bad_payloads_are_ignored(db):
    assert software_spend.store_payload(db, 1, "ramp", None) == 0
    assert software_spend.store_payload(db, 1, "ramp", {"months": [{"vendors": []}, "x"]}) == 0
    software_spend.replace_month(db, 1, NOV, "ramp", [{"vendor": "", "amount": 5}, {"vendor": "A", "amount": 1}, {"vendor": "A", "amount": 2}])
    db.commit()
    assert db.query(SoftwareSpend).count() == 1


# --- connectors --------------------------------------------------------------

def test_onepassword_payload_carries_seat_details():
    conn = onepassword.OnePasswordConnector.__new__(onepassword.OnePasswordConnector)
    entry = LedgerEntry(external_id="1password-seats-2026-11", date=datetime(2026, 11, 20), account_code="software",
                        account_name="1Password", debit=79.9, category="Software",
                        metadata={"metric_type": "seat_cost", "seats": 10, "active_users": 7,
                                  "seat_price_monthly": 7.99, "billing_basis": "seats", "unused_seats": 3,
                                  "seat_utilization": 0.7})
    payload = conn.software_spend_payload([entry])
    line = payload["months"][0]["vendors"][0]
    assert payload["months"][0]["period"] == "2026-11-01"
    assert line["amount"] == 79.9 and line["seats"] == 10 and line["details"]["unused_seats"] == 3
    assert conn.software_spend_payload([]) == {"months": []}


# --- the sync route and the view ---------------------------------------------

def _client(db, monkeypatch, provider, connector_cls, result):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import connectors as connectors_api
    from server.core.db import get_db
    from server.core.security import get_current_user

    company = db.query(Company).one()
    company.metadata_json = {"connectors": {provider: {"connected": True, "credentials": {"access_token": "tok"}}}}
    db.commit()

    async def fake_sync(self):
        return result

    async def fake_close(self):
        return None

    monkeypatch.setattr(connector_cls, "sync_all", fake_sync)
    monkeypatch.setattr(connector_cls, "close", fake_close, raising=False)
    app = FastAPI()
    app.include_router(connectors_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.query(User).one()
    return TestClient(app)


def test_route_stores_software_spend_without_touching_opex(db, monkeypatch):
    result = SyncResult(success=True, provider_id="ramp", sync_type="full", records_synced=2, metadata={
        "software_spend": {"months": [{"period": "2026-11-01", "vendors": [
            {"vendor": "Notion", "amount": 96, "currency": "USD", "basis": "card", "transactions": 1}]}]}})
    client = _client(db, monkeypatch, "ramp", ramp.RampConnector, result)
    res = client.post("/api/connectors/companies/1/sync/ramp")
    assert res.status_code == 200, res.text
    assert db.query(FinancialRecord).count() == 0

    view = client.get("/api/connectors/companies/1/software-spend").json()
    assert view["currency"] == "USD" and view["sources"] == ["ramp"]
    assert view["months"][0]["vendors"][0]["vendor"] == "Notion"
    assert client.get("/api/connectors/companies/999/software-spend").status_code == 404
