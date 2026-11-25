"""Marketplace channel sales: months accumulate on the connection and the
GET .../channel-sales view reads them back."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api.connectors import CHANNEL_MONTHS_KEPT, merge_channel_sales
from server.connectors import amazon
from server.connectors.base import SyncResult
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.user import User
from server.models.workspace import WorkspaceMember


def _month(period, net=1000.0, orders=10):
    return {"period": period, "marketplace": "Amazon.in", "net_sales_ex_gst": net,
            "orders_shipped": orders, "amazon_fees": net * 0.2, "amazon_fee_pct": 0.2}


def test_merge_adds_new_month_and_keeps_old():
    first = merge_channel_sales(None, {"channel": "amazon", "months": [_month("2026-09-01")]})
    second = merge_channel_sales(first, {"channel": "amazon", "months": [_month("2026-10-01")]})
    assert [m["period"] for m in second["months"]] == ["2026-09-01", "2026-10-01"]
    assert second["channel"] == "amazon" and second["synced_at"]


def test_merge_resync_replaces_same_month():
    first = merge_channel_sales(None, {"channel": "amazon", "months": [_month("2026-10-01", net=1)]})
    again = merge_channel_sales(first, {"channel": "amazon", "months": [_month("2026-10-01", net=2)]})
    assert len(again["months"]) == 1 and again["months"][0]["net_sales_ex_gst"] == 2


def test_merge_keeps_last_twelve_sorted():
    block = None
    for m in [12, 3, 7, 1, 11, 2, 4, 5, 6, 8, 9, 10]:
        block = merge_channel_sales(block, {"channel": "amazon", "months": [_month(f"2025-{m:02d}-01")]})
    block = merge_channel_sales(block, {"channel": "amazon", "months": [_month("2026-01-01")]})
    periods = [m["period"] for m in block["months"]]
    assert len(periods) == CHANNEL_MONTHS_KEPT
    assert periods[0] == "2025-02-01" and periods[-1] == "2026-01-01"


def test_merge_ignores_garbage_existing():
    block = merge_channel_sales("not-a-dict", {"channel": "amazon", "months": [_month("2026-10-01"), {"x": 1}]})
    assert [m["period"] for m in block["months"]] == ["2026-10-01"]


# --- route + view -------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[
        User.__table__, Company.__table__, WorkspaceMember.__table__, FinancialRecord.__table__,
    ])
    session = sessionmaker(bind=engine)()
    owner = User(email="owner@brand.in", is_active=True)
    session.add(owner)
    session.flush()
    session.add(Company(id=1, name="Brand", user_id=owner.id, currency="INR"))
    session.commit()
    return session


def _client(db, monkeypatch, results):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.api import connectors as connectors_api
    from server.core.db import get_db
    from server.core.security import get_current_user

    company = db.query(Company).one()
    company.metadata_json = {"connectors": {"amazon": {"connected": True, "credentials": {
        "client_id": "c", "client_secret": "s", "refresh_token": "r", "region": "eu"}}}}
    db.commit()
    queue = list(results)

    async def fake_sync(self):
        return queue.pop(0)

    async def fake_close(self):
        return None

    monkeypatch.setattr(amazon.AmazonSellerConnector, "sync_all", fake_sync)
    monkeypatch.setattr(amazon.AmazonSellerConnector, "close", fake_close, raising=False)
    app = FastAPI()
    app.include_router(connectors_api.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.query(User).one()
    return TestClient(app)


def _result(period):
    m = _month(period)
    return SyncResult(success=True, provider_id="amazon", sync_type="full", records_synced=3,
                      metadata={"amazon": m, "channel_sales": {"channel": "amazon", "months": [m]}})


def test_two_syncs_show_two_months(db, monkeypatch):
    client = _client(db, monkeypatch, [_result("2026-09-01"), _result("2026-10-01")])
    assert client.get("/api/connectors/companies/1/channel-sales").json() == {"channels": []}
    for _ in range(2):
        res = client.post("/api/connectors/companies/1/sync/amazon")
        assert res.status_code == 200, res.text
    view = client.get("/api/connectors/companies/1/channel-sales").json()
    assert len(view["channels"]) == 1
    ch = view["channels"][0]
    assert ch["channel"] == "amazon" and ch["provider_id"] == "amazon" and ch["synced_at"]
    assert [m["period"] for m in ch["months"]] == ["2026-09-01", "2026-10-01"]
    # Marketplace figures stay off the blended ledger.
    assert db.query(FinancialRecord).count() == 0
    assert client.get("/api/connectors/companies/999/channel-sales").status_code == 404


def test_disconnected_channel_is_hidden(db, monkeypatch):
    client = _client(db, monkeypatch, [_result("2026-10-01")])
    client.post("/api/connectors/companies/1/sync/amazon")
    company = db.query(Company).one()
    meta = dict(company.metadata_json)
    meta["connectors"] = {"amazon": {**meta["connectors"]["amazon"], "connected": False}}
    company.metadata_json = meta
    db.commit()
    assert client.get("/api/connectors/companies/1/channel-sales").json() == {"channels": []}
