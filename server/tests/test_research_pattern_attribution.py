"""Research rows are published studies, not FounderConsole peer outcomes.

pattern_type='research' (for example saas / pre_seed / cost_reduction from
a16z, 65%, n=80) used to render as "65% of similar companies saw positive
outcomes ... (based on 80 decisions)". Peer wording stays on decision_outcome
rows that already clear the distinct-company gate. That gate is unchanged.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.copilot.context_pack import build_platform_intelligence
from server.decision.cross_company_claims import (
    format_research_insight,
    research_citation,
)
from server.decision.decision_engine import (
    _get_cross_company_success_rates,
    generate_recommendations,
)
from server.decision.pattern_engine import DecisionPatternEngine
from server.seed.seed_research_patterns import RESEARCH_PATTERNS
from server.services.pattern_aggregator import _research_source, get_relevant_patterns
from server.services.peer_privacy import MIN_DISTINCT_PEERS
from server.simulate.simulation_engine import SimulationInputs

A16Z_SOURCE = "a16z Startup Metrics Guide"
A16Z_INSIGHT = "Industry research (a16z, n=80): 65% positive outcomes"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    session.execute(text("""
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
            computed_at TIMESTAMP,
            metadata_json TEXT
        )
    """))
    session.commit()
    yield session
    session.close()


def _insert(
    db,
    *,
    pattern_type: str,
    decision_type: str,
    sample_size: int,
    success_rate: float,
    contributing: int,
    source: str = None,
    industry: str = "saas",
    stage: str = "pre_seed",
) -> None:
    metadata = json.dumps({"source": source, "notes": "citation"}) if source else None
    db.execute(
        text("""
            INSERT INTO cross_company_patterns
                (pattern_type, industry, stage, decision_type, sample_size,
                 success_rate, median_impact, p25_impact, p75_impact,
                 contributing_companies, metadata_json)
            VALUES
                (:pattern_type, :industry, :stage, :decision_type, :sample_size,
                 :success_rate, 0, 0, 0, :contributing, :metadata)
        """),
        {
            "pattern_type": pattern_type,
            "industry": industry,
            "stage": stage,
            "decision_type": decision_type,
            "sample_size": sample_size,
            "success_rate": success_rate,
            "contributing": contributing,
            "metadata": metadata,
        },
    )
    db.commit()


def _peer_pattern(decision_type: str = "cost_reduction") -> dict:
    return {
        "decision_type": decision_type,
        "sample_size": 30,
        "company_count": MIN_DISTINCT_PEERS,
        "success_rate": 80.0,
        "recommendation": "Focus on vendor renegotiation.",
    }


def _recommendations(db, decision_type: str = "cost_reduction") -> list:
    engine = DecisionPatternEngine(db)
    engine.find_patterns = lambda *args, **kwargs: [_peer_pattern(decision_type)]
    return engine.get_recommendations({"industry": "saas", "stage": "pre_seed"})


def _bind_session(monkeypatch, db) -> None:
    monkeypatch.setattr(
        "server.core.db.SessionLocal",
        lambda: SimpleNamespace(execute=db.execute, close=lambda: None),
    )


def _quiet_monte_carlo(*args, **kwargs):
    return {
        "survival": {"18m": 40},
        "runway": {"p50": 14},
        "summary": {
            "revenue_18m_median": 100,
            "avg_burn_p50": 1000,
            "final_cash_p50": 50000,
        },
    }


def _decision_recs(monkeypatch, db) -> list:
    _bind_session(monkeypatch, db)
    monkeypatch.setattr(
        "server.decision.decision_engine.run_monte_carlo",
        _quiet_monte_carlo,
    )
    monkeypatch.setattr(
        "server.decision.decision_engine.select_candidates",
        lambda *args, **kwargs: [{
            "id": "cut_cloud",
            "title": "Cut cloud spend",
            "description": "Reduce infra.",
            "bucket": "efficiency",
            "scenario_deltas": {},
        }],
    )
    inputs = SimulationInputs(
        baseline_revenue=10000,
        baseline_growth_rate=5,
        gross_margin=70,
        opex=1000,
        payroll=5000,
        other_costs=500,
        cash_balance=100000,
    )
    return generate_recommendations(
        {"industry": "saas", "stage": "pre_seed", "runway_p50": 10},
        80,
        inputs,
    )


@pytest.mark.parametrize(
    "source,citation",
    [
        ("a16z Startup Metrics Guide", "a16z"),
        ("a16z Marketplace 100", "a16z"),
        ("First Round State of Startups 2024", "First Round"),
        ("First Round Capital Blog", "First Round"),
        ("CB Insights Venture Report 2024", "CB Insights"),
        ("YC Startup School Data", "YC"),
        ("YC Post-Mortems Analysis", "YC"),
        ("Startup Genome Report 2024", "Startup Genome"),
        ("Lenny's Newsletter Marketplace Data", "Lenny's Newsletter"),
        ("Rock Health Digital Health Report", "Rock Health"),
        ("Subscription Economy Index", "Subscription Economy Index"),
        ("HAX Accelerator Report", "HAX"),
        ("", "published research"),
    ],
)
def test_research_citation_uses_the_publisher(source, citation):
    assert research_citation(source) == citation


def test_a16z_seed_row_is_labeled_as_industry_research():
    row = next(
        p for p in RESEARCH_PATTERNS
        if p["industry"] == "saas"
        and p["stage"] == "pre_seed"
        and p["decision_type"] == "cost_reduction"
    )
    assert row["success_rate"] == 65.0
    assert row["sample_size"] == 80
    assert row["source"] == A16Z_SOURCE
    text = format_research_insight(row["source"], row["success_rate"], row["sample_size"])
    assert text == A16Z_INSIGHT
    assert "similar companies" not in text


def test_every_seeded_research_source_stays_out_of_the_peer_sentence():
    for row in RESEARCH_PATTERNS:
        text = format_research_insight(row["source"], row["success_rate"], row["sample_size"])
        assert text.startswith("Industry research (")
        assert f"n={row['sample_size']}" in text
        assert "similar companies" not in text.lower()
        assert research_citation(row["source"]) != "published research"


def test_research_source_parses_json_text_and_dicts():
    payload = {"source": A16Z_SOURCE, "notes": "Cloud cost optimization biggest lever"}
    assert _research_source(json.dumps(payload)) == A16Z_SOURCE
    assert _research_source(payload) == A16Z_SOURCE
    assert _research_source(None) is None
    assert _research_source('{"notes": "no publisher"}') is None


def test_peer_gate_is_unchanged_and_research_rows_still_publish(db):
    """k stays 5. A 4-company decision_outcome stays hidden. Research with n=80 does not."""
    assert MIN_DISTINCT_PEERS == 5
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="pricing",
        sample_size=80,
        success_rate=99.0,
        contributing=MIN_DISTINCT_PEERS - 1,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="hiring",
        sample_size=MIN_DISTINCT_PEERS - 1,
        success_rate=99.0,
        contributing=MIN_DISTINCT_PEERS,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="fundraising",
        sample_size=12,
        success_rate=48.0,
        contributing=MIN_DISTINCT_PEERS,
    )

    rows = get_relevant_patterns(db, industry="saas", stage="pre_seed")
    by_key = {(row["pattern_type"], row["decision_type"]): row for row in rows}

    assert ("decision_outcome", "pricing") not in by_key
    assert ("decision_outcome", "hiring") not in by_key
    research = by_key[("research", "cost_reduction")]
    assert research["source"] == A16Z_SOURCE
    assert research["cross_company_source"] == "research"
    assert research["contributing_companies"] == 0
    assert research["sample_size"] == 80
    peer = by_key[("decision_outcome", "fundraising")]
    assert peer["cross_company_source"] == "peer_cohort"
    assert peer["source"] is None
    assert peer["contributing_companies"] >= MIN_DISTINCT_PEERS
    assert peer["sample_size"] >= MIN_DISTINCT_PEERS


def test_pattern_engine_labels_research_and_keeps_peer_based_on(db):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    rec = _recommendations(db)[0]
    assert rec["cross_company_source"] == "research"
    assert rec["cross_company_insight"] == A16Z_INSIGHT
    assert "similar companies" not in rec["cross_company_insight"]
    assert "based on 80 decisions" not in rec["cross_company_insight"]
    assert rec["based_on"] == f"{MIN_DISTINCT_PEERS} similar companies"
    assert rec["cross_company_success_rate"] == "65.0%"
    assert rec["cross_company_sample_size"] == 80


def test_pattern_engine_keeps_similar_companies_for_a_gated_peer_row(db):
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="cost_reduction",
        sample_size=40,
        success_rate=72.0,
        contributing=MIN_DISTINCT_PEERS,
    )
    rec = _recommendations(db)[0]
    assert rec["cross_company_source"] == "peer_cohort"
    assert rec["cross_company_insight"] == (
        "72% of similar companies saw positive outcomes "
        "from cost reduction decisions (based on 40 decisions)."
    )


def test_pattern_engine_prefers_gated_peers_over_research(db):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="cost_reduction",
        sample_size=40,
        success_rate=72.0,
        contributing=MIN_DISTINCT_PEERS,
    )
    rec = _recommendations(db)[0]
    assert rec["cross_company_source"] == "peer_cohort"
    assert rec["cross_company_insight"].startswith("72% of similar companies")
    assert "Industry research" not in rec["cross_company_insight"]
    assert "80" not in rec["cross_company_insight"]


def test_pattern_engine_does_not_let_an_under_gate_peer_row_replace_research(db):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="cost_reduction",
        sample_size=100,
        success_rate=99.0,
        contributing=MIN_DISTINCT_PEERS - 1,
    )
    rec = _recommendations(db)[0]
    assert rec["cross_company_source"] == "research"
    assert rec["cross_company_insight"] == A16Z_INSIGHT
    assert "99" not in rec["cross_company_insight"]
    assert "similar companies" not in rec["cross_company_insight"]


def test_pattern_engine_still_ignores_research_below_sample_two(db):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=1,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    rec = _recommendations(db)[0]
    assert "cross_company_source" not in rec
    assert "cross_company_insight" not in rec


def test_decision_engine_labels_research_on_the_response(db, monkeypatch):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    _bind_session(monkeypatch, db)
    rates = _get_cross_company_success_rates({"industry": "saas", "stage": "pre_seed"})
    assert rates["cost_reduction"]["cross_company_source"] == "research"
    assert rates["efficiency"]["cross_company_source"] == "research"
    assert rates["efficiency"]["source"] == A16Z_SOURCE

    rec = _decision_recs(monkeypatch, db)[0]
    assert rec["cross_company_source"] == "research"
    assert rec["cross_company_insight"]["cross_company_source"] == "research"
    assert rec["cross_company_insight"]["text"] == A16Z_INSIGHT
    assert rec["cross_company_insight"]["sample_size"] == 80
    assert rec["rationale"] == f"Reduce infra. {A16Z_INSIGHT}"
    blob = json.dumps(rec).lower()
    assert "similar companies" not in blob


def test_decision_engine_keeps_similar_companies_for_a_gated_peer_row(db, monkeypatch):
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="cost_reduction",
        sample_size=40,
        success_rate=72.0,
        contributing=MIN_DISTINCT_PEERS,
    )
    rec = _decision_recs(monkeypatch, db)[0]
    assert rec["cross_company_source"] == "peer_cohort"
    assert rec["cross_company_insight"]["text"] == (
        "72% of similar companies saw positive outcomes from this type of action "
        "(based on 40 decisions)."
    )
    assert rec["rationale"] == (
        "Reduce infra. 72% of similar companies that took this action saw positive outcomes."
    )


def test_decision_engine_prefers_gated_peers_over_research(db, monkeypatch):
    _insert(
        db,
        pattern_type="research",
        decision_type="cost_reduction",
        sample_size=80,
        success_rate=65.0,
        contributing=0,
        source=A16Z_SOURCE,
    )
    _insert(
        db,
        pattern_type="decision_outcome",
        decision_type="cost_reduction",
        sample_size=40,
        success_rate=72.0,
        contributing=MIN_DISTINCT_PEERS,
    )
    rec = _decision_recs(monkeypatch, db)[0]
    assert rec["cross_company_source"] == "peer_cohort"
    assert "similar companies" in rec["cross_company_insight"]["text"]
    assert "Industry research" not in rec["cross_company_insight"]["text"]
    assert "Industry research" not in rec["rationale"]
    assert "80" not in rec["cross_company_insight"]["text"]


class _CompanyQuery:
    def __init__(self, company):
        self.company = company

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.company


class _CompanyDb:
    def __init__(self, company):
        self.company = company

    def query(self, model):
        return _CompanyQuery(self.company)


def test_platform_intelligence_cites_research_instead_of_peers(monkeypatch):
    monkeypatch.setattr(
        "server.services.pattern_aggregator.get_relevant_patterns",
        lambda db, industry, stage: [{
            "pattern_type": "research",
            "decision_type": "cost_reduction",
            "success_rate": 65.0,
            "sample_size": 80,
            "contributing_companies": 0,
            "source": A16Z_SOURCE,
        }],
    )
    pack = build_platform_intelligence(
        1, _CompanyDb(SimpleNamespace(industry="SaaS", stage="Pre_Seed")),
    )
    insight = pack["insights"][0]
    assert insight["insight"] == A16Z_INSIGHT
    assert insight["cross_company_source"] == "research"
    assert "similar companies" not in insight["insight"]
    assert "published studies" in pack["disclaimer"]
    assert "opted-in companies" not in pack["disclaimer"]


def test_platform_intelligence_keeps_peer_wording_for_gated_outcomes(monkeypatch):
    monkeypatch.setattr(
        "server.services.pattern_aggregator.get_relevant_patterns",
        lambda db, industry, stage: [{
            "pattern_type": "decision_outcome",
            "decision_type": "cost_reduction",
            "success_rate": 72.0,
            "sample_size": 40,
            "contributing_companies": MIN_DISTINCT_PEERS,
            "source": None,
        }],
    )
    pack = build_platform_intelligence(
        1, _CompanyDb(SimpleNamespace(industry="saas", stage="pre_seed")),
    )
    insight = pack["insights"][0]
    assert insight["cross_company_source"] == "peer_cohort"
    assert insight["insight"] == (
        f"72% of similar companies (40 decisions across {MIN_DISTINCT_PEERS} companies) "
        "saw positive outcomes from cost reduction decisions."
    )
    assert pack["disclaimer"] == (
        "Based on anonymized, aggregated data from opted-in companies. "
        "Individual company data is never exposed."
    )
