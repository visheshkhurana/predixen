"""Audit 10-19 leftovers: agent-sim investor interest relabel, LLM model
prices, company purge of raw-SQL tables, legacy agent-sim share revocation."""

import pytest


# --- 2. agent sim: fundingProbability is not a probability -----------------

def _snaps(n=4):
    return [
        {"month": m, "cash_balance": 1, "monthly_revenue": 1, "monthly_burn": 1,
         "runway_months": 1, "survival": True}
        for m in range(1, n + 1)
    ]


def _ev(kind):
    return {"eventType": kind, "severity": "info", "description": kind}


def test_agent_sim_funding_is_relabelled_investor_interest():
    from server.simulation_agents.simulation_orchestrator import _compile_results
    from server.simulation_agents.environment_engine import EnvironmentEngine

    events = [_ev("investment_interest"), _ev("investment_pass"),
              _ev("investment_pass"), _ev("investment_pass")]
    out = _compile_results({"cash_balance": 0, "runway_months": 0}, _snaps(), events, [],
                           EnvironmentEngine({}), {}, {})
    s = out["summary"]
    assert s["investorInterestPct"] == 25.0
    assert s["investorInterestEvents"] == 1
    assert s["investorEncounters"] == 4
    assert s["fundingProbability"] == 25.0  # deprecated alias


def test_agent_sim_no_investor_reads_reports_zero_encounters():
    from server.simulation_agents.simulation_orchestrator import _compile_results
    from server.simulation_agents.environment_engine import EnvironmentEngine

    out = _compile_results({"cash_balance": 0, "runway_months": 0}, _snaps(), [], [],
                           EnvironmentEngine({}), {}, {})
    assert out["summary"]["investorEncounters"] == 0
    assert out["summary"]["investorInterestPct"] == 0


def test_agent_sim_report_carries_investor_interest_and_alias():
    from server.simulation_agents.simulation_report import generate_report

    rep = generate_report({"summary": {"monthsSolventPct": 90, "investorInterestPct": 40,
                                       "investorEncounters": 5, "fundingProbability": 40}})
    assert rep["investorInterestPct"] == 40
    assert rep["investorEncounters"] == 5
    assert rep["fundingProbability"] == 40
    # stored pre-relabel runs only have the alias
    old = generate_report({"summary": {"survivalProbability": 50, "fundingProbability": 30}})
    assert old["investorInterestPct"] == 30


def test_agent_sim_ui_no_longer_says_funding_probability():
    src = open("client/src/pages/simulate-v2.tsx").read()
    assert "Investor interest" in src
    assert ">probability<" not in src.replace(" ", "")
    assert "summary.fundingProbability.toFixed" not in src


# --- 4. every routed model carries a price ----------------------------------

def test_every_model_has_input_and_output_price():
    from server.lib.llm.llm_router import MODELS

    for key, cfg in MODELS.items():
        assert cfg.cost_per_1k_input > 0, key
        assert cfg.cost_per_1k_output > 0, key
        assert cfg.cost_per_1k_output >= cfg.cost_per_1k_input, key


def test_default_model_cost_is_nonzero_so_budgets_can_trip():
    from server.lib.llm.llm_router import _estimate_cost_usd

    usage = {"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}}
    assert _estimate_cost_usd("gemini-2.5-flash", usage) == pytest.approx(0.30 + 2.50)
    assert _estimate_cost_usd("gpt-5", usage) == pytest.approx(1.25 + 10.0)
    assert _estimate_cost_usd("claude-sonnet-4-5", usage) == pytest.approx(3.0 + 15.0)


# --- 6. company purge covers raw-SQL / unlinked company tables --------------

def test_unlinked_plan_covers_raw_tables_children_first():
    from server.core.company_purge import plan_unlinked_purge, UNLINKED_COMPANY_TABLES

    existing = {t for t, _, _ in UNLINKED_COMPANY_TABLES}
    plan = plan_unlinked_purge(existing, [])
    names = [(t, a) for t, _, a in plan]
    for t in ("graph_nodes", "events", "company_flags", "ai_agent_budgets", "autopilot_runs",
              "data_confidence_scores", "company_states", "agent_simulation_runs",
              "shared_scenarios", "metric_snapshots"):
        assert (t, "delete") in names, t
    assert ("ai_agent_logs", "nullify") in names
    order = [t for t, _ in names]
    assert order.index("graph_edges") < order.index("graph_nodes")
    # tables that do not exist in this database are skipped
    assert plan_unlinked_purge({"events"}, []) == [("events", "company_id", "delete")]


def test_unlinked_plan_picks_up_live_db_fks_unknown_to_the_orm():
    from server.core.company_purge import plan_unlinked_purge

    plan = plan_unlinked_purge(set(), [("mystery_table", "company_id", False),
                                       ("mystery_log", "company_id", True),
                                       ("fundraising_rounds", "company_id", False)])
    assert ("mystery_table", "company_id", "delete") in plan
    assert ("mystery_log", "company_id", "nullify") in plan
    # already declared in ORM metadata -> handled by the FK walk, not twice
    assert not any(t == "fundraising_rounds" for t, _, _ in plan)


def _pg_ok():
    import os
    from sqlalchemy import create_engine, text
    try:
        e = create_engine(os.environ.get("TEST_PG_ADMIN_URL", "postgresql://localhost/postgres"),
                          connect_args={"connect_timeout": 2})
        with e.connect() as c:
            c.execute(text("SELECT 1"))
        e.dispose()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _pg_ok(), reason="no local PostgreSQL")
def test_purge_with_raw_sql_tables_on_postgres():
    import os
    import uuid
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from server.core.company_purge import _load_all_models, purge_company
    from server.core.db import Base

    admin_url = os.environ.get("TEST_PG_ADMIN_URL", "postgresql://localhost/postgres")
    dbname = "fc_purge_raw_" + uuid.uuid4().hex[:8]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {dbname}"))
    _load_all_models()
    engine = create_engine(admin_url.rsplit("/", 1)[0] + "/" + dbname)
    try:
        # Everything except company_states from the ORM; company_states and the
        # raw tables exactly as server/core/migrations.py creates them.
        Base.metadata.create_all(engine, tables=[t for n, t in Base.metadata.tables.items()
                                                 if n != "company_states"])
        with engine.begin() as c:
            c.execute(text("CREATE TABLE company_states (id SERIAL PRIMARY KEY, "
                           "company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id))"))
            c.execute(text("CREATE TABLE graph_nodes (id SERIAL PRIMARY KEY, company_id INTEGER NOT NULL)"))
            c.execute(text("CREATE TABLE graph_edges (id SERIAL PRIMARY KEY, company_id INTEGER NOT NULL, "
                           "source_node_id INTEGER NOT NULL REFERENCES graph_nodes(id), "
                           "target_node_id INTEGER NOT NULL REFERENCES graph_nodes(id))"))
            c.execute(text("CREATE TABLE ai_agent_logs (id SERIAL PRIMARY KEY, company_id INTEGER)"))
            c.execute(text("CREATE TABLE raw_extra (id SERIAL PRIMARY KEY, "
                           "company_id INTEGER NOT NULL REFERENCES companies(id))"))
        db = sessionmaker(bind=engine)()
        from server.models.company import Company
        from server.models.user import User
        user = User(email=f"p-{uuid.uuid4().hex[:8]}@example.com", password_hash="x")
        db.add(user); db.flush()
        keep, doomed = Company(name="Keep", user_id=user.id), Company(name="Doomed", user_id=user.id)
        db.add_all([keep, doomed]); db.flush()
        for co in (keep, doomed):
            db.execute(text("INSERT INTO company_states (company_id) VALUES (:c)"), {"c": co.id})
            db.execute(text("INSERT INTO raw_extra (company_id) VALUES (:c)"), {"c": co.id})
            n1 = db.execute(text("INSERT INTO graph_nodes (company_id) VALUES (:c) RETURNING id"), {"c": co.id}).scalar()
            n2 = db.execute(text("INSERT INTO graph_nodes (company_id) VALUES (:c) RETURNING id"), {"c": co.id}).scalar()
            db.execute(text("INSERT INTO graph_edges (company_id, source_node_id, target_node_id) "
                            "VALUES (:c, :a, :b)"), {"c": co.id, "a": n1, "b": n2})
            db.execute(text("INSERT INTO ai_agent_logs (company_id) VALUES (:c)"), {"c": co.id})
        db.commit()
        doomed_id, keep_id = doomed.id, keep.id

        purge_company(db, doomed_id)
        db.commit()

        def count(table, cid):
            return db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE company_id = :c"), {"c": cid}).scalar()
        for t in ("company_states", "raw_extra", "graph_nodes", "graph_edges", "ai_agent_logs"):
            assert count(t, doomed_id) == 0, t
            assert count(t, keep_id) >= 1, t
        assert db.execute(text("SELECT COUNT(*) FROM ai_agent_logs WHERE company_id IS NULL")).scalar() == 1
        assert db.execute(text("SELECT COUNT(*) FROM companies WHERE id = :c"), {"c": doomed_id}).scalar() == 0
        db.close()
    finally:
        engine.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {dbname} WITH (FORCE)"))
        admin.dispose()


# --- 7. legacy agent-sim share links -----------------------------------------

def _share_engine():
    import json
    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE agent_simulation_runs (id INTEGER PRIMARY KEY, "
                       "results_json TEXT NOT NULL, share_token VARCHAR(64) UNIQUE)"))
        rows = [
            (1, json.dumps({"summary": {}}), "legacy-auto"),            # pre-#161 auto token
            (2, json.dumps({"shareExpiresAt": None}), "owner-forever"),  # owner-created
            (3, json.dumps({"shareExpiresAt": "2027-01-01T00:00:00"}), "owner-expiring"),
            (4, json.dumps({"summary": {}}), None),                     # never shared
            (5, "not json", "legacy-broken"),
        ]
        for r in rows:
            c.execute(text("INSERT INTO agent_simulation_runs VALUES (:i, :r, :t)"),
                      {"i": r[0], "r": r[1], "t": r[2]})
    return engine


def _tokens(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        return dict(c.execute(text("SELECT id, share_token FROM agent_simulation_runs")).fetchall())


def test_legacy_share_revocation_is_flag_gated(monkeypatch):
    from server.core.migrations import revoke_legacy_agent_sim_shares

    engine = _share_engine()
    monkeypatch.delenv("REVOKE_LEGACY_AGENT_SIM_SHARES", raising=False)
    assert revoke_legacy_agent_sim_shares(engine) == 0
    monkeypatch.setenv("REVOKE_LEGACY_AGENT_SIM_SHARES", "false")
    assert revoke_legacy_agent_sim_shares(engine) == 0
    assert _tokens(engine)[1] == "legacy-auto"


def test_legacy_share_revocation_keeps_owner_links_and_is_idempotent(monkeypatch):
    from server.core.migrations import revoke_legacy_agent_sim_shares

    engine = _share_engine()
    monkeypatch.setenv("REVOKE_LEGACY_AGENT_SIM_SHARES", "true")
    assert revoke_legacy_agent_sim_shares(engine) == 2
    t = _tokens(engine)
    assert t[1] is None and t[5] is None
    assert t[2] == "owner-forever" and t[3] == "owner-expiring"
    assert t[4] is None
    assert revoke_legacy_agent_sim_shares(engine) == 0
    assert _tokens(engine) == t


def test_share_endpoint_always_writes_the_marker_key():
    # The revocation tells owner links apart by this key; the share endpoint
    # must keep writing it even for non-expiring links.
    src = open("server/api/agent_simulation.py").read()
    assert 'results["shareExpiresAt"] = expires_at.isoformat() if expires_at else None' in src
    assert "share_token=None" in src  # runs are not auto-shared any more


def test_boot_calls_revocation():
    src = open("server/main.py").read()
    assert "revoke_legacy_agent_sim_shares(engine)" in src
