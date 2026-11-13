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
from sqlalchemy import desc

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

    financials = {}
    state_json = {}
    snapshot_id = None
    if cs:
        financials = {
            "cash_balance": cs.cash_balance,
            "monthly_burn": cs.monthly_burn,
            "revenue_monthly": cs.revenue_monthly,
            "revenue_growth_rate": float(cs.revenue_growth_rate) if cs.revenue_growth_rate else 0,
            "expenses_monthly": cs.expenses_monthly,
        }
        snapshot_id = cs.snapshot_id
        try:
            state_json = json.loads(cs.state_json) if cs.state_json else {}
        except (json.JSONDecodeError, TypeError):
            state_json = {}

    fr_cash = None
    fr_burn = None
    fr_revenue = None
    latest_fr = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(desc(FinancialRecord.period_start))
        .first()
    )
    if latest_fr:
        fr_cash = float(latest_fr.cash_balance) if latest_fr.cash_balance else None
        fr_burn = float(latest_fr.net_burn) if latest_fr.net_burn else None
        if fr_burn is None and latest_fr.opex:
            rev = float(latest_fr.revenue) if latest_fr.revenue else 0
            fr_burn = float(latest_fr.opex) + (float(latest_fr.payroll) if latest_fr.payroll else 0) - rev
        fr_revenue = float(latest_fr.revenue) if latest_fr.revenue else None

    if ts_metrics:
        def _ts_val(key, *alt_keys):
            v = ts_metrics.get(key)
            if v is None:
                for k in alt_keys:
                    v = ts_metrics.get(k)
                    if v is not None:
                        break
            if isinstance(v, dict):
                return v.get("value")
            return v

        ts_cash = _ts_val("cash_balance", "cash_on_hand", "cash")
        ts_burn = _ts_val("monthly_burn", "net_burn", "burn_rate")
        ts_revenue = _ts_val("monthly_revenue", "mrr", "revenue")

        cs_cash = financials.get("cash_balance") or 0
        best_cash = max(float(ts_cash) if ts_cash else 0, float(fr_cash) if fr_cash else 0)
        if best_cash > 0 and (cs_cash == 0 or (best_cash > cs_cash * 5 and best_cash > 100000)):
            financials["cash_balance"] = best_cash

        cs_burn = financials.get("monthly_burn") or 0
        best_burn = float(ts_burn) if ts_burn else (float(fr_burn) if fr_burn else 0)
        if best_burn > 0 and (cs_burn == 0 or (best_burn > cs_burn * 5 and best_burn > 10000)):
            financials["monthly_burn"] = best_burn

        cs_rev = financials.get("revenue_monthly") or 0
        best_rev = max(float(ts_revenue) if ts_revenue else 0, float(fr_revenue) if fr_revenue else 0)
        if best_rev > 0 and (cs_rev == 0 or (best_rev > cs_rev * 5 and best_rev > 10000)):
            financials["revenue_monthly"] = best_rev
    elif latest_fr:
        if not financials.get("cash_balance") and fr_cash:
            financials["cash_balance"] = fr_cash
        if not financials.get("monthly_burn") and fr_burn:
            financials["monthly_burn"] = fr_burn
        if not financials.get("revenue_monthly") and fr_revenue:
            financials["revenue_monthly"] = fr_revenue

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

    cash = financials.get("cash_balance") or 0
    burn = financials.get("monthly_burn") or 0
    revenue = financials.get("revenue_monthly") or 0
    runway = round(cash / burn, 1) if burn and burn > 0 else None
    growth = financials.get("revenue_growth_rate", 0)

    risks = _compute_risk_indicators(cash, burn, runway, growth, history)

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

        latest_record = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.company_id == company_id)
            .order_by(desc(FinancialRecord.period_start))
            .first()
        )
        base = build_twin_engine_inputs(cs, latest_record)

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
