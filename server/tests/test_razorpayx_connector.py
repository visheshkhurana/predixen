"""RazorpayX catalog id, payroll mapping, and failed-sync recording."""

import asyncio
import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api.connectors import _sample_for, _status_row, router
from server.connectors.base import ConnectorConfig
from server.connectors.razorpayx import (
    ACCOUNT_NUMBER_REQUIRED,
    NO_SALARY_PAYOUTS,
    RazorpayXConnector,
    financials_from_razorpayx,
    redact_account_logs,
    redact_account_number,
)
from server.core.encryption import decrypt_credentials, mask_account_number
from server.connectors.registry import ConnectorRegistry
from server.core.db import Base, get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.financial import FinancialRecord

USER = SimpleNamespace(id=1, email="owner@example.com", is_platform_admin=False, role="user")

OCT = int(datetime(2026, 10, 3, tzinfo=timezone.utc).timestamp())
SEP = int(datetime(2026, 9, 3, tzinfo=timezone.utc).timestamp())

CONTACTS = {
    "entity": "collection",
    "count": 4,
    "items": [
        {"id": "cont_1", "name": "A", "type": "employee", "active": True, "email": "a@example.com"},
        {"id": "cont_2", "name": "B", "type": "employee", "active": True},
        {"id": "cont_3", "name": "C", "type": "employee", "active": False},
        {"id": "cont_4", "name": "Vendor", "type": "vendor", "active": True},
    ],
}

PAYOUTS = {
    "entity": "collection",
    "count": 4,
    "items": [
        {
            "id": "pout_oct",
            "amount": 8500000,
            "currency": "INR",
            "status": "processed",
            "purpose": "salary",
            "created_at": OCT,
        },
        {
            "id": "pout_vendor",
            "amount": 5000000,
            "currency": "INR",
            "status": "processed",
            "purpose": "vendor bill",
            "created_at": OCT,
        },
        {
            "id": "pout_sep",
            "amount": 9900000,
            "currency": "INR",
            "status": "processed",
            "purpose": "salary",
            "created_at": SEP,
        },
        {
            "id": "pout_failed",
            "amount": 100000,
            "currency": "INR",
            "status": "failed",
            "purpose": "salary",
            "created_at": OCT,
        },
    ],
}


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    calls = []

    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.get("base_url")
        self.auth = kwargs.get("auth")
        _FakeClient.calls.append(("init", self.base_url, self.auth))

    async def get(self, path, params=None):
        _FakeClient.calls.append((path, params))
        if path == "/payouts":
            return _Response(200, PAYOUTS)
        if path != "/contacts":
            raise AssertionError(path)
        return _Response(200, CONTACTS)

    async def post(self, *args, **kwargs):
        raise AssertionError("RazorpayX must not POST placeholder payroll endpoints")

    async def aclose(self):
        return None


class _RejectingPayouts(_FakeClient):
    async def get(self, path, params=None):
        _FakeClient.calls.append((path, params))
        if path == "/payouts":
            return _Response(400, {"error": {"description": "The account number is invalid"}})
        return _Response(200, {"entity": "collection", "count": 0, "items": []})


def test_catalog_id_and_legacy_alias_resolve_to_one_connector():
    assert RazorpayXConnector.PROVIDER_ID == "razorpayx"
    assert ConnectorRegistry.get_connector_class("razorpayx") is RazorpayXConnector
    assert ConnectorRegistry.get_connector_class("razorpayx_payroll") is RazorpayXConnector
    assert ConnectorRegistry.canonical_provider_id("razorpayx_payroll") == "razorpayx"
    providers = ConnectorRegistry.get_available_providers()
    assert "razorpayx" in providers
    assert "razorpayx_payroll" not in providers
    assert _sample_for("razorpayx")["payroll"] == 85000
    assert _sample_for("razorpayx")["headcount"] == 15
    assert _sample_for("razorpayx_payroll")["payroll"] == 85000


def test_salary_payouts_map_to_payroll_rupees_and_active_employees():
    mapped = financials_from_razorpayx(CONTACTS["items"], PAYOUTS["items"])

    assert mapped["payroll"] == 85000.0
    assert mapped["headcount"] == 2
    assert mapped["month"] == "2026-10"
    assert mapped["salary_payout_count"] == 1
    assert "85000.00" in mapped["extraction_summary"]
    assert "unavailable" not in mapped


def test_mapping_without_salary_payouts_is_not_available():
    mapped = financials_from_razorpayx(CONTACTS["items"], [PAYOUTS["items"][1]])
    assert mapped["unavailable"] == NO_SALARY_PAYOUTS
    assert mapped["headcount"] == 2
    assert "payroll" not in mapped


def test_sync_without_account_number_does_not_call_razorpay(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("should not call RazorpayX")

    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", explode)
    connector = RazorpayXConnector(
        ConnectorConfig(
            provider_id="razorpayx",
            company_id=1,
            credentials={"api_key": "rzp_test", "api_secret": "test-secret"},
        )
    )
    result = asyncio.run(connector.sync_all())
    assert result.success is False
    assert result.errors == [ACCOUNT_NUMBER_REQUIRED]
    assert "Opfin" in result.errors[0]


def test_sync_records_razorpay_api_errors(monkeypatch):
    _FakeClient.calls = []
    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", _RejectingPayouts)
    connector = RazorpayXConnector(
        ConnectorConfig(
            provider_id="razorpayx_payroll",
            company_id=1,
            credentials={
                "api_key": "rzp_test",
                "api_secret": "test-secret",
                "account_number": "2323230000000000",
            },
        )
    )
    result = asyncio.run(connector.sync_all())
    assert result.success is False
    assert any("invalid" in error for error in result.errors)
    assert not any(call[0] == "post" for call in _FakeClient.calls)


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


def _company(Session, connectors):
    session = Session()
    company = Company(user_id=USER.id, name="Acme", metadata_json={"connectors": connectors})
    session.add(company)
    session.commit()
    company_id = company.id
    session.close()
    return company_id


def _read(Session, company_id):
    session = Session()
    company = session.query(Company).filter(Company.id == company_id).one()
    connectors = dict(company.metadata_json["connectors"])
    records = session.query(FinancialRecord).filter(FinancialRecord.company_id == company_id).all()
    session.close()
    return connectors, records


@pytest.mark.parametrize("provider_id", ["razorpayx", "razorpayx_payroll"])
def test_connect_accepts_catalog_id_and_legacy_alias(client, provider_id, monkeypatch):
    http, Session = client

    async def _authenticated(self):
        return True

    monkeypatch.setattr(RazorpayXConnector, "authenticate", _authenticated)
    company_id = _company(Session, {})
    secret = "test-secret-value"
    response = http.post(
        f"/connectors/companies/{company_id}/connect",
        json={
            "provider_id": provider_id,
            "credentials": {"api_key": "rzp_test", "api_secret": secret},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["provider_id"] == provider_id
    assert secret not in response.text
    connectors, _records = _read(Session, company_id)
    stored = connectors[provider_id]["credentials"]
    assert isinstance(stored, str)
    assert secret not in stored


def test_unknown_provider_is_rejected(client):
    http, Session = client
    company_id = _company(Session, {})
    response = http.post(
        f"/connectors/companies/{company_id}/connect",
        json={"provider_id": "not_a_real_provider", "credentials": {"api_key": "x"}},
    )
    assert response.status_code == 400
    assert "Unknown provider" in response.text


def test_successful_sync_writes_payroll_and_headcount(client, monkeypatch):
    http, Session = client
    _FakeClient.calls = []
    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", _FakeClient)
    company_id = _company(
        Session,
        {
            "razorpayx": {
                "connected": True,
                "credentials": {
                    "api_key": "rzp_test",
                    "api_secret": "test-secret",
                    "account_number": "2323230000000000",
                },
                "last_error": "stale",
            }
        },
    )
    response = http.post(f"/connectors/companies/{company_id}/sync/razorpayx")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["records_synced"] == 3
    assert "test-secret" not in response.text

    connectors, records = _read(Session, company_id)
    assert connectors["razorpayx"]["last_error"] is None
    stored = connectors["razorpayx"]["credentials"]
    assert isinstance(stored, str)
    assert "2323230000000000" not in stored
    assert decrypt_credentials(stored)["account_number"] == "2323230000000000"
    assert "account_number" not in (connectors["razorpayx"].get("settings") or {})
    assert connectors["razorpayx"]["last_sync"]
    assert len(records) == 1
    record = records[0]
    assert record.source_type == "connector_razorpayx"
    assert len(record.source_type) <= 20
    assert record.payroll == 85000.0
    assert record.headcount == 2
    assert "2026-10" in record.extraction_summary
    paths = [call[0] for call in _FakeClient.calls if call[0] != "init"]
    assert "/payouts" in paths
    assert "/contacts" in paths
    assert all("payroll" not in path for path in paths)


def test_legacy_storage_syncs_through_catalog_id(client, monkeypatch):
    http, Session = client
    _FakeClient.calls = []
    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", _FakeClient)
    company_id = _company(
        Session,
        {
            "razorpayx_payroll": {
                "connected": True,
                "credentials": {
                    "api_key": "rzp_test",
                    "api_secret": "test-secret",
                    "account_number": "2323230000000000",
                },
                "last_error": "previous",
            }
        },
    )
    response = http.post(f"/connectors/companies/{company_id}/sync/razorpayx")
    assert response.status_code == 200, response.text
    connectors, records = _read(Session, company_id)
    assert "razorpayx" not in connectors
    assert connectors["razorpayx_payroll"]["connected"] is True
    assert connectors["razorpayx_payroll"]["last_error"] is None
    assert records[0].source_type == "connector_razorpayx"
    assert records[0].payroll == 85000.0
    assert records[0].headcount == 2

    status = http.get(f"/connectors/companies/{company_id}/status")
    assert status.status_code == 200
    rows = {row["provider_id"]: row for row in status.json()["connectors"]}
    assert rows["razorpayx"]["connected"] is True
    assert rows["razorpayx"]["error"] is None
    assert rows["razorpayx_payroll"]["connected"] is True


def test_failed_sync_is_recorded_and_stays_connected(client):
    http, Session = client
    company_id = _company(
        Session,
        {
            "razorpayx": {
                "connected": True,
                "credentials": {"api_key": "rzp_test", "api_secret": "test-secret"},
                "last_error": None,
            }
        },
    )
    response = http.post(f"/connectors/companies/{company_id}/sync/razorpayx")
    assert response.status_code == 400, response.text
    assert "account_number" in response.text
    assert "Opfin" in response.text
    assert "test-secret" not in response.text

    connectors, records = _read(Session, company_id)
    assert records == []
    assert connectors["razorpayx"]["connected"] is True
    assert connectors["razorpayx"]["last_error"]
    assert "account_number" in connectors["razorpayx"]["last_error"]

    status = http.get(f"/connectors/companies/{company_id}/status")
    rows = {row["provider_id"]: row for row in status.json()["connectors"]}
    assert rows["razorpayx"]["connected"] is True
    assert rows["razorpayx"]["error"]
    assert "account_number" in rows["razorpayx"]["error"]


ACCOUNT = "9182736450192837"
ACCOUNT_PREFIX = ACCOUNT[:-4]


def _assert_account_hidden(text: str):
    assert ACCOUNT not in text
    assert ACCOUNT_PREFIX not in text


class _LeakingPayouts(_FakeClient):
    """Razorpay's error description and the httpx log both echo the account number."""

    async def get(self, path, params=None):
        _FakeClient.calls.append((path, params))
        if path == "/payouts":
            account = (params or {}).get("account_number", "")
            logging.getLogger("httpx").error(
                "HTTP Request: GET https://api.razorpay.com/v1/payouts?account_number=%s&from=1",
                account,
            )
            return _Response(
                400,
                {"error": {"description": f"Invalid account {account} for payouts"}},
            )
        return _Response(200, {"entity": "collection", "count": 0, "items": []})


class _RaisingPayouts(_FakeClient):
    async def get(self, path, params=None):
        _FakeClient.calls.append((path, params))
        if path == "/payouts":
            account = (params or {}).get("account_number", "")
            try:
                raise RuntimeError(
                    f"GET https://api.razorpay.com/v1/payouts?account_number={account}&from=1"
                )
            except RuntimeError:
                logging.getLogger("httpx").exception("payout request failed")
                raise
        return _Response(200, {"entity": "collection", "count": 0, "items": []})


def test_redact_account_number_keeps_last_four_only():
    leaked = f"account_number={ACCOUNT} Invalid account {ACCOUNT}"
    redacted = redact_account_number(leaked, ACCOUNT)
    _assert_account_hidden(redacted)
    assert mask_account_number(ACCOUNT) == "••••2837"
    assert "••••2837" in redacted
    assert mask_account_number("1234") == "****"
    assert redact_account_number(f"account_number={ACCOUNT}") == f"account_number={'••••2837'}"


def test_log_filter_strips_account_from_httpx_logs_and_tracebacks(caplog):
    caplog.set_level(logging.DEBUG)
    with redact_account_logs(ACCOUNT):
        logging.getLogger("httpx").error(
            "HTTP Request: GET https://api.razorpay.com/v1/payouts?account_number=%s",
            ACCOUNT,
        )
        try:
            raise RuntimeError(f"boom account_number={ACCOUNT}")
        except RuntimeError:
            logging.getLogger("server.connectors.razorpayx").exception("sync blew up")
    _assert_account_hidden(caplog.text)
    assert "••••2837" in caplog.text


def test_connect_masks_account_and_stores_it_encrypted(client, monkeypatch):
    http, Session = client

    async def _authenticated(self):
        return True

    monkeypatch.setattr(RazorpayXConnector, "authenticate", _authenticated)
    company_id = _company(Session, {})
    response = http.post(
        f"/connectors/companies/{company_id}/connect",
        json={
            "provider_id": "razorpayx",
            "credentials": {"api_key": "rzp_test", "api_secret": "test-secret"},
            "settings": {"account_number": ACCOUNT, "environment": "test"},
        },
    )
    assert response.status_code == 200, response.text
    _assert_account_hidden(response.text)
    assert response.json()["account_hint"] == "••••2837"

    connectors, _records = _read(Session, company_id)
    stored = connectors["razorpayx"]["credentials"]
    settings = connectors["razorpayx"].get("settings") or {}
    assert isinstance(stored, str)
    _assert_account_hidden(stored)
    assert "account_number" not in settings
    assert settings.get("environment") == "test"
    assert decrypt_credentials(stored)["account_number"] == ACCOUNT

    status = http.get(f"/connectors/companies/{company_id}/status")
    assert status.status_code == 200
    _assert_account_hidden(status.text)
    rows = {row["provider_id"]: row for row in status.json()["connectors"]}
    assert rows["razorpayx"]["account_hint"] == "••••2837"
    assert rows["razorpayx"]["connected"] is True

    stored_row = _status_row(
        "razorpayx",
        {
            "connected": True,
            "last_error": f"Invalid account {ACCOUNT}",
            "credentials": {"account_number": ACCOUNT, "api_secret": "test-secret"},
            "records_synced": 0,
        },
    )
    _assert_account_hidden(stored_row["error"])
    assert stored_row["account_hint"] == "••••2837"
    assert "••••2837" in stored_row["error"]
    assert "api_secret" not in stored_row
    assert "test-secret" not in str(stored_row)


def test_sync_error_hides_account_in_response_logs_and_last_error(client, monkeypatch, caplog):
    http, Session = client
    caplog.set_level(logging.DEBUG)
    _FakeClient.calls = []
    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", _LeakingPayouts)
    company_id = _company(
        Session,
        {
            "razorpayx": {
                "connected": True,
                "credentials": {
                    "api_key": "rzp_test",
                    "api_secret": "test-secret",
                    "account_number": ACCOUNT,
                },
                "settings": {"account_number": ACCOUNT},
            }
        },
    )
    response = http.post(f"/connectors/companies/{company_id}/sync/razorpayx")
    assert response.status_code == 400, response.text
    _assert_account_hidden(response.text)
    assert "••••2837" in response.text
    assert "Invalid account" in response.text

    connectors, records = _read(Session, company_id)
    assert records == []
    last_error = connectors["razorpayx"]["last_error"]
    assert last_error
    _assert_account_hidden(last_error)
    assert "••••2837" in last_error
    stored = connectors["razorpayx"]["credentials"]
    assert isinstance(stored, str)
    _assert_account_hidden(stored)
    assert decrypt_credentials(stored)["account_number"] == ACCOUNT
    assert "account_number" not in (connectors["razorpayx"].get("settings") or {})
    _assert_account_hidden(caplog.text)

    status = http.get(f"/connectors/companies/{company_id}/status")
    _assert_account_hidden(status.text)
    rows = {row["provider_id"]: row for row in status.json()["connectors"]}
    _assert_account_hidden(rows["razorpayx"]["error"])
    assert rows["razorpayx"]["account_hint"] == "••••2837"
    assert "••••2837" in rows["razorpayx"]["error"]


def test_transport_exception_does_not_log_or_store_the_account(client, monkeypatch, caplog):
    http, Session = client
    caplog.set_level(logging.DEBUG)
    _FakeClient.calls = []
    monkeypatch.setattr("server.connectors.razorpayx.httpx.AsyncClient", _RaisingPayouts)
    company_id = _company(
        Session,
        {
            "razorpayx": {
                "connected": True,
                "credentials": {
                    "api_key": "rzp_test",
                    "api_secret": "test-secret",
                    "account_number": ACCOUNT,
                },
            }
        },
    )
    response = http.post(f"/connectors/companies/{company_id}/sync/razorpayx")
    assert response.status_code == 400, response.text
    _assert_account_hidden(response.text)
    assert "before payroll numbers could be read" in response.text

    connectors, _records = _read(Session, company_id)
    last_error = connectors["razorpayx"]["last_error"]
    _assert_account_hidden(last_error)
    assert "before payroll numbers could be read" in last_error
    _assert_account_hidden(caplog.text)
