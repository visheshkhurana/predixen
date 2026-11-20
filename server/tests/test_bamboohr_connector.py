"""BambooHR connector and the foreign-currency guard. No network: httpx MockTransport."""

import asyncio
import base64
import json
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from server.api.connectors import _drop_foreign_currency_figures
from server.connectors import bamboohr
from server.connectors.base import ConnectorConfig
from server.connectors.registry import ConnectorRegistry

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


def _conn(**creds):
    base = {"api_key": "key123", "company_domain": "Acme.bamboohr.com"}
    base.update(creds)
    return bamboohr.BambooHRConnector(ConnectorConfig(provider_id="bamboohr", company_id=1, credentials=base))


def _emp(id_, dept, pay="120000.00 USD", per="Year", ptype="Salary", hired=None, ended=None, status="Active"):
    return {"id": str(id_), "displayName": f"Person {id_}", "workEmail": f"p{id_}@acme.io", "department": dept,
            "jobTitle": "Engineer", "employmentHistoryStatus": "Full-Time", "status": status,
            "hireDate": (hired or date(2024, 1, 1)).isoformat(),
            "terminationDate": ended.isoformat() if ended else "0000-00-00",
            "payRate": pay, "payPer": per, "payType": ptype}


EMPLOYEES = [
    _emp(1, "Engineering"),
    _emp(2, "Engineering", hired=TODAY - timedelta(days=10)),
    _emp(3, "Sales", pay="6000.00 USD", per="Month"),
    _emp(4, "Sales", pay="40.00 USD", per="Hour", ptype="Hourly"),
    _emp(5, "Ops", ended=TODAY - timedelta(days=20), status="Inactive"),
]


def _handler(employees=EMPLOYEES, fields_status=200, report_status=200):
    def handler(req):
        if req.url.path.endswith("/meta/fields"):
            return httpx.Response(fields_status, json=[{"id": 1}])
        if req.url.path.endswith("/reports/custom"):
            return httpx.Response(report_status, json={"fields": [], "employees": employees})
        return httpx.Response(404)
    return handler


def test_registered_as_hris():
    assert ConnectorRegistry.get_connector_class("bamboohr") is bamboohr.BambooHRConnector


@pytest.mark.parametrize("raw,expected", [
    ("acme", "acme"), ("acme.bamboohr.com", "acme"), ("https://acme.bamboohr.com/home", "acme"),
    ("ACME", "acme"), ("evil.com/x", ""), ("a b", ""), ("", ""),
])
def test_domain_normalisation(raw, expected):
    assert bamboohr.normalize_bamboo_domain(raw) == expected


@pytest.mark.parametrize("emp,expected", [
    ({"payRate": "120000.00 USD", "payPer": "Year", "payType": "Salary"}, (10000.0, "USD")),
    ({"payRate": "1,200,000 INR", "payPer": "Year"}, (100000.0, "INR")),
    ({"payRate": "6000 EUR", "payPer": "Month", "payType": "Salary"}, (6000.0, "EUR")),
    ({"payRate": "40.00 USD", "payPer": "Hour", "payType": "Hourly"}, (None, None)),
    ({"payRate": "", "payPer": "Year"}, (None, None)),
    ({"payRate": "5000 USD", "payPer": "Pay Period"}, (None, None)),
])
def test_monthly_salary(emp, expected):
    assert bamboohr.monthly_salary(emp) == expected


def test_sync_reports_headcount_moves_and_basic_auth(mock_http):
    seen = mock_http(_handler())
    result = _run(_conn().sync_all())
    assert result.success, result.errors
    assert all(r.url.host == "api.bamboohr.com" and "/gateway.php/acme/v1/" in r.url.path for r in seen)
    assert seen[0].headers["Authorization"] == "Basic " + base64.b64encode(b"key123:x").decode()
    body = json.loads(seen[1].content)
    assert "payRate" in body["fields"] and seen[1].url.params["format"] == "JSON"

    hr = result.metadata["hr_summary"]
    assert hr["headcount"] == 4
    assert hr["by_department"] == {"Engineering": 2, "Sales": 2}
    assert hr["hires_30d"] == 1 and hr["exits_30d"] == 1 and hr["exits_90d"] == 1
    assert hr["salary_run_rate_monthly"] == 10000 + 10000 + 6000
    assert hr["salary_coverage"] == 0.75

    fin = result.metadata["financials"]
    assert fin["headcount"] == 4
    assert "payroll" not in fin  # 3 of 4 salaried < 80%
    assert any("75%" in w for w in result.warnings)
    assert fin["period_start"] == TODAY.replace(day=1).isoformat()


def test_payroll_used_when_coverage_is_high(mock_http):
    mock_http(_handler(employees=EMPLOYEES[:3]))
    fin = _run(_conn().sync_all()).metadata["financials"]
    assert fin["payroll"] == 26000 and fin["payroll_currency"] == "USD"
    assert fin["payroll_basis"] == "salary_run_rate"


def test_other_currencies_are_flagged(mock_http):
    mock_http(_handler(employees=EMPLOYEES[:3] + [_emp(9, "Ops", pay="50000 EUR")]))
    result = _run(_conn().sync_all())
    assert result.metadata["hr_summary"]["other_pay_currencies"] == ["EUR"]
    assert any("EUR" in w for w in result.warnings)


@pytest.mark.parametrize("status,text", [(401, "rejected the API key"), (404, "No BambooHR account at acme"), (403, "can't read employee data")])
def test_auth_errors_are_readable(mock_http, status, text):
    mock_http(_handler(fields_status=status))
    result = _run(_conn().sync_all())
    assert not result.success and text in result.errors[0]


def test_report_failure_and_missing_inputs(mock_http):
    mock_http(_handler(report_status=429))
    assert "rate limiting" in _run(_conn().sync_all()).errors[0]
    seen = mock_http(_handler())
    seen.clear()
    assert "subdomain" in _run(_conn(company_domain="bad_domain").sync_all()).errors[0]
    assert "API key" in _run(_conn(api_key="").sync_all()).errors[0]
    assert seen == []


def test_employee_records(mock_http):
    mock_http(_handler())
    conn = _conn()
    assert _run(conn.authenticate())
    emps = {e.external_id: e for e in _run(conn.fetch_employees())}
    assert emps["1"].salary == 10000 and emps["1"].metadata["currency"] == "USD"
    assert emps["4"].salary is None
    assert emps["5"].status == "inactive" and emps["1"].status == "active"


def test_foreign_currency_figures_are_dropped_with_a_warning():
    warnings = []
    out = _drop_foreign_currency_figures(
        {"payroll": 26000, "payroll_currency": "USD", "headcount": 4, "revenue": 10, "revenue_currency": "inr"},
        "INR", warnings,
    )
    assert "payroll" not in out and out["revenue"] == 10 and out["headcount"] == 4
    assert warnings == ["Payroll is in USD and the company currency is INR, so it was not recorded."]
    assert _drop_foreign_currency_figures({"payroll": 1, "payroll_currency": "USD"}, None, []) == {"payroll": 1, "payroll_currency": "USD"}
