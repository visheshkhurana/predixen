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

        revenue = cs.revenue_monthly or 0
        growth_rate = float(cs.revenue_growth_rate or 0)
        expenses = cs.expenses_monthly or 0
        cash = cs.cash_balance or 0

        burn = cs.monthly_burn or 0
        if expenses == 0 and burn > 0:
            expenses = burn

        opex = expenses * 0.3
        payroll = expenses * 0.5
        other_costs = expenses * 0.2

        inputs = EnhancedSimulationInputs(
            baseline_revenue=revenue,
            baseline_growth_rate=growth_rate,
            gross_margin=70,
            opex=opex,
            payroll=payroll,
            other_costs=other_costs,
            cash_balance=cash,
            pricing_change_pct=scenario_config.get("pricing_change_pct", 0),
            growth_uplift_pct=scenario_config.get("growth_uplift_pct", 0),
            burn_reduction_pct=scenario_config.get("burn_reduction_pct", 0),
            fundraise_month=scenario_config.get("fundraise_month"),
            fundraise_amount=scenario_config.get("fundraise_amount", 0),
        )

        config = SimulationConfig(iterations=500, horizon_months=24, seed=42)
        results = run_enhanced_monte_carlo(inputs, config)

        emit_twin_event(db, company_id, "simulation_run", "digital_twin", {
            "scenario": scenario_config,
            "p50_runway": results.get("p50_runway"),
            "survival_probability": results.get("survival_probability"),
        })

        return {
            "company_id": company_id,
            "snapshot_id": cs.snapshot_id,
            "scenario": scenario_config,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Twin simulation failed for company {company_id}: {e}")

        cash = cs.cash_balance or 0
        burn = cs.monthly_burn or 0
        base_runway = cash / burn if burn > 0 else 24

        adj = 1.0
        adj -= scenario_config.get("burn_reduction_pct", 0) / 100
        adj += len(scenario_config.get("hiring_plan", [])) * 0.05

        p50 = round(base_runway / adj, 1)
        p10 = round(p50 * 0.7, 1)
        p90 = round(p50 * 1.4, 1)

        survival = min(0.95, p50 / 24) if p50 > 0 else 0

        emit_twin_event(db, company_id, "simulation_run", "digital_twin_fallback", {
            "scenario": scenario_config,
            "p50_runway": p50,
            "fallback": True,
        })

        return {
            "company_id": company_id,
            "snapshot_id": cs.snapshot_id,
            "scenario": scenario_config,
            "fallback": True,
            "results": {
                "p10_runway": p10,
                "p50_runway": p50,
                "p90_runway": p90,
                "survival_probability": round(survival, 3),
                "months_projected": 24,
            },
        }
