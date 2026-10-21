"""Peer revenue bands and stage stay inside a k-anonymous aggregate.

/intelligence/similar, the similar_companies fields on summary, strategies,
and ai-insights, and pattern_aggregator stats used to return other companies'
mrr_range and stage one peer at a time. A peer contributes only after an
explicit data_sharing_enabled opt-in. Aggregates require at least
MIN_DISTINCT_PEERS distinct companies. Below that the list is empty and the
reason is insufficient_peers. Individual names, ids, revenue, and bands are
never returned. A company still receives its own exact figures.

Run: python -m pytest server/tests/test_similar_companies_privacy.py -q
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.api import intelligence_graph as intelligence_api
from server.core.db import Base, get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.twin_event import TwinEvent
from server.services.pattern_aggregator import (
    aggregate_benchmark_updates,
    aggregate_decision_patterns,
    get_relevant_patterns,
)
from server.services.peer_privacy import MIN_DISTINCT_PEERS, INSUFFICIENT_PEERS, opted_in

A_REVENUE = 45123.0
B_REVENUE = 987654.0
MAJOR_REVENUE = 150001.0
MINOR_REVENUE = 4321.0
UNSHARED_REVENUE = 777777.0
LEAK_MEDIAN = 666666.0

MAJOR_STAGE = "series_c_cohort"
MINOR_STAGE = "preseed_private"
UNSHARED_STAGE = "stealth_unshared"
MAJOR_BAND = "$100K-500K"
MINOR_BAND = "$0-5K"
UNSHARED_BAND = "$500K+"


def _user(user_id: int):
    return SimpleNamespace(
        id=user_id,
        email=f"owner-{user_id}@example.com",
        is_platform_admin=False,
        is_email_verified=False,
        role="owner",
    )


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
            Scenario.__table__,
            SimulationRun.__table__,
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


def _add_company(
    db,
    user_id: int,
    name: str,
    *,
    industry: str = "saas",
    stage: str = "seed",
    sharing: bool = False,
) -> Company:
    company = Company(
        user_id=user_id,
        name=name,
        industry=industry,
        stage=stage,
        currency="USD",
        data_sharing_enabled=sharing,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _add_revenue(db, company_id: int, revenue: float, day: int = 1) -> None:
    db.add(
        FinancialRecord(
            company_id=company_id,
            period_start=date(2026, 8, day),
            period_end=date(2026, 8, 28),
            revenue=revenue,
            mrr=revenue,
            source_type="manual",
        )
    )
    db.commit()


def _add_decision(db, company_id: int, title: str = "Hire an AE") -> None:
    db.add(
        CompanyDecision(
            id=uuid.uuid4(),
            company_id=company_id,
            title=title,
            status="accepted",
            confidence="high",
        )
    )
    db.commit()


def _payloads(client: TestClient, company_id: int) -> dict:
    base = f"/companies/{company_id}/intelligence"
    routes = {
        "similar": client.get(f"{base}/similar"),
        "summary": client.get(f"{base}/summary"),
        "strategies": client.get(f"{base}/strategies"),
        "ai-insights": client.get(f"{base}/ai-insights"),
        "network": client.get(f"{base}/network"),
    }
    payloads = {}
    for label, resp in routes.items():
        assert resp.status_code == 200, f"{label}: {resp.text}"
        payloads[label] = resp.json()
    return payloads


def _similar_lists(payloads: dict) -> list:
    found = []
    for label, payload in payloads.items():
        if "similar_companies" in payload:
            found.append((label, payload["similar_companies"]))
        nested = payload.get("strategy_insights") or {}
        if "similar_companies" in nested:
            found.append((f"{label}.strategy_insights", nested["similar_companies"]))
    return found


def _assert_lists_empty(payloads: dict) -> None:
    lists = _similar_lists(payloads)
    assert lists, "expected similar_companies on the intelligence responses"
    for label, rows in lists:
        assert rows == [], f"{label} returned individual peers: {rows}"


def _walk_numbers(node, hits: list, forbidden: list) -> None:
    if isinstance(node, bool) or node is None:
        return
    if isinstance(node, (int, float)):
        for value in forbidden:
            if math.isclose(float(node), value, rel_tol=0, abs_tol=0.001):
                hits.append(node)
        return
    if isinstance(node, str):
        compact = node.replace(",", "").replace("$", "").replace(" ", "")
        for value in forbidden:
            token = str(int(value)) if float(value).is_integer() else str(value)
            if token in compact:
                hits.append(node)
        return
    if isinstance(node, dict):
        for value in node.values():
            _walk_numbers(value, hits, forbidden)
        return
    if isinstance(node, list):
        for value in node:
            _walk_numbers(value, hits, forbidden)


def _assert_numbers_absent(payload, forbidden: list, label: str) -> None:
    hits: list = []
    _walk_numbers(payload, hits, forbidden)
    assert hits == [], f"{label} contained foreign exact numbers {hits}"


def _assert_numbers_present(payload, required: float) -> None:
    hits: list = []
    _walk_numbers(payload, hits, [required])
    assert hits, f"own revenue {required} missing from {json.dumps(payload)[:500]}"


def _assert_no_peer_identity(payload, peer_ids: set, peer_names: list) -> None:
    serialized = json.dumps(payload)
    for name in peer_names:
        assert name not in serialized

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("company_id", "id", "peer_id") and value in peer_ids:
                    raise AssertionError(f"peer id {value} exposed at {key}")
                if key == "name" and value in peer_names:
                    raise AssertionError(f"peer name {value} exposed")
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)


def _assert_bands_are_aggregates(aggregates: dict) -> None:
    assert aggregates["peer_count"] >= MIN_DISTINCT_PEERS
    for key in ("mrr_bands", "stages", "industries", "growth_tiers", "employee_ranges"):
        for band in aggregates[key]:
            assert set(band) == {"band", "companies"}
            assert band["companies"] >= MIN_DISTINCT_PEERS


def _own_mrr_range_ok(payload) -> None:
    """mrr_range may describe the caller. It must not describe a peer row."""
    own_parents = {"your_profile", "company_profile", "profile_summary", "profile"}

    def walk(node, parent_key=None) -> None:
        if isinstance(node, dict):
            if "mrr_range" in node and parent_key not in own_parents:
                raise AssertionError(f"peer mrr_range under {parent_key}: {node}")
            if "similarity_score" in node or "peer_rank" in node or "shared_traits" in node:
                raise AssertionError(f"individual peer row: {node}")
            for key, value in node.items():
                walk(value, key)
        elif isinstance(node, list):
            for item in node:
                walk(item, parent_key)

    walk(payload)


def test_missing_sharing_flag_is_not_opt_in():
    assert opted_in(SimpleNamespace()) is False
    assert opted_in(SimpleNamespace(data_sharing_enabled=None)) is False
    assert opted_in(SimpleNamespace(data_sharing_enabled=False)) is False
    assert opted_in(SimpleNamespace(data_sharing_enabled=True)) is True


def test_fewer_than_five_opted_in_peers_yields_no_bands(db):
    owner = _user(1)
    company_a = _add_company(db, owner.id, "Company A", stage="seed", sharing=False)
    _add_revenue(db, company_a.id, A_REVENUE)

    peer_ids = set()
    peer_names = []
    for i in range(MIN_DISTINCT_PEERS - 1):
        name = f"ZZ-PEER-SMALL-{i}"
        peer = _add_company(
            db, 100 + i, name, stage=MAJOR_STAGE, sharing=True,
        )
        _add_revenue(db, peer.id, MAJOR_REVENUE)
        peer_ids.add(peer.id)
        peer_names.append(name)
    for i in range(6):
        name = f"ZZ-PEER-UNSHARED-{i}"
        hidden = _add_company(
            db, 200 + i, name, stage=MAJOR_STAGE, sharing=False,
        )
        _add_revenue(db, hidden.id, MAJOR_REVENUE)
        peer_ids.add(hidden.id)
        peer_names.append(name)

    db.execute(text("""
        CREATE TABLE cross_company_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type VARCHAR(100) NOT NULL,
            industry VARCHAR(100),
            stage VARCHAR(100),
            decision_type VARCHAR(100),
            sample_size INTEGER DEFAULT 0,
            success_rate FLOAT DEFAULT 0,
            median_impact FLOAT DEFAULT 0,
            p25_impact FLOAT DEFAULT 0,
            p75_impact FLOAT DEFAULT 0,
            contributing_companies INTEGER DEFAULT 0,
            computed_at TIMESTAMP
        )
    """))
    db.execute(
        text("""
            INSERT INTO cross_company_patterns
                (pattern_type, industry, stage, decision_type, sample_size,
                 success_rate, median_impact, p25_impact, p75_impact, contributing_companies)
            VALUES
                ('benchmark', 'all', 'all', 'revenue_leak_marker', 2, 0,
                 :median, :median, :median, 2),
                ('benchmark', 'all', 'all', 'single_point_leak', 1, 0,
                 :median, :median, :median, 8),
                ('decision_outcome', 'all', 'all', 'hire_leak_marker', 2, 100,
                 0, 0, 0, 2),
                ('benchmark', 'all', 'all', 'burn', 6, 0, 40, 20, 60, 6)
        """),
        {"median": LEAK_MEDIAN},
    )
    db.commit()

    payloads = _payloads(_client(db, owner), company_a.id)
    _assert_lists_empty(payloads)
    assert payloads["similar"]["reason"] == INSUFFICIENT_PEERS
    assert payloads["similar"]["aggregates"] is None
    assert payloads["similar"]["peer_count"] == 0
    assert payloads["summary"]["similar_companies_reason"] == INSUFFICIENT_PEERS
    assert payloads["summary"]["similar_company_aggregates"] is None
    assert payloads["strategies"]["similar_companies_reason"] == INSUFFICIENT_PEERS
    assert payloads["ai-insights"]["similar_companies_reason"] == INSUFFICIENT_PEERS

    blob = json.dumps(payloads)
    assert MAJOR_STAGE not in blob
    assert MAJOR_BAND not in blob
    assert MINOR_BAND not in blob
    assert "revenue_leak_marker" not in blob
    assert "single_point_leak" not in blob
    assert "hire_leak_marker" not in blob
    for payload in payloads.values():
        _assert_numbers_absent(payload, [MAJOR_REVENUE, LEAK_MEDIAN, UNSHARED_REVENUE], "small cohort")
        _assert_no_peer_identity(payload, peer_ids, peer_names)
        _own_mrr_range_ok(payload)
    _assert_numbers_present(payloads["similar"]["your_profile"], A_REVENUE)
    _assert_numbers_present(payloads["summary"]["company_profile"], A_REVENUE)
    assert payloads["similar"]["your_profile"]["company_id"] == company_a.id
    assert payloads["similar"]["your_profile"]["name"] == "Company A"

    visible = get_relevant_patterns(db, industry="saas", stage="seed")
    markers = {row["decision_type"] for row in visible}
    assert "revenue_leak_marker" not in markers
    assert "single_point_leak" not in markers
    assert "hire_leak_marker" not in markers
    assert "burn" in markers
    assert all(
        (row["contributing_companies"] or 0) >= MIN_DISTINCT_PEERS
        for row in visible
        if row["pattern_type"] in ("benchmark", "decision_outcome")
    )


def test_five_or_more_peers_yield_only_aggregates(db):
    owner = _user(1)
    company_a = _add_company(db, owner.id, "Company A", stage="seed", sharing=False)
    _add_revenue(db, company_a.id, A_REVENUE)

    peer_ids = set()
    peer_names = []
    for i in range(MIN_DISTINCT_PEERS):
        name = f"ZZ-PEER-MAJOR-{i}"
        peer = _add_company(db, 100 + i, name, stage=MAJOR_STAGE, sharing=True)
        _add_revenue(db, peer.id, MAJOR_REVENUE)
        peer_ids.add(peer.id)
        peer_names.append(name)
    for i in range(2):
        name = f"ZZ-PEER-MINOR-{i}"
        peer = _add_company(db, 300 + i, name, stage=MINOR_STAGE, sharing=True)
        _add_revenue(db, peer.id, MINOR_REVENUE)
        peer_ids.add(peer.id)
        peer_names.append(name)
    for i in range(3):
        name = f"ZZ-PEER-UNSHARED-{i}"
        hidden = _add_company(db, 400 + i, name, stage=UNSHARED_STAGE, sharing=False)
        _add_revenue(db, hidden.id, UNSHARED_REVENUE)
        peer_ids.add(hidden.id)
        peer_names.append(name)

    payloads = _payloads(_client(db, owner), company_a.id)
    _assert_lists_empty(payloads)

    aggregates = payloads["similar"]["aggregates"]
    assert payloads["similar"]["reason"] is None
    _assert_bands_are_aggregates(aggregates)
    assert aggregates["peer_count"] == MIN_DISTINCT_PEERS + 2

    mrr_labels = {band["band"]: band["companies"] for band in aggregates["mrr_bands"]}
    stage_labels = {band["band"]: band["companies"] for band in aggregates["stages"]}
    assert mrr_labels[MAJOR_BAND] == MIN_DISTINCT_PEERS
    assert MINOR_BAND not in mrr_labels
    assert UNSHARED_BAND not in mrr_labels
    assert stage_labels[MAJOR_STAGE] == MIN_DISTINCT_PEERS
    assert MINOR_STAGE not in stage_labels
    assert UNSHARED_STAGE not in stage_labels

    assert payloads["summary"]["similar_company_aggregates"]["peer_count"] == aggregates["peer_count"]
    assert payloads["strategies"]["similar_company_aggregates"]["peer_count"] == aggregates["peer_count"]
    assert payloads["ai-insights"]["similar_company_aggregates"]["peer_count"] == aggregates["peer_count"]
    assert payloads["summary"]["graph_stats"]["similar_companies_found"] == aggregates["peer_count"]

    network_labels = [node.get("label") for node in payloads["network"]["nodes"]]
    assert not any(name in (network_labels or []) for name in peer_names)
    assert all("mrr_range" not in (node.get("properties") or {}) for node in payloads["network"]["nodes"])

    blob = json.dumps(payloads)
    assert MINOR_STAGE not in blob
    assert UNSHARED_STAGE not in blob
    assert MINOR_BAND not in blob
    for payload in payloads.values():
        _assert_numbers_absent(
            payload, [MAJOR_REVENUE, MINOR_REVENUE, UNSHARED_REVENUE, B_REVENUE], "aggregates",
        )
        _assert_no_peer_identity(payload, peer_ids, peer_names)
        _own_mrr_range_ok(payload)
    _assert_numbers_present(payloads["similar"]["your_profile"], A_REVENUE)


def test_company_sees_only_its_own_exact_numbers(db):
    user_a = _user(1)
    user_b = _user(2)
    company_a = _add_company(db, user_a.id, "Company A", stage="seed", sharing=False)
    company_b = _add_company(db, user_b.id, "Company B", stage=MAJOR_STAGE, sharing=True)
    _add_revenue(db, company_a.id, A_REVENUE)
    _add_revenue(db, company_b.id, B_REVENUE)

    peer_ids = {company_b.id}
    peer_names = ["Company B"]
    for i in range(MIN_DISTINCT_PEERS):
        name = f"ZZ-PEER-MAJOR-{i}"
        peer = _add_company(db, 100 + i, name, stage=MAJOR_STAGE, sharing=True)
        _add_revenue(db, peer.id, MAJOR_REVENUE)
        peer_ids.add(peer.id)
        peer_names.append(name)

    viewed_by_a = _payloads(_client(db, user_a), company_a.id)
    viewed_by_b = _payloads(_client(db, user_b), company_b.id)

    for payload in viewed_by_a.values():
        _assert_numbers_absent(payload, [B_REVENUE, MAJOR_REVENUE], "company A view")
        _assert_no_peer_identity(payload, peer_ids, peer_names)
        _own_mrr_range_ok(payload)
    _assert_numbers_present(viewed_by_a["similar"]["your_profile"], A_REVENUE)
    _assert_numbers_present(viewed_by_a["summary"]["company_profile"], A_REVENUE)
    _assert_numbers_present(viewed_by_a["ai-insights"]["profile"], A_REVENUE)
    assert viewed_by_a["similar"]["your_profile"]["name"] == "Company A"
    assert "Company B" not in json.dumps(viewed_by_a)

    b_forbidden_ids = {company_a.id} | (peer_ids - {company_b.id})
    b_forbidden_names = ["Company A", *[name for name in peer_names if name != "Company B"]]
    for payload in viewed_by_b.values():
        _assert_numbers_absent(payload, [A_REVENUE, MAJOR_REVENUE], "company B view")
        _assert_no_peer_identity(payload, b_forbidden_ids, b_forbidden_names)
        _own_mrr_range_ok(payload)
    _assert_numbers_present(viewed_by_b["similar"]["your_profile"], B_REVENUE)
    _assert_numbers_present(viewed_by_b["summary"]["company_profile"], B_REVENUE)
    assert viewed_by_b["similar"]["your_profile"]["name"] == "Company B"
    assert viewed_by_b["similar"]["your_profile"]["company_id"] == company_b.id
    assert "Company A" not in json.dumps(viewed_by_b)

    _assert_lists_empty(viewed_by_a)
    _assert_lists_empty(viewed_by_b)
    _assert_bands_are_aggregates(viewed_by_a["similar"]["aggregates"])
    _assert_bands_are_aggregates(viewed_by_b["similar"]["aggregates"])
    assert UNSHARED_BAND not in json.dumps(viewed_by_a["similar"]["aggregates"])


def test_pattern_aggregator_suppresses_stats_below_five_companies(db):
    small_revenues = []
    for i in range(MIN_DISTINCT_PEERS - 1):
        company = _add_company(
            db, 100 + i, f"ZZ-AGG-SMALL-{i}", stage=MAJOR_STAGE, sharing=True,
        )
        revenue = 810000.0 + i
        small_revenues.append(revenue)
        _add_revenue(db, company.id, revenue, day=min(i + 1, 28))
        _add_decision(db, company.id)
    for i in range(3):
        company = _add_company(
            db, 200 + i, f"ZZ-AGG-HIDDEN-{i}", stage=MAJOR_STAGE, sharing=False,
        )
        _add_revenue(db, company.id, 820000.0 + i, day=min(i + 1, 28))
        _add_decision(db, company.id)

    patterns = aggregate_decision_patterns(db)
    benchmarks = aggregate_benchmark_updates(db)
    assert patterns["patterns"] == []
    assert patterns["reason"] == INSUFFICIENT_PEERS
    assert benchmarks["benchmarks"] == {}
    assert benchmarks["reason"] == INSUFFICIENT_PEERS
    blob = json.dumps({"patterns": patterns, "benchmarks": benchmarks})
    assert MAJOR_STAGE not in blob
    for revenue in small_revenues:
        assert str(int(revenue)) not in blob
    assert "ZZ-AGG-SMALL" not in blob
    assert "company_id" not in blob

    fifth = _add_company(db, 500, "ZZ-AGG-FIFTH", stage=MAJOR_STAGE, sharing=True)
    _add_revenue(db, fifth.id, 810004.0)
    _add_decision(db, fifth.id)

    patterns = aggregate_decision_patterns(db)
    benchmarks = aggregate_benchmark_updates(db)
    assert patterns["reason"] is None
    assert benchmarks["reason"] is None
    assert patterns["patterns"]
    for pattern in patterns["patterns"]:
        assert pattern["contributing_companies"] >= MIN_DISTINCT_PEERS
        assert "company_id" not in pattern
        assert "name" not in pattern
        assert "mrr" not in pattern
        assert "mrr_range" not in pattern
    assert MAJOR_STAGE in {pattern["stage"] for pattern in patterns["patterns"]}
    stage_stats = benchmarks["benchmarks"][MAJOR_STAGE]
    assert stage_stats["sample_size"] >= MIN_DISTINCT_PEERS
    assert stage_stats["revenue"]["companies"] >= MIN_DISTINCT_PEERS
    assert stage_stats["revenue"]["sample_size"] >= MIN_DISTINCT_PEERS
    serialized = json.dumps({"patterns": patterns, "benchmarks": benchmarks})
    assert "ZZ-AGG-" not in serialized
    assert "company_id" not in serialized
