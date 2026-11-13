"""A failed generic connector sync records last_error on the connection.

Before this, only the needs_reauth path wrote last_error. Every other failure
rolled back and raised, so the card kept showing the previous success.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api.connectors import router
from server.connectors.base import SyncResult
from server.connectors.hubspot import HubSpotConnector
from server.core.db import Base, get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.financial import FinancialRecord

USER = SimpleNamespace(id=1, email="owner@example.com", is_platform_admin=False, role="user")


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Company.__table__, FinancialRecord.__table__])
    Session = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: USER
    return TestClient(app), Session


def _company(Session):
    session = Session()
    company = Company(
        user_id=USER.id,
        name="Acme",
        metadata_json={
            "connectors": {
                "hubspot": {
                    "connected": True,
                    "credentials": {"access_token": "pat-test"},
                    "last_sync": "2026-11-01T00:00:00",
                    "last_error": None,
                }
            }
        },
    )
    session.add(company)
    session.commit()
    company_id = company.id
    session.close()
    return company_id


def _hubspot_row(Session, company_id):
    session = Session()
    company = session.query(Company).filter(Company.id == company_id).one()
    row = dict(company.metadata_json["connectors"]["hubspot"])
    session.close()
    return row


def _status_error(http, company_id):
    rows = http.get(f"/connectors/companies/{company_id}/status").json()["connectors"]
    return next(r for r in rows if r["provider_id"] == "hubspot")


def test_unexpected_exception_records_last_error(client, monkeypatch):
    http, Session = client

    async def _boom(self):
        raise RuntimeError("upstream timed out")

    monkeypatch.setattr(HubSpotConnector, "sync_all", _boom)
    company_id = _company(Session)

    response = http.post(f"/connectors/companies/{company_id}/sync/hubspot")
    assert response.status_code == 500
    assert "upstream timed out" in response.text

    row = _hubspot_row(Session, company_id)
    assert row["connected"] is True
    assert "upstream timed out" in row["last_error"]
    assert row["last_error_at"]
    # The previous successful sync time is kept; it is not overwritten.
    assert row["last_sync"] == "2026-11-01T00:00:00"

    status = _status_error(http, company_id)
    assert status["connected"] is True
    assert "upstream timed out" in status["error"]


def test_failed_sync_result_records_last_error_and_success_clears_it(client, monkeypatch):
    http, Session = client

    async def _failed(self):
        return SyncResult(
            success=False, provider_id="hubspot", sync_type="full", errors=["rate limited"]
        )

    monkeypatch.setattr(HubSpotConnector, "sync_all", _failed)
    company_id = _company(Session)

    response = http.post(f"/connectors/companies/{company_id}/sync/hubspot")
    assert response.status_code == 400
    row = _hubspot_row(Session, company_id)
    assert row["connected"] is True
    assert "rate limited" in row["last_error"]
    assert not row.get("needs_reauth")

    async def _ok(self):
        return SyncResult(success=True, provider_id="hubspot", sync_type="full", records_synced=3)

    monkeypatch.setattr(HubSpotConnector, "sync_all", _ok)
    response = http.post(f"/connectors/companies/{company_id}/sync/hubspot")
    assert response.status_code == 200, response.text
    row = _hubspot_row(Session, company_id)
    assert row["last_error"] is None
    assert "last_error_at" not in row
    assert row["records_synced"] == 3
