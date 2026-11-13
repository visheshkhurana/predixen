"""
Digital Twin Service — orchestration layer that assembles the unified twin state
from existing models: CompanyState, FinancialRecord, TruthScan, Simulations,
Decisions, Alerts, and raw events.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from server.models import (
    Company,
    CompanyState,
    FinancialRecord,
    Scenario,
    SimulationRun,
    CompanyDecision,
)
from server.models.twin_event import TwinEvent

logger = logging.getLogger(__name__)

# Creation-time CompanyState seed (server/api/companies.py
# _get_stage_sample_financials). pre_seed is cash 150_000 / burn 12_000,
# which displays as Cash $150K, Burn $12K, Runway 12.5 mo. That seed is not
# an entered financial and must never be shown as one.
_SAMPLE_SOURCE = "sample"


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _stage_sample_fingerprints() -> set:
    """(cash, burn, revenue, expenses) tuples written at company creation."""
    from server.api.companies import _get_stage_sample_financials

    fingerprints = set()
    for stage in (
        None, "pre_seed", "seed", "series_a", "series_b",
        "pre_series_a", "growth", "pre_ipo", "public",
    ):
        sample = _get_stage_sample_financials(stage)
        fingerprints.add((
            int(sample.get("cashBalance") or 0),
            int(sample.get("monthlyBurn") or 0),
            int(sample.get("revenueMonthly") or 0),
            int(sample.get("expensesMonthly") or 0),
        ))
    return fingerprints


def _is_stage_sample_state(cs) -> bool:
    """True when CompanyState is still the untouched creation-time sample."""
    if cs is None:
        return False
    parts = []
    for attr in ("cash_balance", "monthly_burn", "revenue_monthly", "expenses_monthly"):
        number = _num(getattr(cs, attr, None))
        if number is None:
            return False
        parts.append(int(number))
    return tuple(parts) in _stage_sample_fingerprints()


def _truth_metric(ts_metrics: dict, *keys):
    """First non-estimated truth-scan number, or None."""
    if not isinstance(ts_metrics, dict):
        return None
    estimated = set(ts_metrics.get("_estimated_metrics") or [])
    for key in keys:
        if key in estimated:
            continue
        raw = ts_metrics.get(key)
        if raw is None:
            continue
        if isinstance(raw, dict):
            if raw.get("estimated") is True:
                continue
            raw = raw.get("value")
        number = _num(raw)
        if number is not None:
            return number
    return None


def _record_burn(record):
    """Signed net burn, same definition /overview's computed metrics use."""
    from server.core.burn import net_burn

    if record is None:
        return None
    return net_burn(record)


def _record_revenue(record):
    if record is None:
        return None
    if getattr(record, "mrr", None) is not None:
        return _num(record.mrr)
    return _num(getattr(record, "revenue", None))


def resolve_twin_financials(cs, real_record, sample_record, ts_metrics) -> dict:
    """Cash, burn, revenue and runway for the Digital Twin.

    Same precedence as GET /metrics/computed, which is what /overview shows:
    the entered FinancialRecord, then a non-estimated truth-scan value.
    CompanyState fills a gap only when it is not the creation-time stage
    sample. A labelled sample record is returned as an assumption. Anything
    still unknown stays None — never the pre-seed $150K / $12K seed.
    """
    from server.core.burn import gross_burn

    assumptions = []
    sample_state = _is_stage_sample_state(cs)
    use_sample_record = real_record is None and sample_record is not None

    def pick(real_value, truth_value, sample_value, state_value, field):
        if real_record is not None and real_value is not None:
            return real_value
        if truth_value is not None and real_record is None:
            return truth_value
        # A real record with this field blank is "not provided", not a cue
        # to fall back onto the stage sample or an older sample file.
        if real_record is not None:
            if truth_value is not None:
                return truth_value
            return None
        if use_sample_record and sample_value is not None:
            assumptions.append(field)
            return sample_value
        if not sample_state and state_value is not None:
            return state_value
        return None

    cash = pick(
        _num(getattr(real_record, "cash_balance", None)) if real_record is not None else None,
        _truth_metric(ts_metrics, "cash_balance", "cash_on_hand", "cash"),
        _num(getattr(sample_record, "cash_balance", None)) if sample_record is not None else None,
        _num(getattr(cs, "cash_balance", None)) if cs is not None else None,
        "cash_balance",
    )
    burn = pick(
        _record_burn(real_record),
        _truth_metric(ts_metrics, "monthly_burn", "net_burn", "burn_rate"),
        _record_burn(sample_record) if use_sample_record else None,
        _num(getattr(cs, "monthly_burn", None)) if cs is not None else None,
        "monthly_burn",
    )
    revenue = pick(
        _record_revenue(real_record),
        _truth_metric(ts_metrics, "monthly_revenue", "mrr", "revenue"),
        _record_revenue(sample_record) if use_sample_record else None,
        _num(getattr(cs, "revenue_monthly", None)) if cs is not None else None,
        "revenue_monthly",
    )

    growth = None
    if real_record is not None and getattr(real_record, "mom_growth", None) is not None:
        growth = _num(real_record.mom_growth)
    elif real_record is None:
        growth = _truth_metric(ts_metrics, "revenue_growth_mom", "revenue_growth_rate")
        if growth is None and not sample_state and cs is not None:
            growth = _num(getattr(cs, "revenue_growth_rate", None))

    expenses = None
    cost_record = real_record or (sample_record if use_sample_record else None)
    if cost_record is not None:
        gross = gross_burn(cost_record)
        expenses = gross if gross > 0 else None
    elif not sample_state and cs is not None:
        expenses = _num(getattr(cs, "expenses_monthly", None))

    if cash is not None and burn is not None and burn > 0:
        runway = round(cash / burn, 1) if cash > 0 else 0.0
    else:
        runway = None
    if runway is not None and ("cash_balance" in assumptions or "monthly_burn" in assumptions):
        assumptions.append("runway_months")

    return {
        "cash_balance": cash,
        "monthly_burn": burn,
        "revenue_monthly": revenue,
        "revenue_growth_rate": growth,
        "expenses_monthly": expenses,
        "runway_months": runway,
        "assumption_fields": assumptions,
    }


def _latest_record(db: Session, company_id: int, *, sample: bool):
    query = db.query(FinancialRecord).filter(FinancialRecord.company_id == company_id)
    if sample:
        query = query.filter(FinancialRecord.source_type == _SAMPLE_SOURCE)
    else:
        # manual_baseline leaves source_type NULL. NULL is an entered record.
        query = query.filter(or_(
            FinancialRecord.source_type.is_(None),
            FinancialRecord.source_type != _SAMPLE_SOURCE,
        ))
    return query.order_by(desc(FinancialRecord.period_start)).first()


EVENT_TYPES = [
    "state_update",
    "revenue_update",
    "expense_update",
    "simulation_run",
    "decision_made",
    "decision_outcome",
    "alert_triggered",
    "connector_sync",
    "truth_scan_complete",
    "fundraising_update",
    "headcount_change",
    "data_ingestion",
]


def get_twin_state(db: Session, company_id: int) -> dict:
    from server.core.cache import cache_get, cache_set, cache_key
    ck = cache_key("twin_state", str(company_id))
    cached = cache_get(ck)
    if cached:
        return cached

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {"error": "Company not found"}

    cs = db.query(CompanyState).filter(CompanyState.company_id == company_id).first()

    from server.models import TruthScan
    latest_ts = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company_id)
        .order_by(desc(TruthScan.created_at))
        .first()
    )
    ts_metrics = {}
    if latest_ts and latest_ts.outputs_json:
        ts_metrics = latest_ts.outputs_json.get("metrics", {}) if isinstance(latest_ts.outputs_json, dict) else {}

    state_json = {}
    snapshot_id = cs.snapshot_id if cs else None
    # The creation-time sample lives in state_json too (customers, mrr, …).
    # Don't surface those as derived metrics once the seed is rejected.
    if cs and not _is_stage_sample_state(cs):
        try:
            state_json = json.loads(cs.state_json) if cs.state_json else {}
        except (json.JSONDecodeError, TypeError):
            state_json = {}

    real_record = _latest_record(db, company_id, sample=False)
    sample_record = _latest_record(db, company_id, sample=True)
    resolved = resolve_twin_financials(cs, real_record, sample_record, ts_metrics)
    financials = {
        "cash_balance": resolved["cash_balance"],
        "monthly_burn": resolved["monthly_burn"],
        "revenue_monthly": resolved["revenue_monthly"],
        "revenue_growth_rate": resolved["revenue_growth_rate"],
        "expenses_monthly": resolved["expenses_monthly"],
        "assumption_fields": resolved["assumption_fields"],
    }

    latest_records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(desc(FinancialRecord.period_start))
        .limit(12)
        .all()
    )

    history = []
    for r in reversed(latest_records):
        history.append({
            "period": r.period_start.isoformat() if r.period_start else None,
            "revenue": r.revenue,
            "cogs": r.cogs,
            "opex": r.opex,
            "net_burn": r.net_burn,
            "mrr": r.mrr,
            "arr": r.arr,
            "runway_months": r.runway_months,
        })

    cash = resolved["cash_balance"]
    burn = resolved["monthly_burn"]
    runway = resolved["runway_months"]
    growth = resolved["revenue_growth_rate"]

    risks = _compute_risk_indicators(cash or 0, burn or 0, runway, growth or 0, history)

    metadata = {}
    if company.metadata_json:
        try:
            metadata = json.loads(company.metadata_json) if isinstance(company.metadata_json, str) else company.metadata_json
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    recent_events = (
        db.query(TwinEvent)
        .filter(TwinEvent.company_id == company_id)
        .order_by(desc(TwinEvent.created_at))
        .limit(20)
        .all()
    )

    result = {
        "company_id": company_id,
        "company_name": company.name,
        "snapshot_id": snapshot_id,
        "last_updated": cs.updated_at.isoformat() if cs and cs.updated_at else None,
        "financials": financials,
        "assumption_fields": resolved["assumption_fields"],
        "derived_metrics": {
            "runway_months": runway,
            "gross_margin": state_json.get("grossMargin") or state_json.get("gross_margin"),
            "ltv": state_json.get("ltv"),
            "cac": state_json.get("cac"),
            "ltv_cac_ratio": (
                round(state_json.get("ltv", 0) / state_json.get("cac", 1), 2)
                if state_json.get("ltv") and state_json.get("cac")
                else None
            ),
            "customer_count": state_json.get("customerCount") or state_json.get("customer_count"),
            "churn_rate": state_json.get("churnRate") or state_json.get("churn_rate"),
            "headcount": state_json.get("headcount"),
        },
        "risk_indicators": risks,
        "financial_history": history,
        "recent_events": [e.to_dict() for e in recent_events],
        "twin_health": _compute_twin_health(cs, history, recent_events),
        "auto_simulations": metadata.get("auto_simulations", []),
    }
    cache_set(ck, result, ttl=120)
    return result


def _compute_risk_indicators(
    cash: float, burn: float, runway: Optional[float], growth: float, history: list
) -> list:
    risks = []

    if runway is not None and runway < 6:
        severity = "critical" if runway < 3 else "warning"
        risks.append({
            "type": "runway_risk",
            "severity": severity,
            "message": f"Runway is {runway} months",
            "value": runway,
            "threshold": 6,
        })

    if burn > 0 and len(history) >= 2:
        prev_burn = abs(history[-2].get("net_burn") or 0)
        if prev_burn > 0:
            burn_change = ((burn - prev_burn) / prev_burn) * 100
            if burn_change > 20:
                risks.append({
                    "type": "burn_spike",
                    "severity": "warning",
                    "message": f"Burn increased {burn_change:.0f}% month-over-month",
                    "value": burn_change,
                    "threshold": 20,
                })

    if growth < 0:
        risks.append({
            "type": "revenue_decline",
            "severity": "warning" if growth > -10 else "critical",
            "message": f"Revenue declining at {growth:.1f}%",
            "value": growth,
            "threshold": 0,
        })

    if not risks:
        risks.append({
            "type": "healthy",
            "severity": "info",
            "message": "No significant risks detected",
            "value": None,
            "threshold": None,
        })

    return risks


def _compute_twin_health(cs, history: list, events: list) -> dict:
    score = 0
    factors = []

    if cs and cs.state_json:
        score += 25
        factors.append("canonical_state_present")
    if len(history) >= 3:
        score += 25
        factors.append("sufficient_history")
    elif len(history) >= 1:
        score += 10
        factors.append("partial_history")
    if cs and cs.updated_at:
        age = (datetime.utcnow() - cs.updated_at).days
        if age <= 7:
            score += 25
            factors.append("recently_updated")
        elif age <= 30:
            score += 15
            factors.append("moderately_stale")
        else:
            factors.append("stale_data")
    if len(events) > 0:
        score += 25
        factors.append("events_tracked")

    return {
        "score": min(score, 100),
        "factors": factors,
        "status": "excellent" if score >= 80 else "good" if score >= 50 else "needs_data",
    }


def emit_twin_event(
    db: Session, company_id: int, event_type: str, source: str, payload: Optional[dict] = None
) -> TwinEvent:
    event = TwinEvent(
        company_id=company_id,
        event_type=event_type,
        source=source,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    try:
        from server.core.cache import cache_delete, cache_key, cache_invalidate_pattern
        cache_delete(cache_key("twin_state", str(company_id)))
        cache_invalidate_pattern(f"kpis:{company_id}:*")
    except Exception:
        pass

    try:
        from server.services.intelligence_graph import process_graph_event
        process_graph_event(db, company_id, event_type, payload or {})
    except Exception as e:
        logger.debug(f"Graph event processing skipped: {e}")

    return event


def get_twin_events(
    db: Session,
    company_id: int,
    event_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    query = db.query(TwinEvent).filter(TwinEvent.company_id == company_id)
    if event_type:
        query = query.filter(TwinEvent.event_type == event_type)
    events = query.order_by(desc(TwinEvent.created_at)).offset(offset).limit(limit).all()
    return [e.to_dict() for e in events]


def get_twin_history(db: Session, company_id: int, months: int = 12) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    records = (
        db.query(FinancialRecord)
        .filter(
            FinancialRecord.company_id == company_id,
            FinancialRecord.period_start >= cutoff,
        )
        .order_by(FinancialRecord.period_start)
        .all()
    )

    events = (
        db.query(TwinEvent)
        .filter(TwinEvent.company_id == company_id, TwinEvent.created_at >= cutoff)
        .order_by(TwinEvent.created_at)
        .all()
    )

    scenario_ids = [
        s.id for s in db.query(Scenario.id).filter(Scenario.company_id == company_id).all()
    ]

    sims = []
    if scenario_ids:
        sims = (
            db.query(SimulationRun)
            .filter(
                SimulationRun.scenario_id.in_(scenario_ids),
                SimulationRun.created_at >= cutoff,
            )
            .order_by(desc(SimulationRun.created_at))
            .limit(20)
            .all()
        )

    sim_results = []
    for s in sims:
        try:
            outputs = json.loads(s.outputs_json) if isinstance(s.outputs_json, str) else s.outputs_json
        except (json.JSONDecodeError, TypeError):
            outputs = None
        sim_results.append({
            "id": s.id,
            "scenario_id": s.scenario_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "outputs": outputs,
        })

    return {
        "company_id": company_id,
        "period_months": months,
        "financial_records": [
            {
                "period": r.period_start.isoformat() if r.period_start else None,
                "revenue": r.revenue,
                "expenses": (r.cogs or 0) + (r.opex or 0),
                "net_burn": r.net_burn,
                "mrr": r.mrr,
                "runway_months": r.runway_months,
            }
            for r in records
        ],
        "events": [e.to_dict() for e in events],
        "simulations": sim_results,
    }


def get_decision_memory(db: Session, company_id: int, limit: int = 20) -> list:
    decisions = (
        db.query(CompanyDecision)
        .filter(CompanyDecision.company_id == company_id)
        .order_by(desc(CompanyDecision.created_at))
        .limit(limit)
        .all()
    )

    return [d.to_dict() for d in decisions]


TWIN_ITERATIONS = 500
TWIN_HORIZON_MONTHS = 24
SUSTAINABLE_SENTINEL = 900  # enhanced MC emits 999 for "never ran out of cash"


def _engine_margin_clamp(gm_pct: float) -> float:
    """The margin the enhanced engine will actually use after its own clamp."""
    try:
        from server.core.units import clamp_gross_margin_pct  # type: ignore
        return float(clamp_gross_margin_pct(gm_pct))
    except Exception:
        return max(10.0, min(95.0, float(gm_pct)))


def _latest_gross_margin_pct(record) -> Optional[float]:
    """Gross margin (percent) from the latest P&L record, or None if unknown."""
    if record is None:
        return None
    gm = getattr(record, "gross_margin", None)
    if gm is not None:
        try:
            v = float(gm)
            if v == v:
                return v * 100.0 if abs(v) <= 1.0 else v
        except (TypeError, ValueError):
            pass
    revenue = getattr(record, "revenue", None) or 0
    cogs = getattr(record, "cogs", None)
    if revenue and revenue > 0 and cogs is not None and cogs > 0:
        return (revenue - cogs) / revenue * 100.0
    return None


def build_twin_engine_inputs(cs, latest_record) -> dict:
    """Enhanced Monte Carlo inputs from the company state, on the canonical burn.

    CompanyState.monthly_burn is NET burn (total costs incl. COGS - revenue) and
    expenses_monthly is total costs incl. COGS. The engine computes
    ``revenue * gross_margin - (opex + payroll + other)``, so its cost lines
    must EXCLUDE COGS. The old code passed total expenses as opex/payroll/other
    AND applied a hardcoded 70% margin, counting COGS twice.

    Cost lines are sized from the margin the engine will really use (after its
    clamp) so month one burns exactly the dashboard's net burn. With no known
    margin the engine's top margin is used and COGS is treated as a fixed cost;
    ``gross_margin_known`` says so.
    """
    revenue = float(cs.revenue_monthly or 0)
    net_burn = float(cs.monthly_burn or 0)
    expenses = float(cs.expenses_monthly or 0)
    cash = float(cs.cash_balance or 0)
    try:
        growth = float(cs.revenue_growth_rate or 0)
    except (TypeError, ValueError):
        growth = 0.0

    if net_burn > 0:
        total_costs = net_burn + revenue
    elif expenses > 0:
        total_costs = expenses
    else:
        total_costs = revenue

    gm_known = _latest_gross_margin_pct(latest_record)
    gm_engine = _engine_margin_clamp(gm_known if gm_known is not None else 100.0)
    costs_ex_cogs = max(0.0, total_costs - revenue * (1 - gm_engine / 100.0))

    # Split by the latest P&L's real shares; with none, everything is opex
    # (no invented 30/50/20 split).
    shares = (0.0, 0.0, 0.0)
    if latest_record is not None:
        parts = [max(0.0, float(getattr(latest_record, k, 0) or 0)) for k in ("opex", "payroll", "other_costs")]
        tot = sum(parts)
        if tot > 0:
            shares = tuple(x / tot for x in parts)
    if sum(shares) <= 0:
        shares = (1.0, 0.0, 0.0)

    # Monthly revenue churn (percent) only when the company has one on file;
    # the engine's default would otherwise apply an invented 5%.
    churn_pct = 0.0
    try:
        state = json.loads(cs.state_json) if getattr(cs, "state_json", None) else {}
    except (TypeError, ValueError):
        state = {}
    for key in ("churn_rate", "churnRate"):
        raw = state.get(key) if isinstance(state, dict) else None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw >= 0:
            churn_pct = raw * 100.0 if raw <= 1 else float(raw)
            break

    return {
        "churn_rate": churn_pct,
        "baseline_revenue": revenue,
        "baseline_growth_rate": growth,
        "gross_margin": gm_engine,
        "opex": costs_ex_cogs * shares[0],
        "payroll": costs_ex_cogs * shares[1],
        "other_costs": costs_ex_cogs * shares[2],
        "cash_balance": cash,
        "gross_margin_known": gm_known is not None,
        "net_burn": max(0.0, total_costs - revenue),
    }


def summarize_twin_results(results: dict) -> dict:
    """Flat P10/P50/P90 + 24m survival from the enhanced engine's nested output."""
    runway = results.get("runway") or {}
    survival = results.get("survivalProbability") or {}
    cfg = results.get("config") or {}

    def runway_value(key):
        v = runway.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    s24 = survival.get("24m")
    return {
        "p10_runway": runway_value("p10"),
        "p50_runway": runway_value("p50"),
        "p90_runway": runway_value("p90"),
        # Fraction (0-1) of runs with cash left after 24 months.
        "survival_probability": (float(s24) / 100.0) if isinstance(s24, (int, float)) else None,
        "sustainable_rate": runway.get("sustainableRate"),
        "iterations": cfg.get("iterations"),
        "horizon_months": cfg.get("horizonMonths"),
    }


def run_twin_simulation(
    db: Session, company_id: int, scenario_config: dict
) -> dict:
    cs = db.query(CompanyState).filter(CompanyState.company_id == company_id).first()
    if not cs:
        return {"error": "No company state available for simulation"}

    try:
        from server.simulate.enhanced_monte_carlo import (
            run_enhanced_monte_carlo, EnhancedSimulationInputs, SimulationConfig
        )
        import dataclasses
        from types import SimpleNamespace
        from server.models import TruthScan

        latest_ts = (
            db.query(TruthScan)
            .filter(TruthScan.company_id == company_id)
            .order_by(desc(TruthScan.created_at))
            .first()
        )
        ts_metrics = {}
        if latest_ts and isinstance(getattr(latest_ts, "outputs_json", None), dict):
            ts_metrics = latest_ts.outputs_json.get("metrics", {}) or {}

        real_record = _latest_record(db, company_id, sample=False)
        sample_record = _latest_record(db, company_id, sample=True)
        resolved = resolve_twin_financials(cs, real_record, sample_record, ts_metrics)
        if resolved["cash_balance"] is None or resolved["monthly_burn"] is None:
            return {
                "error": "Cash and monthly burn are not on file, so nothing was simulated.",
                "error_code": "missing_financials",
            }

        # Copy so the engine sees entered cash/burn/revenue, not the
        # creation-time CompanyState sample, and so we don't write that
        # sample back onto the stored row.
        engine_cs = SimpleNamespace(
            revenue_monthly=resolved["revenue_monthly"] or 0,
            monthly_burn=resolved["monthly_burn"],
            expenses_monthly=resolved["expenses_monthly"] or 0,
            cash_balance=resolved["cash_balance"],
            revenue_growth_rate=(
                resolved["revenue_growth_rate"]
                if resolved["revenue_growth_rate"] is not None
                else getattr(cs, "revenue_growth_rate", 0)
            ),
            snapshot_id=getattr(cs, "snapshot_id", None),
            state_json=getattr(cs, "state_json", None),
        )
        base = build_twin_engine_inputs(engine_cs, real_record or sample_record)

        kwargs = dict(
            baseline_revenue=base["baseline_revenue"],
            baseline_growth_rate=base["baseline_growth_rate"],
            gross_margin=base["gross_margin"],
            opex=base["opex"],
            payroll=base["payroll"],
            other_costs=base["other_costs"],
            cash_balance=base["cash_balance"],
            churn_rate=base["churn_rate"],
            pricing_change_pct=scenario_config.get("pricing_change_pct", 0) or 0,
            growth_uplift_pct=scenario_config.get("growth_uplift_pct", 0) or 0,
            burn_reduction_pct=scenario_config.get("burn_reduction_pct", 0) or 0,
            fundraise_month=scenario_config.get("fundraise_month"),
            fundraise_amount=scenario_config.get("fundraise_amount", 0) or 0,
        )

        hiring_plan = [h for h in (scenario_config.get("hiring_plan") or []) if isinstance(h, dict)]
        hiring_mode = "none"
        if hiring_plan:
            field_names = {f.name for f in dataclasses.fields(EnhancedSimulationInputs)}
            if "hiring_plan" in field_names:
                kwargs["hiring_plan"] = hiring_plan
                hiring_mode = "by_start_month"
            else:
                # Engine without per-month hires: add every planned hire's cost
                # from month one (conservative) rather than dropping them.
                added = 0.0
                for h in hiring_plan:
                    try:
                        added += max(0.0, float(h.get("count", 1) or 0)) * max(0.0, float(h.get("monthly_cost", 0) or 0))
                    except (TypeError, ValueError):
                        continue
                kwargs["payroll"] = kwargs["payroll"] + added
                hiring_mode = "from_month_1"

        inputs = EnhancedSimulationInputs(**kwargs)
        config = SimulationConfig(
            iterations=TWIN_ITERATIONS, horizon_months=TWIN_HORIZON_MONTHS, seed=42
        )
        results = run_enhanced_monte_carlo(inputs, config)
        summary = summarize_twin_results(results)

        emit_twin_event(db, company_id, "simulation_run", "digital_twin", {
            "scenario": scenario_config,
            "p50_runway": summary["p50_runway"],
            "survival_probability": summary["survival_probability"],
        })

        return {
            "company_id": company_id,
            "snapshot_id": cs.snapshot_id,
            "scenario": scenario_config,
            "summary": summary,
            "inputs": {
                "gross_margin_pct": base["gross_margin"],
                "gross_margin_known": base["gross_margin_known"],
                "net_burn": base["net_burn"],
                "hiring_plan_mode": hiring_mode,
            },
            "results": results,
        }

    except Exception as e:
        # No invented fallback: the old path fabricated P10 = 0.7x and
        # P90 = 1.4x of a naive runway and presented them as a distribution.
        logger.error(f"Twin simulation failed for company {company_id}: {e}")
        return {
            "error": "The simulation engine failed; no results were produced.",
            "error_code": "simulation_failed",
        }
