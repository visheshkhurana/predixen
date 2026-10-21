"""Cross-company revenue must not leak through intelligence responses.

benchmarks and summary used to percentile the newest FinancialRecords across
every company. strategies medians up to 200 peer records. ai-insights put that
peer median in prose, and recommendations copied the sentence. With a small
group those figures are another tenant's exact revenue. None of these
responses may contain company B's revenue. Own-company data stays.

These handlers do not call an LLM, so there is no model prompt to mock.

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


def test_owner_of_a_cannot_see_company_b_revenue_on_intelligence_routes(db, monkeypatch):
    company_a = _add_company(db, OWNER.id, "Company A")
    company_b = _add_company(db, OWNER.id + 1, "Company B")
    _add_revenue(db, company_a.id, A_REVENUE, date(2026, 8, 1), date(2026, 8, 31))
    # Newer than A's row, so the old "newest 500 records" query would include it.
    _add_revenue(db, company_b.id, B_REVENUE, date(2026, 10, 1), date(2026, 10, 31))

    calls = {"benchmarks": 0, "peer_insights": 0}

    def _trap_benchmarks(*args, **kwargs):
        calls["benchmarks"] += 1
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

    def _trap_peer_insights(*args, **kwargs):
        calls["peer_insights"] += 1
        return [{
            "type": "revenue_benchmark",
            "title": "Revenue vs Peers",
            "description": f"peer median of ${B_REVENUE:,.2f}",
            "metric": f"${B_REVENUE:,.0f}",
        }]

    monkeypatch.setattr(intelligence_service, "get_growth_benchmarks", _trap_benchmarks)
    monkeypatch.setattr(intelligence_api, "get_growth_benchmarks", _trap_benchmarks, raising=False)
    monkeypatch.setattr(intelligence_service, "_generate_peer_insights", _trap_peer_insights)

    client = _client(db, OWNER)
    base = f"/companies/{company_a.id}/intelligence"
    benchmarks_resp = client.get(f"{base}/benchmarks")
    summary_resp = client.get(f"{base}/summary")
    strategies_resp = client.get(f"{base}/strategies")
    ai_resp = client.get(f"{base}/ai-insights")
    recommendations_resp = client.post(
        f"{base}/recommendations",
        json={"simulation_result": {"survival_probability": 0.6}},
    )

    responses = {
        "benchmarks": benchmarks_resp,
        "summary": summary_resp,
        "strategies": strategies_resp,
        "ai-insights": ai_resp,
        "recommendations": recommendations_resp,
    }
    for label, resp in responses.items():
        assert resp.status_code == 200, f"{label}: {resp.text}"
    assert calls["benchmarks"] == 0, "cross-company benchmark aggregation must not run"
    assert calls["peer_insights"] == 0, "peer financial insights must not run"

    benchmarks = benchmarks_resp.json()
    summary = summary_resp.json()
    strategies = strategies_resp.json()
    ai_insights = ai_resp.json()
    recommendations = recommendations_resp.json()

    assert benchmarks["stage_benchmarks"] == {}
    assert benchmarks["total_companies_analyzed"] == 0
    assert benchmarks["total_data_points"] == 0
    assert benchmarks["your_profile"]["mrr"] == pytest.approx(A_REVENUE)

    assert summary["growth_benchmarks"] is None
    profile = summary["company_profile"]
    assert profile["company_id"] == company_a.id
    assert profile["name"] == "Company A"
    assert profile["mrr"] == pytest.approx(A_REVENUE)

    assert "strategies" in strategies and "peer_insights" in strategies
    assert strategies["profile_summary"]["stage"] == "seed"
    assert strategies["profile_summary"]["industry"] == "saas"

    assert ai_insights["company_id"] == company_a.id
    assert "insights" in ai_insights
    assert ai_insights["profile"]["mrr"] == pytest.approx(A_REVENUE)

    assert "recommendations" in recommendations
    assert recommendations["profile_summary"]["mrr"] == pytest.approx(A_REVENUE)

    payloads = {
        "benchmarks": benchmarks,
        "summary": summary,
        "strategies": strategies,
        "ai-insights": ai_insights,
        "recommendations": recommendations,
    }
    for label, payload in payloads.items():
        leaked = _contains_foreign_revenue(payload)
        assert leaked is None, f"{label} leaked company B revenue via {leaked}"
