"""Cross-company revenue must not leak through intelligence benchmarks.

GET /companies/{id}/intelligence/benchmarks and
GET /companies/{id}/intelligence/summary used to percentile the newest
FinancialRecords across every company. With a small group, p25/median/p75
are another tenant's exact revenue. Both responses now withhold those
peer stats. Own-company data on the summary stays.

Run: python -m pytest server/tests/test_intelligence_benchmark_privacy.py -q
"""

from __future__ import annotations

import json
import math
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import intelligence_graph as intelligence_api
from server.core.db import Base, get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.models.twin_event import TwinEvent
from server.services import intelligence_graph as intelligence_service

OWNER = SimpleNamespace(
    id=1,
    email="owner-a@example.com",
    is_platform_admin=False,
    is_email_verified=False,
    role="owner",
)

# Distinctive figures. B's revenue must never show up for A's owner, including
# as a percentile. A's revenue is allowed, because it is A's own book.
A_REVENUE = 45123.45
B_REVENUE = 987654.32


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            FinancialRecord.__table__,
            CompanyDecision.__table__,
            TwinEvent.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _client(db, user) -> TestClient:
    app = FastAPI()
    app.include_router(intelligence_api.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _add_company(db, user_id: int, name: str) -> Company:
    company = Company(
        user_id=user_id,
        name=name,
        industry="saas",
        stage="seed",
        currency="USD",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _add_revenue(db, company_id: int, revenue: float, start: date, end: date) -> None:
    db.add(
        FinancialRecord(
            company_id=company_id,
            period_start=start,
            period_end=end,
            revenue=revenue,
            source_type="manual",
        )
    )
    db.commit()


def _legacy_percentiles(values: list[float]) -> list[float]:
    """The old get_growth_benchmarks index selection, not an interpolation."""
    sorted_r = sorted(v for v in values if v > 0)
    n = len(sorted_r)
    if n == 0:
        return []
    return [
        sorted_r[n // 4] if n >= 4 else sorted_r[0],
        sorted_r[n // 2],
        sorted_r[3 * n // 4] if n >= 4 else sorted_r[-1],
    ]


def _contains_foreign_revenue(payload) -> str | None:
    """Return the offending fragment if B's revenue or a percentile of it appears."""
    forbidden_numbers = [B_REVENUE]
    for percentile in _legacy_percentiles([A_REVENUE, B_REVENUE]):
        if math.isclose(percentile, A_REVENUE, rel_tol=0, abs_tol=0.001):
            continue
        forbidden_numbers.append(percentile)

    def walk(node) -> str | None:
        if isinstance(node, bool) or node is None:
            return None
        if isinstance(node, (int, float)):
            for forbidden in forbidden_numbers:
                if math.isclose(float(node), forbidden, rel_tol=0, abs_tol=0.001):
                    return f"numeric {node}"
            return None
        if isinstance(node, str):
            compact = node.replace(",", "").replace("$", "").replace(" ", "")
            if "987654" in compact:
                return node
            return None
        if isinstance(node, dict):
            for value in node.values():
                found = walk(value)
                if found:
                    return found
            return None
        if isinstance(node, list):
            for value in node:
                found = walk(value)
                if found:
                    return found
        return None

    found = walk(payload)
    if found:
        return found
    serialized = json.dumps(payload, default=str)
    compact = serialized.replace(",", "").replace("$", "").replace(" ", "")
    if "987654" in compact or "987654.32" in serialized:
        return serialized
    return None


def test_owner_of_a_cannot_see_company_b_revenue_in_benchmarks_or_summary(db, monkeypatch):
    company_a = _add_company(db, OWNER.id, "Company A")
    company_b = _add_company(db, OWNER.id + 1, "Company B")
    _add_revenue(db, company_a.id, A_REVENUE, date(2026, 8, 1), date(2026, 8, 31))
    # Newer than A's row, so the old "newest 500 records" query would include it.
    _add_revenue(db, company_b.id, B_REVENUE, date(2026, 10, 1), date(2026, 10, 31))

    calls = {"n": 0}

    def _trap(*args, **kwargs):
        calls["n"] += 1
        return {
            "your_profile": {},
            "stage_benchmarks": {
                "seed": {
                    "p25": B_REVENUE,
                    "median": B_REVENUE,
                    "p75": B_REVENUE,
                    "sample_size": 1,
                }
            },
            "total_companies_analyzed": 2,
            "total_data_points": 2,
        }

    monkeypatch.setattr(intelligence_service, "get_growth_benchmarks", _trap)
    monkeypatch.setattr(intelligence_api, "get_growth_benchmarks", _trap, raising=False)

    client = _client(db, OWNER)
    benchmarks_resp = client.get(f"/companies/{company_a.id}/intelligence/benchmarks")
    summary_resp = client.get(f"/companies/{company_a.id}/intelligence/summary")

    assert benchmarks_resp.status_code == 200, benchmarks_resp.text
    assert summary_resp.status_code == 200, summary_resp.text
    assert calls["n"] == 0, "cross-company benchmark aggregation must not run"

    benchmarks = benchmarks_resp.json()
    summary = summary_resp.json()

    assert benchmarks["stage_benchmarks"] == {}
    assert benchmarks["total_companies_analyzed"] == 0
    assert benchmarks["total_data_points"] == 0
    assert benchmarks["your_profile"]["mrr"] == pytest.approx(A_REVENUE)

    assert summary["growth_benchmarks"] is None
    profile = summary["company_profile"]
    assert profile["company_id"] == company_a.id
    assert profile["name"] == "Company A"
    assert profile["mrr"] == pytest.approx(A_REVENUE)

    for label, payload in (("benchmarks", benchmarks), ("summary", summary)):
        leaked = _contains_foreign_revenue(payload)
        assert leaked is None, f"{label} leaked company B revenue via {leaked}"
