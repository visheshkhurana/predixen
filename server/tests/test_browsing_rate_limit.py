"""Signed-in browsing must stay inside the read budget.

A main sidebar page mounts the app shell plus that page's react-query hooks.
The shell alone is companies, scenarios, decisions, smart-alerts, computed
metrics, truth/latest, and baseline. Six of those pages a minute used to trip
the single 60/min bucket. This replays the calls the client actually fires.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from jose import jwt
from starlette.requests import Request

from server.core.config import settings
from server.middleware.rate_limiter import (
    AUTH_COOKIE_NAME,
    CORS_EXPOSE_HEADERS,
    RateLimiterMiddleware,
)

REPO = Path(__file__).resolve().parents[2]
CLIENT = REPO / "client" / "src"

API_CALLS = {
    "api.companies.list": ("GET", "/companies"),
    "api.truth.latest": ("GET", "/companies/{id}/truth/latest"),
    "api.metrics.computed": ("GET", "/companies/{id}/metrics/computed"),
    "api.decisions.latest": ("GET", "/companies/{id}/decisions/latest"),
    "api.scenarios.list": ("GET", "/companies/{id}/scenarios"),
    "api.benchmarks.search": ("POST", "/benchmarks/search"),
    "api.benchmarks.industries": ("GET", "/benchmarks/industries"),
    "api.decisions.strategicDiagnosis": ("GET", "/companies/{id}/strategic-diagnosis"),
    "api.simulations.latest": ("GET", "/scenarios/{id}/simulation/latest"),
    "api.simulations.getTimeseries": ("GET", "/scenarios/{id}/timeseries"),
    "api.dashboard.kpis": ("GET", "/dashboard/companies/{id}/kpis"),
}

# Hooks whose useQuery calls fire on mount when a company is selected.
QUERY_HOOKS = {
    "useFinancialMetrics": CLIENT / "hooks" / "useFinancialMetrics.ts",
    "useCompanies": CLIENT / "api" / "hooks.ts",
    "useTruthScan": CLIENT / "api" / "hooks.ts",
    "useDecisions": CLIENT / "api" / "hooks.ts",
    "useScenarios": CLIENT / "api" / "hooks.ts",
    "useBenchmarkSearch": CLIENT / "api" / "hooks.ts",
    "useBenchmarkIndustries": CLIENT / "api" / "hooks.ts",
    "useStrategicDiagnosisQuery": CLIENT / "api" / "hooks.ts",
    "useSimulation": CLIENT / "api" / "hooks.ts",
    "useScenarioTimeseries": CLIENT / "api" / "hooks.ts",
}

# Shell is mounted on every signed-in page. Simulate's default tab is
# Scenarios, and inactive Radix tabs unmount, so History is not in the load.
PAGES = [
    ("Dashboard", "/overview", [(CLIENT / "pages" / "overview.tsx", "OverviewPage")]),
    ("Simulate", "/simulate", [
        (CLIENT / "pages" / "simulate-workspace.tsx", "SimulateWorkspace"),
        (CLIENT / "pages" / "scenarios.tsx", "ScenariosPage"),
    ]),
    ("Decisions", "/decisions", [(CLIENT / "pages" / "decisions.tsx", "DecisionsPage")]),
    ("Alerts", "/alerts", [(CLIENT / "pages" / "alerts.tsx", "AlertsPage")]),
    ("Cap Table", "/cap-table", [(CLIENT / "pages" / "cap-table.tsx", "CapTablePage")]),
    ("Fundraising", "/fundraising", [(CLIENT / "pages" / "fundraising.tsx", "FundraisingPage")]),
    ("Investor Room", "/investor-room", [(CLIENT / "pages" / "investor-room.tsx", "InvestorRoomPage")]),
    ("Hiring Planner", "/hiring", [(CLIENT / "pages" / "hiring-planner.tsx", "HiringPlannerPage")]),
    ("Digital Twin", "/digital-twin", [(CLIENT / "pages" / "digital-twin.tsx", "DigitalTwinPage")]),
    ("KPI Dashboards", "/dashboards", [(CLIENT / "pages" / "dashboards.tsx", "DashboardsPage")]),
    ("Competition", "/competition", [(CLIENT / "pages" / "competition.tsx", "CompetitionPage")]),
    ("Health Check", "/truth", [(CLIENT / "pages" / "truth-scan.tsx", "TruthScanPage")]),
    ("Data Input", "/data", [(CLIENT / "pages" / "data-input.tsx", "DataInput")]),
    ("Integrations", "/integrations", [(CLIENT / "pages" / "integrations.tsx", "IntegrationsPage")]),
]

SHELL = [
    (CLIENT / "components" / "app-sidebar.tsx", "AppSidebar"),
    (CLIENT / "components" / "CompanySwitcher.tsx", "CompanySwitcher"),
    (CLIENT / "App.tsx", "AppLayout"),
]

RATE_ENV = (
    "RATE_LIMIT_AUTH",
    "RATE_LIMIT_ADMIN_LOGIN",
    "RATE_LIMIT_API",
    "RATE_LIMIT_UPLOAD",
    "RATE_LIMIT_SIMULATION",
    "RATE_LIMIT_READ",
    "RATE_LIMIT_READ_BURST",
    "RATE_LIMIT_LLM",
    "RATE_LIMIT_EMAIL",
)


@dataclass(frozen=True)
class ApiCall:
    method: str
    path: str
    dedupe: tuple
    source: str

    def concrete(self) -> str:
        return self.path.replace("{id}", "7")


def _skip_string(src: str, i: int) -> int:
    quote = src[i]
    i += 1
    while i < len(src):
        if src[i] == "\\":
            i += 2
            continue
        if src[i] == quote:
            return i + 1
        i += 1
    return i


def _skip_template(src: str, i: int) -> int:
    """i points at the opening backtick."""
    i += 1
    while i < len(src):
        if src[i] == "\\":
            i += 2
            continue
        if src[i] == "`":
            return i + 1
        if src[i] == "$" and i + 1 < len(src) and src[i + 1] == "{":
            i = _match_brace(src, i + 1)[1]
            continue
        i += 1
    return i


def _match_brace(src: str, open_at: int) -> tuple[str, int]:
    """src[open_at] is { or (. Returns the inclusive text and the index after it."""
    opener = src[open_at]
    closer = "}" if opener == "{" else ")"
    depth = 0
    i = open_at
    while i < len(src):
        c = src[i]
        if c in "\"'":
            i = _skip_string(src, i)
            continue
        if c == "`":
            i = _skip_template(src, i)
            continue
        if c == "/" and i + 1 < len(src) and src[i + 1] == "/":
            nxt = src.find("\n", i)
            i = len(src) if nxt < 0 else nxt + 1
            continue
        if c == "/" and i + 1 < len(src) and src[i + 1] == "*":
            nxt = src.find("*/", i + 2)
            i = len(src) if nxt < 0 else nxt + 2
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return src[open_at : i + 1], i + 1
        i += 1
    return src[open_at:], len(src)


def _skip_generics(src: str, i: int) -> int:
    depth = 0
    brace = 0
    while i < len(src):
        c = src[i]
        if c in "\"'":
            i = _skip_string(src, i)
            continue
        if c == "`":
            i = _skip_template(src, i)
            continue
        if c == "{":
            brace += 1
        elif c == "}":
            brace = max(0, brace - 1)
        elif c == "<" and brace == 0:
            depth += 1
        elif c == ">" and brace == 0:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _calls(src: str) -> list[tuple[str, int]]:
    found = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            i = _skip_string(src, i)
            continue
        if c == "`":
            i = _skip_template(src, i)
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            nxt = src.find("\n", i)
            i = n if nxt < 0 else nxt + 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            nxt = src.find("*/", i + 2)
            i = n if nxt < 0 else nxt + 2
            continue
        if c.isalpha() or c in "_$":
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            name = src[i:j]
            k = j
            while k < n and src[k] in " \t\n\r":
                k += 1
            if k < n and src[k] == "<":
                k = _skip_generics(src, k)
                while k < n and src[k] in " \t\n\r":
                    k += 1
            if k < n and src[k] == "(":
                found.append((name, k))
            i = j
            continue
        i += 1
    return found


def _slice_function(src: str, name: str) -> str:
    match = re.search(rf"(?m)^(?:export\s+default\s+function|export\s+function|function)\s+{re.escape(name)}\b", src)
    if not match:
        raise AssertionError(f"function {name} not found")
    rest = src[match.end() :]
    nxt = re.search(r"(?m)^(?:export\s+default\s+function|export\s+function|async\s+function|function)\s+", rest)
    end = match.end() + nxt.start() if nxt else len(src)
    return src[match.start() : end]


def _normalize_path(path: str) -> str:
    text = path.strip()
    # ${selectedCompany?.id} contains a '?' from optional chaining. Substitute
    # the template before treating '?' as a query string.
    text = re.sub(r"\$\{[^}]*\}", "{id}", text)
    text = text.split("?", 1)[0].strip()
    if text.startswith("/api/"):
        text = text[4:]
    elif text == "/api":
        text = "/"
    if len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text or "/"


def _query_key_parts(block: str) -> Optional[list[str]]:
    match = re.search(r"queryKey\s*:\s*", block)
    if not match:
        return None
    rest = block[match.end() :]
    if rest.startswith("["):
        array, _ = _match_brace_general(rest, 0, "[", "]")
        return _split_key(array[1:-1])
    if rest.startswith(("'", '"', "`")):
        return [_normalize_key_piece(rest)]
    return None


def _match_brace_general(src: str, open_at: int, opener: str, closer: str) -> tuple[str, int]:
    depth = 0
    i = open_at
    while i < len(src):
        c = src[i]
        if c in "\"'":
            i = _skip_string(src, i)
            continue
        if c == "`":
            i = _skip_template(src, i)
            continue
        if c == "/" and i + 1 < len(src) and src[i + 1] == "/":
            nxt = src.find("\n", i)
            i = len(src) if nxt < 0 else nxt + 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return src[open_at : i + 1], i + 1
        i += 1
    return src[open_at:], len(src)


def _split_key(inner: str) -> list[str]:
    parts = []
    i = 0
    n = len(inner)
    while i < n:
        while i < n and inner[i] in " \t\n\r,":
            i += 1
        if i >= n:
            break
        if inner[i] in "\"'":
            start = i
            i = _skip_string(inner, i)
            parts.append(inner[start + 1 : i - 1])
            continue
        if inner[i] == "`":
            start = i
            i = _skip_template(inner, i)
            parts.append(re.sub(r"\$\{[^}]*\}", "{id}", inner[start + 1 : i - 1]))
            continue
        start = i
        depth = 0
        while i < n:
            if inner[i] in "\"'":
                i = _skip_string(inner, i)
                continue
            if inner[i] == "`":
                i = _skip_template(inner, i)
                continue
            if inner[i] in "([{":
                depth += 1
            elif inner[i] in ")]}":
                depth = max(0, depth - 1)
            elif inner[i] == "," and depth == 0:
                break
            else:
                i += 1
                continue
            i += 1
        if inner[start:i].strip():
            parts.append("{id}")
    return parts


def _normalize_key_piece(raw: str) -> str:
    if raw[0] in "\"'":
        return raw[1 : raw.index(raw[0], 1)]
    if raw[0] == "`":
        end = raw.index("`", 1)
        return re.sub(r"\$\{[^}]*\}", "{id}", raw[1:end])
    return "{id}"


def _explicit_url(block: str) -> Optional[str]:
    """URL passed to fetch / fetchJson / apiRequest, not a queryKey segment."""
    patterns = (
        r"fetchJson\(\s*[`'\"]([^`'\"]+)[`'\"]",
        r"\bfetch\(\s*[`'\"]([^`'\"]+)[`'\"]",
        r"apiRequest\(\s*['\"]\w+['\"]\s*,\s*[`'\"]([^`'\"]+)[`'\"]",
    )
    for pattern in patterns:
        match = re.search(pattern, block)
        if match and match.group(1).startswith("/"):
            return match.group(1)
    return None


def _path_from_key(parts: list[str]) -> Optional[str]:
    if not parts:
        return None
    first = parts[0]
    if not (first.startswith("/") or first.startswith("api")):
        return None
    joined = "/".join(parts)
    if not joined.startswith("/"):
        joined = f"/{joined}"
    return _normalize_path(joined)


def _call_from_block(block: str, source: str) -> Optional[ApiCall]:
    if "fully_diluted" in block and "!==" in block:
        return None
    api = re.search(r"\bapi\.(\w+)\.(\w+)", block)
    method = "GET"
    path = None
    if api:
        mapped = API_CALLS.get(f"api.{api.group(1)}.{api.group(2)}")
        if mapped:
            method, path = mapped
    if path is None:
        request = re.search(r"apiRequest\(\s*['\"](\w+)['\"]", block)
        if request:
            method = request.group(1).upper()
        url = _explicit_url(block)
        if url:
            path = _normalize_path(url)
    parts = _query_key_parts(block)
    if path is None and parts:
        path = _path_from_key(parts)
    if path is None:
        return None
    if parts:
        dedupe = (method, tuple(re.sub(r"\$\{[^}]*\}", "{id}", p).split("?", 1)[0] for p in parts))
    else:
        dedupe = (method, (path,))
    return ApiCall(method, path, dedupe, source)


def _queries_in(src: str, source: str) -> list[ApiCall]:
    calls = []
    for name, paren in _calls(src):
        if name == "useQuery":
            obj = _object_after(src, paren)
            if not obj:
                continue
            parsed = _call_from_block(obj, source)
            if parsed:
                calls.append(parsed)
        elif name in QUERY_HOOKS:
            calls.extend(_hook_queries(name))
    return calls


_HOOK_CACHE: dict[str, list[ApiCall]] = {}


def _hook_queries(name: str) -> list[ApiCall]:
    cached = _HOOK_CACHE.get(name)
    if cached is not None:
        return cached
    path = QUERY_HOOKS[name]
    body = _slice_function(path.read_text(), name)
    found = []
    for call_name, paren in _calls(body):
        if call_name != "useQuery":
            continue
        obj = _object_after(body, paren)
        if not obj:
            continue
        parsed = _call_from_block(obj, f"{path.name}:{name}")
        if parsed:
            found.append(parsed)
    _HOOK_CACHE[name] = found
    return found


def _object_after(src: str, paren_at: int) -> Optional[str]:
    i = paren_at + 1
    while i < len(src) and src[i] in " \t\n\r":
        i += 1
    if i >= len(src) or src[i] != "{":
        return None
    text, _ = _match_brace(src, i)
    return text


def _unique(calls: list[ApiCall]) -> list[ApiCall]:
    seen = set()
    out = []
    for call in calls:
        if call.dedupe in seen:
            continue
        seen.add(call.dedupe)
        out.append(call)
    return out


def page_loads() -> list[tuple[str, str, list[ApiCall]]]:
    shell: list[ApiCall] = []
    for path, name in SHELL:
        shell.extend(_queries_in(_slice_function(path.read_text(), name), f"{path.name}:{name}"))
    shell = _unique(shell)
    loads = []
    for label, route, slices in PAGES:
        calls = list(shell)
        for path, name in slices:
            calls.extend(_queries_in(_slice_function(path.read_text(), name), f"{path.name}:{name}"))
        loads.append((label, route, _unique(calls)))
    return loads


def _token(sub: str) -> str:
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(hours=2)}
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded if isinstance(encoded, str) else encoded.decode()


def _request(path: str, method: str = "GET", token: Optional[str] = None, peer: str = "203.0.113.40") -> Request:
    headers = []
    if token:
        headers.append((b"cookie", f"{AUTH_COOKIE_NAME}={token}".encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": (peer, 5000),
        "server": ("testserver", 80),
        "extensions": {"peer_host": peer},
    }
    return Request(scope)


async def _dispatch(middleware: RateLimiterMiddleware, request: Request) -> int:
    async def _ok(_request):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, _ok)
    return response.status_code


def _run(coro):
    async def _wrapped():
        try:
            return await coro
        finally:
            current = asyncio.current_task()
            pending = [task for task in asyncio.all_tasks() if task is not current]
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

    return asyncio.run(_wrapped())


def _limiter(clock: list, **kwargs) -> RateLimiterMiddleware:
    return RateLimiterMiddleware(app=None, clock=lambda: clock[0], **kwargs)


@pytest.fixture(autouse=True)
def _db_down(monkeypatch):
    for name in RATE_ENV:
        monkeypatch.delenv(name, raising=False)
    def _down():
        raise RuntimeError("rate limit database unavailable")
    monkeypatch.setattr("server.middleware.rate_limiter._get_engine", _down)
    log = logging.getLogger("server.middleware.rate_limiter")
    previous = log.level
    log.setLevel(logging.CRITICAL)
    yield
    log.setLevel(previous)


def test_client_paths_match_the_api_map():
    src = (CLIENT / "api" / "client.ts").read_text()
    assert "request<any>('/companies')" in src
    assert "`/companies/${companyId}/truth/latest`" in src
    assert "`/companies/${companyId}/metrics/computed`" in src
    assert "`/companies/${companyId}/decisions/latest`" in src
    assert "`/companies/${companyId}/scenarios`" in src
    assert "'/benchmarks/search'" in src
    assert "'/benchmarks/industries'" in src
    assert "strategic-diagnosis" in src
    assert "`/scenarios/${scenarioId}/simulation/latest`" in src
    assert "`/scenarios/${scenarioId}/timeseries`" in src
    assert "`/dashboard/companies/${companyId}/kpis`" in src
    security = (REPO / "server" / "core" / "security.py").read_text()
    assert f'AUTH_COOKIE_NAME = "{AUTH_COOKIE_NAME}"' in security
    main = (REPO / "server" / "main.py").read_text()
    assert "expose_headers=CORS_EXPOSE_HEADERS" in main
    financials = (CLIENT / "hooks" / "useFinancialMetrics.ts").read_text()
    assert "queryKey: ['truth', companyId]" in financials
    assert "queryKey: ['financials-baseline', companyId]" in financials
    assert "refetchOnWindowFocus: true" not in financials
    hiring = (CLIENT / "pages" / "hiring-planner.tsx").read_text()
    assert "useTruthScan(companyId ?? null)" in hiring
    data_input = (CLIENT / "pages" / "data-input.tsx").read_text()
    assert "['financials-baseline', currentCompany?.id]" in data_input
    query_client = (CLIENT / "lib" / "queryClient.ts").read_text()
    assert "refetchOnWindowFocus: false" in query_client
    assert "error.status === 429" in query_client


def test_page_load_catalog_and_session_budget():
    loads = page_loads()
    by_count = sorted(loads, key=lambda item: len(item[2]), reverse=True)
    print("\nPER-PAGE API CALLS (shell + page, deduped by react-query key)")
    audited = {
        "/companies",
        "/companies/{id}/truth/latest",
        "/companies/{id}/metrics/computed",
        "/companies/{id}/financials/baseline",
    }
    shell_paths = {call.path for call in by_count[0][2]}
    for label, route, calls in by_count:
        print(f"{len(calls):3d}  {label}  {route}")
        for call in calls:
            print(f"     {call.method:4s} {call.path}")
    assert audited <= shell_paths
    shell_only = next(calls for label, _route, calls in loads if label == "Data Input")
    shell_only_paths = {call.path for call in shell_only}
    assert "/companies/{id}/decisions" in shell_only_paths
    assert "/companies/{id}/smart-alerts" in shell_only_paths
    cap = next(calls for label, _route, calls in loads if label == "Cap Table")
    assert "/companies/{id}/cap-table/summary" in {call.path for call in cap}
    assert "/companies/{id}/cap-table/summary-409a" in {call.path for call in cap}
    alerts = next(calls for label, _route, calls in loads if label == "Alerts")
    assert "/alerts/companies/{id}/alerts" in {call.path for call in alerts}
    assert "/alerts/companies/{id}/analyze" in {call.path for call in alerts}
    fundraising = next(calls for label, _route, calls in loads if label == "Fundraising")
    assert "/companies/{id}/cap-tables" in {call.path for call in fundraising}
    assert "/companies/{id}/fundraising/rounds" in {call.path for call in fundraising}
    heaviest = by_count[0][2]
    assert len(heaviest) >= 15
    assert len(heaviest) <= 40
    for _label, _route, calls in loads:
        assert len(calls) >= 7
        assert len(calls) <= 40

    cycle = by_count[:6]
    token = _token("browse-session")
    clock = [1_000_000.0]
    middleware = _limiter(clock)
    read_counts = []
    for _label, _route, calls in cycle:
        reads = 0
        for call in calls:
            category, _limit = middleware._get_category(
                _request(call.concrete(), call.method, token)
            )
            if category == "read":
                reads += 1
        read_counts.append(reads)
    minute_reads = sum(read_counts)
    print(f"SIX HEAVIEST READS/MIN {minute_reads} PAGE READS {read_counts}")
    assert minute_reads > 60
    assert minute_reads * 3 <= middleware.rate_limit_read
    assert max(read_counts) * 3 <= middleware.rate_limit_read_burst
    assert middleware.rate_limit_read == 480
    assert middleware.rate_limit_read_burst == 120

    async def _session():
        statuses = []
        for _minute in range(2):
            for _label, _route, calls in cycle:
                for call in calls:
                    statuses.append(
                        await _dispatch(
                            middleware,
                            _request(call.concrete(), call.method, token, peer="203.0.113.77"),
                        )
                    )
                clock[0] += 10
        return statuses

    statuses = _run(_session())
    assert statuses, "session fired no calls"
    assert 429 not in statuses, statuses.count(429)
    assert set(statuses) == {200}


def test_previous_60_per_minute_budget_returns_429():
    loads = sorted(page_loads(), key=lambda item: len(item[2]), reverse=True)
    cycle = loads[:6]
    token = _token("browse-old-cap")
    clock = [2_000_000.0]
    middleware = _limiter(clock, rate_limit_read=60, rate_limit_read_burst=60)

    async def _one_minute():
        statuses = []
        for _label, _route, calls in cycle:
            for call in calls:
                statuses.append(
                    await _dispatch(
                        middleware,
                        _request(call.concrete(), call.method, token, peer="203.0.113.78"),
                    )
                )
            clock[0] += 10
        return statuses

    statuses = _run(_one_minute())
    assert 429 in statuses
    assert statuses.count(200) >= 60


def test_categories_keep_abuse_routes_strict():
    middleware = _limiter([0.0])
    token = _token("category-user")

    def category(path, method="GET", authed=False):
        return middleware._get_category(_request(path, method, token if authed else None))

    assert category("/companies", authed=True) == ("read", 480)
    assert category("/api/companies/7/truth/latest", authed=True)[0] == "read"
    assert category("/companies") == ("api", 60)
    assert category("/auth/login", "POST") == ("auth", 5)
    assert category("/auth/register", "POST") == ("auth", 5)
    assert category("/auth/forgot-password", "POST") == ("auth", 5)
    assert category("/auth/reset-password", "POST") == ("auth", 5)
    assert category("/auth/admin/login", "POST") == ("admin_auth", 3)
    assert category("/leads", "POST") == ("leads", 8)
    assert category("/api/leads", "POST") == ("leads", 8)
    assert category("/leads", "GET")[0] == "api"
    assert category("/companies/7/strategic-diagnosis", authed=True) == ("llm", 20)
    assert category("/scenarios/7/simulate", "POST", authed=True) == ("simulation", 10)
    assert category("/companies/7/truth/run", "POST", authed=True) == ("simulation", 10)
    assert category("/auth/send-verification", "POST") == ("email", 5)
    assert category("/companies/7/digest/send", "POST", authed=True) == ("email", 5)
    assert category("/companies/7/financials/csv-import", "POST", authed=True) == ("upload", 10)
    assert category("/health")[0] == "health"
    assert "Retry-After" in CORS_EXPOSE_HEADERS
    assert "RateLimit-Limit" in CORS_EXPOSE_HEADERS


def test_read_burst_rejects_without_counting_and_users_do_not_share_a_bucket():
    clock = [3_000_000.0]
    middleware = _limiter(clock, rate_limit_read=100, rate_limit_read_burst=2)
    alice = _token("burst-alice")
    bob = _token("burst-bob")
    peer = "203.0.113.90"

    async def _burst():
        ok = []
        for _ in range(2):
            ok.append(await _dispatch(middleware, _request("/companies", token=alice, peer=peer)))
        rejected = []
        for _ in range(3):
            clock[0] = 3_000_001.0
            rejected.append(await _dispatch(middleware, _request("/companies", token=alice, peer=peer)))
        clock[0] = 3_000_010.0
        after = await _dispatch(middleware, _request("/companies", token=alice, peer=peer))
        other = await _dispatch(middleware, _request("/companies", token=bob, peer=peer))
        return ok, rejected, after, other

    ok, rejected, after, other = _run(_burst())
    assert ok == [200, 200]
    assert rejected == [429, 429, 429]
    assert after == 200
    assert other == 200


def test_anonymous_ip_cap_does_not_spend_the_signed_in_read_budget():
    clock = [4_000_000.0]
    middleware = _limiter(clock)
    peer = "198.51.100.40"
    token = _token("reader-after-anon")

    async def _mix():
        anon = [
            await _dispatch(middleware, _request("/companies", peer=peer))
            for _ in range(70)
        ]
        authed = await _dispatch(middleware, _request("/companies", token=token, peer=peer))
        return anon, authed

    anon, authed = _run(_mix())
    assert anon[:60] == [200] * 60
    assert anon[60:] == [429] * 10
    assert authed == 200


def test_one_hundred_login_attempts_are_blocked():
    clock = [5_000_000.0]
    middleware = _limiter(clock)
    peer = "198.51.100.10"

    async def _logins():
        return [
            await _dispatch(middleware, _request("/auth/login", "POST", peer=peer))
            for _ in range(100)
        ]

    statuses = _run(_logins())
    assert statuses[:5] == [200] * 5
    assert statuses[5:] == [429] * 95


def test_one_hundred_lead_posts_are_blocked():
    clock = [6_000_000.0]
    middleware = _limiter(clock)
    peer = "198.51.100.20"

    async def _leads():
        return [
            await _dispatch(middleware, _request("/api/leads", "POST", peer=peer))
            for _ in range(100)
        ]

    statuses = _run(_leads())
    assert statuses[:8] == [200] * 8
    assert statuses[8:] == [429] * 92


def test_cors_exposes_retry_after_on_429():
    app = FastAPI()

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    app.add_middleware(RateLimiterMiddleware, rate_limit_auth=1)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://founderconsole.ai"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=CORS_EXPOSE_HEADERS,
    )
    client = TestClient(app)
    origin = {"Origin": "https://founderconsole.ai"}
    first = client.post("/auth/login", headers=origin)
    second = client.post("/auth/login", headers=origin)
    assert first.status_code == 200
    assert second.status_code == 429
    exposed = second.headers.get("access-control-expose-headers", "")
    assert "Retry-After" in exposed
    assert "RateLimit-Limit" in exposed
    assert "X-RateLimit-Limit" in exposed
    assert second.headers.get("retry-after")
    assert second.json()["retry_after"] >= 1
    assert "Retry-After" in first.headers.get("access-control-expose-headers", "")
