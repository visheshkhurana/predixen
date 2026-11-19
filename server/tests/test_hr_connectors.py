"""HR / payroll connectors against their documented APIs (Keka, greytHR, Gusto,
Deel, Rippling, RazorpayX page cap). No network: httpx MockTransport."""

import asyncio
import base64
import urllib.parse
from contextlib import contextmanager

import httpx
import pytest

from server.connectors.base import ConnectorConfig


def _run(coro):
    return asyncio.run(coro)


@contextmanager
def mock_http(handler):
    """Route every httpx.AsyncClient created inside the block through `handler`."""
    orig = httpx.AsyncClient

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    httpx.AsyncClient = Patched
    try:
        yield
    finally:
        httpx.AsyncClient = orig


def _cfg(provider, creds):
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds, settings={})


# --- Keka -----------------------------------------------------------------------

from server.connectors.keka import KekaConnector, normalize_keka_company

KEKA_CREDS = {"company": "acme", "client_id": "cid", "client_secret": "csec", "api_key": "akey"}


def _keka_handler(seen):
    def handler(request: httpx.Request):
        seen.append(request)
        if request.url.host == "login.keka.com":
            assert request.method == "POST" and request.url.path == "/connect/token"
            form = urllib.parse.parse_qs(request.content.decode())
            assert form == {"grant_type": ["kekaapi"], "scope": ["kekaapi"], "client_id": ["cid"],
                            "client_secret": ["csec"], "api_key": ["akey"]}
            assert request.headers.get("user-agent")
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 86400, "token_type": "Bearer"})
        assert request.url.host == "acme.keka.com"
        assert request.headers["authorization"] == "Bearer tok"
        assert request.headers.get("user-agent")
        path = request.url.path
        q = request.url.params
        if path == "/api/v1/hris/employees":
            page = int(q.get("pageNumber"))
            assert int(q.get("pageSize")) <= 200
            if q.get("pageSize") == "1":
                return httpx.Response(200, json={"data": [], "totalPages": 1})
            rows = {
                1: [{"id": "e1", "displayName": "Asha Rao", "email": "asha@acme.in", "joiningDate": "2023-04-01T00:00:00Z",
                     "jobTitle": {"identifier": "j1", "title": "Engineer"}, "exitDate": None, "employeeNumber": "A1"}],
                2: [{"id": "e2", "displayName": "Ravi K", "email": "ravi@acme.in", "joiningDate": "2021-01-10T00:00:00",
                     "jobTitle": {"title": "Ops"}, "exitDate": "2024-01-31T00:00:00", "employeeNumber": "A2"}],
            }[page]
            return httpx.Response(200, json={"data": rows, "pageNumber": page, "totalPages": 2})
        if path == "/api/v1/payroll/salaries":
            return httpx.Response(200, json={"data": [{"employee": {"id": "e1"}, "ctc": 1200000}], "totalPages": 1})
        if path == "/api/v1/payroll/paygroups":
            return httpx.Response(200, json={"data": [{"id": 3, "identifier": "pg-1", "name": "India"}], "totalPages": 1})
        if path == "/api/v1/payroll/paygroups/pg-1/paycycles":
            assert q.get("runStatus") == "Finalized"
            return httpx.Response(200, json={"data": [
                {"identifier": "pc-1", "month": "October", "startDate": "2026-10-01", "endDate": "2026-10-31", "runStatus": 1},
            ], "totalPages": 1})
        if path == "/api/v1/payroll/paygroups/pg-1/paycycles/pc-1/payregister":
            return httpx.Response(200, json={"data": [
                {"identifier": "e1", "grossAmount": 100000, "totalDeductions": 15000, "netAmount": 85000,
                 "totalContributions": 3600, "currencyCode": "INR",
                 "deductions": [{"componentTitle": "PF Employee", "amount": 1800}, {"componentTitle": "TDS", "amount": 13000}],
                 "contributions": [{"componentTitle": "PF Employer", "amount": 1800}]},
                {"identifier": "e3", "grossAmount": 50000, "totalDeductions": 5000, "netAmount": 45000, "currencyCode": "INR"},
            ], "totalPages": 1})
        if path == "/api/v1/payroll/runs" or path == "/health":
            raise AssertionError("undocumented Keka endpoint called")
        return httpx.Response(404)
    return handler


def test_keka_company_normalization():
    assert normalize_keka_company("acme") == "acme"
    assert normalize_keka_company("https://Acme.keka.com/home") == "acme"
    assert normalize_keka_company("acme.keka.com") == "acme"
    assert normalize_keka_company("evil.com/x") == ""
    assert normalize_keka_company("a b") == ""


def test_keka_token_exchange_and_tenant_host():
    seen = []
    conn = KekaConnector(_cfg("keka", KEKA_CREDS))
    with mock_http(_keka_handler(seen)):
        assert _run(conn.authenticate()) is True
    assert seen[0].url.host == "login.keka.com"
    assert str(seen[1].url).startswith("https://acme.keka.com/api/v1/hris/employees")
    assert conn.rotated_credentials() is None


def test_keka_employees_paged_with_job_title_and_ctc():
    seen = []
    conn = KekaConnector(_cfg("keka", KEKA_CREDS))
    with mock_http(_keka_handler(seen)):
        emps = _run(conn.fetch_employees())
    assert [e.external_id for e in emps] == ["e1", "e2"]
    asha, ravi = emps
    assert asha.designation == "Engineer" and asha.salary == 1200000 and asha.status == "active"
    assert asha.join_date.year == 2023 and asha.department is None
    assert ravi.status == "inactive" and ravi.salary is None


def test_keka_payroll_from_pay_register():
    seen = []
    conn = KekaConnector(_cfg("keka", KEKA_CREDS))
    with mock_http(_keka_handler(seen)):
        runs = _run(conn.fetch_payroll_runs())
    assert len(runs) == 1
    run = runs[0]
    assert run.total_gross == 150000 and run.total_deductions == 20000 and run.total_net == 130000
    assert run.employee_count == 2 and run.currency == "INR" and run.status == "completed"
    assert run.breakdown["pf"] == 3600 and run.breakdown["tds"] == 13000
    assert run.period_start.month == 10


def test_keka_old_credentials_ask_to_reconnect_without_network():
    def handler(request):
        raise AssertionError("no request expected")
    conn = KekaConnector(_cfg("keka", {"api_key": "k", "tenant_id": "t", "base_url": "https://api.keka.com"}))
    with mock_http(handler):
        assert _run(conn.authenticate()) is False
        assert _run(conn.fetch_employees()) == []
    assert "reconnected" in conn.auth_error and "acme.keka.com" in conn.auth_error


def test_keka_bad_token_reports_reason():
    def handler(request):
        return httpx.Response(400, json={"error": "invalid_client"})
    conn = KekaConnector(_cfg("keka", KEKA_CREDS))
    with mock_http(handler):
        assert _run(conn.authenticate()) is False
    assert "invalid_client" in conn.auth_error


def test_keka_rejects_hostile_company():
    conn = KekaConnector(_cfg("keka", {**KEKA_CREDS, "company": "evil.example/#"}))
    with mock_http(lambda r: (_ for _ in ()).throw(AssertionError("no request"))):
        assert _run(conn.authenticate()) is False
    assert "acme" in conn.auth_error


# --- greytHR -------------------------------------------------------------------

from server.connectors.greythr import GreytHRConnector, normalize_greythr_domain, summarize_salary_statement

GREYTHR_CREDS = {"domain": "acme", "api_access_id": "apiuser", "api_secret": "pw"}

STATEMENT = [
    {"employeeId": 1, "employeeNo": "5002", "itemName": "INCOME", "description": "GROSS", "amount": 208333, "type": "INCOME", "itemOrder": "/00001/00001"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "BASIC", "amount": 83333, "type": "INCOME", "itemOrder": "/00001/00001/00001"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "DEDUCT", "description": "TOTAL DEDUCTIONS", "amount": -54467, "type": "INCOME", "itemOrder": "/00001/00002"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "PF", "amount": 10000, "type": "DEDUCT", "itemOrder": "/00001/00002/00001"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "INC_TAX", "amount": 44267, "type": "DEDUCT", "itemOrder": "/00001/00002/00004"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "PROF_TAX", "amount": 200, "type": "DEDUCT", "itemOrder": "/00001/00002/00005"},
    {"employeeId": 1, "employeeNo": "5002", "itemName": "FULL_INC", "amount": 208333, "type": "Others", "itemOrder": "/00001/00003"},
    {"employeeId": 2, "employeeNo": "5018", "itemName": "INCOME", "amount": 11851, "type": "INCOME", "itemOrder": "/00001/00001"},
    {"employeeId": 2, "employeeNo": "5018", "itemName": "DEDUCT", "amount": -569, "type": "INCOME", "itemOrder": "/00001/00002"},
    {"employeeId": 2, "employeeNo": "5018", "itemName": "PF", "amount": 569, "type": "DEDUCT", "itemOrder": "/00001/00002/00001"},
]


def _greythr_handler(seen, token_status=200):
    def handler(request: httpx.Request):
        seen.append(request)
        assert request.url.host == "api.greythr.com"
        assert request.headers["x-greythr-domain"] == "acme.greythr.com"
        if request.url.path == "/oauth2/v2/client-token":
            assert request.method == "POST"
            assert request.headers["authorization"] == "Basic " + base64.b64encode(b"apiuser:pw").decode()
            if token_status != 200:
                return httpx.Response(token_status, json={"error": "invalid"})
            return httpx.Response(200, json={"access_token": "gt-tok", "expires_in": 3599, "token_type": "bearer"})
        assert request.headers["access-token"] == "gt-tok"
        q = request.url.params
        if request.url.path == "/employee/v2/employees":
            page = int(q.get("page"))
            if q.get("size") == "1":
                return httpx.Response(200, json={"data": [], "pages": {"totalPages": 1}})
            rows = {
                1: [{"employeeId": 83, "name": "Nandish Shetty", "email": "n@acme.in", "employeeNo": "0001",
                     "dateOfJoin": "2010-01-21", "leftorg": False, "status": 2}],
                2: [{"employeeId": 16, "name": "S Rami Reddy", "email": "r@acme.in", "employeeNo": "5028",
                     "dateOfJoin": "2015-03-14", "leftorg": True, "leavingDate": "2024-02-01", "status": 3}],
            }[page]
            return httpx.Response(200, json={"data": rows, "pages": {"totalPages": 2, "totalElements": 2}})
        if request.url.path.startswith("/payroll/v2/employees/salary/statement/"):
            month = request.url.path.rsplit("/", 1)[-1]
            if month == "2026-09-01":
                return httpx.Response(200, json={"data": STATEMENT, "pages": {"totalPages": 1}})
            return httpx.Response(404, json={"message": "Payroll not processed"})
        return httpx.Response(404)
    return handler


def test_greythr_domain_normalization():
    assert normalize_greythr_domain("acme") == "acme.greythr.com"
    assert normalize_greythr_domain("Acme.greythr.com") == "acme.greythr.com"
    assert normalize_greythr_domain("https://acme.greythr.com/") == "acme.greythr.com"
    assert normalize_greythr_domain("https://api.greythr.com") == ""
    assert normalize_greythr_domain("evil.com/#") == ""


def test_greythr_token_then_access_token_header():
    seen = []
    conn = GreytHRConnector(_cfg("greythr", GREYTHR_CREDS))
    with mock_http(_greythr_handler(seen)):
        assert _run(conn.authenticate()) is True
    assert seen[0].url.path == "/oauth2/v2/client-token"
    assert "x-api-secret" not in seen[1].headers


def test_greythr_employees_use_data_and_pages():
    seen = []
    conn = GreytHRConnector(_cfg("greythr", GREYTHR_CREDS))
    with mock_http(_greythr_handler(seen)):
        emps = _run(conn.fetch_employees())
    assert [(e.name, e.status) for e in emps] == [("Nandish Shetty", "active"), ("S Rami Reddy", "inactive")]
    assert emps[0].join_date.year == 2010 and emps[0].metadata["employee_no"] == "0001"


def test_greythr_salary_statement_summary():
    s = summarize_salary_statement(STATEMENT)
    assert s["gross"] == 208333 + 11851
    assert s["deductions"] == 54467 + 569
    assert s["net"] == s["gross"] - s["deductions"]
    assert s["employee_count"] == 2
    assert s["breakdown"] == {"pf": 10569, "tds": 44267, "professional_tax": 200}


def test_greythr_payroll_per_month_skips_unprocessed():
    from datetime import datetime
    seen = []
    conn = GreytHRConnector(_cfg("greythr", GREYTHR_CREDS))
    with mock_http(_greythr_handler(seen)):
        runs = _run(conn.fetch_payroll_runs(datetime(2026, 8, 1), datetime(2026, 10, 15)))
    months = [r.url.path.rsplit("/", 1)[-1] for r in seen if "statement" in r.url.path]
    assert months == ["2026-08-01", "2026-09-01", "2026-10-01"]
    assert len(runs) == 1 and runs[0].period_start == datetime(2026, 9, 1) and runs[0].period_end.day == 30
    assert runs[0].total_gross == 220184 and runs[0].currency == "INR"


def test_greythr_old_base_url_credentials_still_resolve_domain():
    seen = []
    conn = GreytHRConnector(_cfg("greythr", {"api_access_id": "apiuser", "api_secret": "pw",
                                             "base_url": "https://acme.greythr.com"}))
    with mock_http(_greythr_handler(seen)):
        assert _run(conn.authenticate()) is True


def test_greythr_missing_domain_asks_to_reconnect():
    conn = GreytHRConnector(_cfg("greythr", {"api_access_id": "a", "api_secret": "b", "base_url": "https://api.greythr.com"}))
    with mock_http(lambda r: (_ for _ in ()).throw(AssertionError("no request"))):
        assert _run(conn.authenticate()) is False
    assert "reconnected" in conn.auth_error


def test_greythr_bad_credentials_message():
    conn = GreytHRConnector(_cfg("greythr", GREYTHR_CREDS))
    with mock_http(_greythr_handler([], token_status=401)):
        assert _run(conn.authenticate()) is False
    assert "API Details" in conn.auth_error


# --- Gusto ----------------------------------------------------------------------

from server.connectors.gusto import GustoConnector


def _gusto_handler(seen, resource=None):
    resource = resource if resource is not None else {"type": "Company", "uuid": "co-1"}

    def handler(request: httpx.Request):
        seen.append(request)
        path = request.url.path
        if path == "/v1/me":
            raise AssertionError("/v1/me is deprecated")
        if path == "/v1/token_info":
            return httpx.Response(200, json={"scope": "companies:read", "resource": resource,
                                             "resource_owner": {"type": "CompanyAdmin", "uuid": "u"}})
        if path == "/v1/companies/co-1/payrolls":
            q = request.url.params
            assert q.get("include") == "totals" and q.get("per") == "100"
            page = int(q.get("page"))
            if page == 1:
                batch = [{"payroll_uuid": f"p{i}", "processed": True,
                          "pay_period": {"start_date": "2026-09-01", "end_date": "2026-09-15"},
                          "totals": {"gross_pay": "1000.00", "company_debit": "1300.00", "net_pay": "750.00",
                                     "employee_taxes": "200.00", "employee_benefits_deductions": "50.00",
                                     "employer_taxes": "90.00"}} for i in range(100)]
            else:
                batch = [{"payroll_uuid": "last", "processed": True,
                          "pay_period": {"start_date": "2026-10-01", "end_date": "2026-10-15"},
                          "totals": {"gross_pay": "2000.00", "company_debit": "2600.00", "net_pay": "1500.00"}}]
            return httpx.Response(200, json=batch)
        if path == "/v1/companies/co-1/employees":
            return httpx.Response(200, json=[{"uuid": "emp-1", "first_name": "Jo", "last_name": "Li",
                                              "date_of_birth": "1990-05-05", "hired_at": "2024-02-01",
                                              "terminated": False,
                                              "jobs": [{"primary": True, "title": "PM", "current_compensation_uuid": "c2",
                                                        "compensations": [
                                                            {"uuid": "c1", "rate": "50000", "payment_unit": "Year", "effective_date": "2023-01-01"},
                                                            {"uuid": "c2", "rate": "90000", "payment_unit": "Year", "effective_date": "2025-01-01"}]}]}])
        return httpx.Response(404)
    return handler


def test_gusto_company_from_token_info():
    seen = []
    conn = GustoConnector(_cfg("gusto", {"access_token": "a", "refresh_token": "r"}))
    with mock_http(_gusto_handler(seen)):
        assert _run(conn.authenticate()) is True
    assert conn._company_uuid == "co-1"
    assert [r.url.path for r in seen] == ["/v1/token_info"]


def test_gusto_token_without_company_fails_clearly():
    conn = GustoConnector(_cfg("gusto", {"access_token": "a"}))
    with mock_http(_gusto_handler([], resource={"type": "Oauth::Application", "uuid": "app"})):
        assert _run(conn.authenticate()) is False
    assert "company" in conn.auth_error.lower()


def test_gusto_payrolls_paginated_with_gross_pay():
    seen = []
    conn = GustoConnector(_cfg("gusto", {"access_token": "a"}))
    with mock_http(_gusto_handler(seen)):
        runs = _run(conn.fetch_payroll_runs())
    assert len(runs) == 101
    assert runs[0].total_gross == 1000.0  # gross_pay, not company_debit
    assert runs[0].total_deductions == 250.0 and runs[0].total_net == 750.0
    assert runs[0].breakdown["company_debit"] == 1300.0
    assert runs[-1].total_gross == 2000.0


def test_gusto_employee_hire_date_and_current_compensation():
    conn = GustoConnector(_cfg("gusto", {"access_token": "a"}))
    with mock_http(_gusto_handler([])):
        emps = _run(conn.fetch_employees())
    assert emps[0].join_date.year == 2024  # hired_at, not date_of_birth
    assert emps[0].salary == 90000.0


# --- Deel -----------------------------------------------------------------------

from server.connectors.deel import DeelConnector, annual_compensation


def _deel_handler(seen, invoices=True):
    def handler(request: httpx.Request):
        seen.append(request)
        assert request.url.host == "api.letsdeel.com"
        assert request.url.path.startswith("/rest/")
        path = request.url.path[len("/rest"):]
        q = request.url.params
        if path == "/people":
            if q.get("limit") == "1":
                return httpx.Response(200, json={"data": [], "page": {"offset": 0, "total_rows": 2}})
            offset = int(q.get("offset"))
            rows = [
                {"id": "p1", "full_name": "Alex Rivera", "emails": [{"type": "personal", "value": "a@x.dev"},
                                                                    {"type": "work", "value": "alex@acme.dev"}],
                 "job_title": "Engineer", "department": {"id": "d", "name": "R&D"}, "hiring_status": "active",
                 "start_date": "2025-02-01", "employments": [{"id": "c1"}]},
                {"id": "p2", "full_name": "Sam Ode", "emails": [{"type": "work", "value": "sam@acme.dev"}],
                 "hiring_status": "inactive", "employments": []},
            ][offset:offset + 1]
            return httpx.Response(200, json={"data": rows, "page": {"offset": offset, "total_rows": 2, "items_per_page": 1}})
        if path == "/contracts":
            cursor = q.get("after_cursor")
            if cursor is None:
                return httpx.Response(200, json={"data": [{"id": "c1", "status": "in_progress"}],
                                                 "page": {"cursor": "cur-2", "total_rows": 2}})
            assert cursor == "cur-2"
            return httpx.Response(200, json={"data": [{"id": "c2", "status": "completed"}],
                                             "page": {"cursor": None, "total_rows": 2}})
        if path == "/contracts/c1":
            return httpx.Response(200, json={"data": {"id": "c1", "worker": {"email": "alex@acme.dev"},
                                                      "compensation_details": {"amount": 8000, "currency_code": "GBP",
                                                                               "frequency": "monthly"}}})
        if path == "/invoices":
            assert q.get("issued_from_date")
            assert "from_date" not in q
            if not invoices:
                return httpx.Response(200, json={"data": [], "page": {"offset": 0, "total_rows": 0}})
            return httpx.Response(200, json={"data": [
                {"id": "i1", "total": "8400", "amount": "8000", "deel_fee": "400", "currency": "GBP", "status": "paid",
                 "issued_at": "2026-09-28", "paid_at": "2026-10-02", "contract_id": "c1"},
                {"id": "i2", "total": "8400", "amount": "8000", "deel_fee": "400", "currency": "GBP", "status": "paid",
                 "issued_at": "2026-10-28", "paid_at": "2026-11-01", "contract_id": "c1"},
            ], "page": {"offset": 0, "total_rows": 2}})
        return httpx.Response(404)
    return handler


def test_deel_annual_compensation():
    assert annual_compensation({"amount": 8000, "currency_code": "GBP", "frequency": "monthly"}) == (96000, "GBP")
    assert annual_compensation({"gross_annual_salary": 120000, "currency_code": "USD"}) == (120000, "USD")
    assert annual_compensation({}) is None


def test_deel_people_offset_paging_emails_and_salary_from_contract():
    seen = []
    conn = DeelConnector(_cfg("deel", {"api_key": "k"}))
    with mock_http(_deel_handler(seen)):
        emps = _run(conn.fetch_employees())
    assert [e.external_id for e in emps] == ["p1", "p2"]
    assert emps[0].email == "alex@acme.dev" and emps[0].department == "R&D"
    assert emps[0].salary == 96000 and emps[0].metadata["salary_currency"] == "GBP"
    assert emps[1].status == "inactive"
    # only the active contract's detail is fetched; contracts paged by cursor
    detail_calls = [r.url.path for r in seen if r.url.path.startswith("/rest/contracts/")]
    assert detail_calls == ["/rest/contracts/c1"]


def test_deel_payroll_from_paid_invoices_and_not_revenue():
    conn = DeelConnector(_cfg("deel", {"api_key": "k"}))
    with mock_http(_deel_handler([])):
        result = _run(conn.sync_all())
    assert result.success
    fin = result.metadata["financials"]
    assert "revenue" not in fin
    assert fin["payroll"] == 8400 and fin["payroll_runs_count"] == 2
    assert fin["contractor_invoices_total"] == 16800


def test_deel_payroll_falls_back_to_contract_compensation():
    conn = DeelConnector(_cfg("deel", {"api_key": "k"}))
    with mock_http(_deel_handler([], invoices=False)):
        runs = _run(conn.fetch_payroll_runs())
    assert len(runs) == 1 and runs[0].status == "estimated"
    assert runs[0].total_gross == 8000 and runs[0].currency == "GBP"


# --- Rippling -------------------------------------------------------------------

from server.connectors.rippling import RipplingConnector


def test_rippling_v2_workers_follow_next_link_and_skip_payroll():
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        assert request.url.host == "rest.ripplingapis.com"
        assert not request.url.path.startswith("/platform/api")
        assert request.url.path == "/workers"
        q = request.url.params
        if q.get("limit") == "1":
            return httpx.Response(200, json={"results": []})
        if q.get("cursor") is None:
            assert q.get("limit") == "100" and "compensation" in q.get("expand")
            return httpx.Response(200, json={"results": [{
                "id": "w1", "work_email": "a@acme.com", "status": "ACTIVE", "title": "CTO", "start_date": "2024-01-01",
                "user": {"display_name": "Ana"}, "department": {"name": "Eng"},
                "compensation": {"annual_compensation": {"currency_type": "USD", "value": 180000}}}],
                "next_link": "https://rest.ripplingapis.com/workers?cursor=abc&limit=100&expand=user,department,compensation"})
        assert q.get("cursor") == "abc"
        return httpx.Response(200, json={"results": [{
            "id": "w2", "work_email": "b@acme.com", "status": "TERMINATED", "user": {"display_name": "Bo"},
            "compensation": {"annual_compensation": {"currency_type": "USD", "value": 90000}}}], "next_link": None})

    conn = RipplingConnector(_cfg("rippling", {"api_key": "tok"}))
    with mock_http(handler):
        result = _run(conn.sync_all())
        assert _run(conn.fetch_payroll_runs()) == []
    assert result.success
    fin = result.metadata["financials"]
    assert fin["headcount"] == 1 and fin["annual_payroll"] == 180000 and fin["payroll"] == 15000
    assert RipplingConnector.SUPPORTS_PAYROLL is False


def test_rippling_refuses_off_host_next_link():
    conn = RipplingConnector(_cfg("rippling", {"api_key": "tok"}))
    assert conn._next_request("https://evil.example/workers?cursor=x") is None
    assert conn._next_request("https://rest.ripplingapis.com/workers?cursor=x") == "/workers?cursor=x"
    assert conn._next_request("/workers?cursor=y") == "/workers?cursor=y"


def test_rippling_rejected_token_message():
    conn = RipplingConnector(_cfg("rippling", {"api_key": "old-v1-key"}))
    with mock_http(lambda r: httpx.Response(401, json={"detail": "nope"})):
        assert _run(conn.authenticate()) is False
    assert "workers.read" in conn.auth_error


# --- RazorpayX page cap ---------------------------------------------------------

def test_razorpayx_page_cap_raised_and_logged(caplog, monkeypatch):
    import logging
    from server.connectors import razorpayx
    assert razorpayx.MAX_PAGES * razorpayx.PAGE_SIZE >= 10000
    monkeypatch.setattr(razorpayx, "MAX_PAGES", 2)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"items": [{"id": str(i)} for i in range(razorpayx.PAGE_SIZE)]})

    conn = razorpayx.RazorpayXConnector(_cfg("razorpayx", {"api_key": "k", "api_secret": "s", "account_number": "7878780080316316"}))
    with mock_http(handler), caplog.at_level(logging.WARNING, logger="server.connectors.razorpayx"):
        items = _run(conn._collect("/payouts", {}))
    assert len(items) == 2 * razorpayx.PAGE_SIZE and len(calls) == 2
    assert any("page cap" in r.getMessage() for r in caplog.records)


def test_old_keka_connection_sync_reports_reconnect_message():
    conn = KekaConnector(_cfg("keka", {"api_key": "k", "tenant_id": "t"}))
    result = _run(conn.sync_all())
    assert not result.success and "reconnected" in result.errors[0]
