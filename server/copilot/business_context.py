"""
Business Context Engine for Copilot.

Builds a comprehensive company context object before every copilot response,
pulling data from financial records, truth scans, connected data sources,
and computed metrics to give the AI deep company understanding.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_business_context(company, db: Session) -> Dict[str, Any]:
    from server.models.truth_scan import TruthScan
    from server.models.financial import FinancialRecord, FinancialMetricPoint
    from server.models.scenario import Scenario
    from server.models.simulation_run import SimulationRun

    ctx: Dict[str, Any] = {
        "company": _build_company_profile(company),
        "financials": {},
        "customers": {},
        "product": {},
        "team": {},
        "trends": {},
        "connectors": {},
        "data_gaps": [],
    }

    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()

    if truth_scan and truth_scan.outputs_json:
        ctx["financials"] = _extract_financial_metrics(truth_scan.outputs_json)
    
    records = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).limit(12).all()

    if records:
        ctx["financials"].update(_compute_trends(records))
        if not ctx["financials"].get("revenue"):
            latest = records[0]
            ctx["financials"].update(_extract_from_record(latest))
        ctx["team"] = _extract_team_data(records)

    uploaded = db.query(FinancialMetricPoint).filter(
        FinancialMetricPoint.company_id == company.id
    ).order_by(FinancialMetricPoint.period.desc()).limit(200).all()

    if uploaded:
        ctx["financials"]["uploaded_metrics"] = _summarize_uploaded_metrics(uploaded)

    latest_sim = None
    scenarios = db.query(Scenario).filter(
        Scenario.company_id == company.id
    ).order_by(Scenario.created_at.desc()).limit(5).all()

    for s in scenarios:
        sim = db.query(SimulationRun).filter(
            SimulationRun.scenario_id == s.id
        ).order_by(SimulationRun.created_at.desc()).first()
        if sim and (latest_sim is None or sim.created_at > latest_sim.created_at):
            latest_sim = sim

    if latest_sim and latest_sim.outputs_json:
        ctx["financials"]["latest_simulation"] = {
            "runway": latest_sim.outputs_json.get("runway", {}),
            "survival": latest_sim.outputs_json.get("survival", {}),
            "summary": latest_sim.outputs_json.get("summary", {}),
            "computed_at": latest_sim.created_at.isoformat() if latest_sim.created_at else None,
        }

    connector_data = _extract_connector_data(company)
    ctx["connectors"] = connector_data.get("connected", {})
    ctx["customers"].update(connector_data.get("customer_data", {}))
    ctx["product"].update(connector_data.get("product_data", {}))

    ctx["data_gaps"] = _identify_data_gaps(ctx)

    return ctx


def _build_company_profile(company) -> Dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name or "Unknown",
        "industry": company.industry or "Not specified",
        "stage": company.stage or "Not specified",
        "currency": company.currency or "USD",
        "website": getattr(company, "website", None),
        "description": getattr(company, "description", None),
    }


def _extract_financial_metrics(ts_data: Dict[str, Any]) -> Dict[str, Any]:
    metrics = ts_data.get("metrics", {})
    result = {}

    metric_map = {
        "revenue": "monthly_revenue",
        "mrr": "mrr",
        "arr": "arr",
        "cash_balance": "cash_balance",
        "net_burn": "net_burn",
        "runway_months": "runway_months",
        "gross_margin": "gross_margin",
        "opex": "opex",
        "payroll": "payroll",
        "cogs": "cogs",
        "other_costs": "other_costs",
        "headcount": "headcount",
        "customers": "customers",
        "ltv": "ltv",
        "cac": "cac",
        "ltv_cac_ratio": "ltv_cac_ratio",
        "arpu": "arpu",
        "churn_rate": "churn_rate",
        "nrr": "nrr",
        "mom_growth": "revenue_growth_mom",
    }

    for out_key, ts_key in metric_map.items():
        val = metrics.get(ts_key) or metrics.get(out_key)
        if val is not None:
            try:
                result[out_key] = float(val)
            except (ValueError, TypeError):
                result[out_key] = val

    result["data_confidence"] = ts_data.get("data_confidence_score", 0)
    result["quality_of_growth"] = ts_data.get("quality_of_growth_index", 0)
    result["computed_at"] = ts_data.get("computed_at", None)

    return result


def _extract_from_record(rec) -> Dict[str, Any]:
    result = {}
    fields = ["revenue", "mrr", "arr", "cash_balance", "net_burn", "runway_months",
              "gross_margin", "opex", "payroll", "cogs", "other_costs", "headcount",
              "customers", "ltv", "cac", "ltv_cac_ratio", "arpu", "mom_growth",
              "marketing_expense"]
    for f in fields:
        val = getattr(rec, f, None)
        if val is not None:
            result[f] = float(val)
    return result


def _compute_trends(records: list) -> Dict[str, Any]:
    if len(records) < 2:
        return {}

    trends: Dict[str, Any] = {}

    revenues = [(r.period_end, float(r.revenue)) for r in records if r.revenue and r.period_end]
    if len(revenues) >= 2:
        revenues.sort(key=lambda x: x[0])
        recent = revenues[-1][1]
        oldest = revenues[0][1]
        months = len(revenues)
        if oldest > 0 and months > 1:
            total_growth = (recent - oldest) / oldest * 100
            avg_monthly = total_growth / (months - 1)
            trends["revenue_trend"] = {
                "direction": "growing" if total_growth > 0 else "declining",
                "total_change_pct": round(total_growth, 1),
                "avg_monthly_growth_pct": round(avg_monthly, 1),
                "months_tracked": months,
                "latest": recent,
                "earliest": oldest,
            }

    burns = [(r.period_end, float(r.net_burn)) for r in records if r.net_burn is not None and r.period_end]
    if len(burns) >= 2:
        burns.sort(key=lambda x: x[0])
        recent_burn = burns[-1][1]
        oldest_burn = burns[0][1]
        if oldest_burn != 0:
            burn_change = (recent_burn - oldest_burn) / abs(oldest_burn) * 100
            trends["burn_trend"] = {
                "direction": "increasing" if burn_change > 0 else "decreasing",
                "change_pct": round(burn_change, 1),
                "latest": recent_burn,
                "earliest": oldest_burn,
            }

    margins = [(r.period_end, float(r.gross_margin)) for r in records if r.gross_margin is not None and r.period_end]
    if len(margins) >= 2:
        margins.sort(key=lambda x: x[0])
        margin_delta = margins[-1][1] - margins[0][1]
        trends["margin_trend"] = {
            "direction": "improving" if margin_delta > 0 else "declining",
            "change_pp": round(margin_delta, 1),
            "latest": margins[-1][1],
            "earliest": margins[0][1],
        }

    cacs = [(r.period_end, float(r.cac)) for r in records if r.cac is not None and r.period_end]
    if len(cacs) >= 2:
        cacs.sort(key=lambda x: x[0])
        cac_change = cacs[-1][1] - cacs[0][1]
        trends["cac_trend"] = {
            "direction": "increasing" if cac_change > 0 else "decreasing",
            "latest": cacs[-1][1],
            "earliest": cacs[0][1],
        }

    return {"trends": trends}


def _extract_team_data(records: list) -> Dict[str, Any]:
    team = {}
    for rec in records:
        if rec.headcount:
            team["current_headcount"] = int(rec.headcount)
            break

    headcounts = [(r.period_end, int(r.headcount)) for r in records if r.headcount and r.period_end]
    if len(headcounts) >= 2:
        headcounts.sort(key=lambda x: x[0])
        net_change = headcounts[-1][1] - headcounts[0][1]
        team["headcount_change"] = net_change
        team["headcount_trend"] = "growing" if net_change > 0 else ("shrinking" if net_change < 0 else "stable")

    for rec in records:
        if rec.payroll and rec.headcount and rec.headcount > 0:
            team["avg_cost_per_employee"] = round(float(rec.payroll) / int(rec.headcount), 0)
            break

    payrolls = [float(r.payroll) for r in records if r.payroll]
    if payrolls:
        team["monthly_payroll"] = payrolls[0]
        revenues = [float(r.revenue) for r in records if r.revenue]
        if revenues and revenues[0] > 0:
            team["payroll_as_pct_of_revenue"] = round(payrolls[0] / revenues[0] * 100, 1)

    return team


def _summarize_uploaded_metrics(metrics: list) -> Dict[str, Any]:
    by_key: Dict[str, list] = {}
    for m in metrics:
        key = m.metric_key
        if key not in by_key:
            by_key[key] = []
        if len(by_key[key]) < 6:
            by_key[key].append({
                "period": m.period.isoformat() if m.period else None,
                "value": float(m.value),
            })

    summary = {}
    for key, points in by_key.items():
        if points:
            summary[key] = {
                "latest_value": points[0]["value"],
                "data_points": len(points),
                "latest_period": points[0]["period"],
            }
    return summary


def _extract_connector_data(company) -> Dict[str, Any]:
    result = {
        "connected": {},
        "customer_data": {},
        "product_data": {},
    }

    metadata = getattr(company, "metadata_json", None) or {}
    connectors = metadata.get("connectors", {})

    if not connectors:
        return result

    for name, config in connectors.items():
        if not isinstance(config, dict):
            continue
        status = config.get("status", "unknown")
        if status in ("connected", "synced", "active"):
            result["connected"][name] = {
                "status": status,
                "last_sync": config.get("last_sync"),
            }

            synced_data = config.get("synced_data", {})

            if name in ("shopify", "stripe", "chargebee", "recurly"):
                if synced_data.get("customers"):
                    result["customer_data"][f"{name}_customers"] = synced_data["customers"]
                if synced_data.get("products"):
                    result["product_data"][f"{name}_products"] = synced_data["products"]
                if synced_data.get("revenue_data"):
                    result["customer_data"][f"{name}_revenue"] = synced_data["revenue_data"]

            if name in ("google_analytics", "mixpanel", "amplitude"):
                if synced_data.get("demographics"):
                    result["customer_data"][f"{name}_demographics"] = synced_data["demographics"]
                if synced_data.get("acquisition_channels"):
                    result["customer_data"][f"{name}_channels"] = synced_data["acquisition_channels"]
                if synced_data.get("geography"):
                    result["customer_data"][f"{name}_geography"] = synced_data["geography"]

            if name in ("hubspot", "salesforce", "pipedrive", "close_crm"):
                if synced_data.get("pipeline"):
                    result["customer_data"][f"{name}_pipeline"] = synced_data["pipeline"]
                if synced_data.get("deals"):
                    result["customer_data"][f"{name}_deals"] = synced_data["deals"]

            if name in ("gusto", "rippling", "deel", "razorpayx", "keka", "greythr"):
                if synced_data.get("payroll"):
                    result["customer_data"][f"{name}_payroll"] = synced_data["payroll"]
                if synced_data.get("departments"):
                    result["customer_data"][f"{name}_departments"] = synced_data["departments"]

    return result


def _identify_data_gaps(ctx: Dict[str, Any]) -> List[str]:
    gaps = []
    fin = ctx.get("financials", {})

    if not fin.get("revenue") and not fin.get("mrr"):
        gaps.append("No revenue data - upload financial records or connect Stripe/Shopify")
    if not fin.get("cash_balance"):
        gaps.append("No cash balance data - needed for runway calculations")
    if not fin.get("gross_margin") and not fin.get("cogs"):
        gaps.append("No margin/COGS data - connect accounting software or upload P&L")
    if not fin.get("cac") and not fin.get("ltv"):
        gaps.append("No CAC/LTV data - connect CRM or analytics for unit economics")
    if not ctx.get("team", {}).get("current_headcount"):
        gaps.append("No headcount data - connect HR/payroll system or enter manually")
    if not ctx.get("connectors"):
        gaps.append("No data connectors linked - connect Stripe, Shopify, or QuickBooks for richer analysis")
    if not ctx.get("customers"):
        gaps.append("No customer demographics - connect Google Analytics or Shopify for demographic-fit analysis")

    return gaps


def format_context_for_prompt(ctx: Dict[str, Any]) -> str:
    parts = []

    company = ctx.get("company", {})
    parts.append(f"=== COMPANY PROFILE ===")
    parts.append(f"Name: {company.get('name', 'Unknown')}")
    parts.append(f"Industry: {company.get('industry', 'Not specified')}")
    parts.append(f"Stage: {company.get('stage', 'Not specified')}")
    parts.append(f"Currency: {company.get('currency', 'USD')}")

    fin = ctx.get("financials", {})
    if fin:
        parts.append(f"\n=== FINANCIAL METRICS ===")
        metric_display = {
            "revenue": ("Monthly Revenue", "${:,.0f}"),
            "mrr": ("MRR", "${:,.0f}"),
            "arr": ("ARR", "${:,.0f}"),
            "cash_balance": ("Cash Balance", "${:,.0f}"),
            "net_burn": ("Net Burn", "${:,.0f}/mo"),
            "runway_months": ("Runway", "{:.1f} months"),
            "gross_margin": ("Gross Margin", "{:.1f}%"),
            "opex": ("Operating Expenses", "${:,.0f}/mo"),
            "payroll": ("Payroll", "${:,.0f}/mo"),
            "cogs": ("COGS", "${:,.0f}/mo"),
            "headcount": ("Headcount", "{:.0f}"),
            "customers": ("Customers", "{:.0f}"),
            "ltv": ("LTV", "${:,.0f}"),
            "cac": ("CAC", "${:,.0f}"),
            "ltv_cac_ratio": ("LTV:CAC", "{:.1f}x"),
            "arpu": ("ARPU", "${:,.0f}"),
            "churn_rate": ("Churn Rate", "{:.1f}%"),
            "nrr": ("NRR", "{:.1f}%"),
            "mom_growth": ("MoM Growth", "{:.1f}%"),
        }
        for key, (label, fmt) in metric_display.items():
            val = fin.get(key)
            if val is not None:
                try:
                    parts.append(f"  {label}: {fmt.format(val)}")
                except (ValueError, TypeError):
                    parts.append(f"  {label}: {val}")

        if fin.get("data_confidence"):
            parts.append(f"  Data Confidence Score: {fin['data_confidence']}/100")

    trends = fin.get("trends", {})
    if trends:
        parts.append(f"\n=== TRENDS (Historical) ===")
        if trends.get("revenue_trend"):
            rt = trends["revenue_trend"]
            parts.append(f"  Revenue: {rt['direction']} ({rt['total_change_pct']:+.1f}% over {rt['months_tracked']} months, avg {rt['avg_monthly_growth_pct']:+.1f}%/mo)")
        if trends.get("burn_trend"):
            bt = trends["burn_trend"]
            parts.append(f"  Burn: {bt['direction']} ({bt['change_pct']:+.1f}% change)")
        if trends.get("margin_trend"):
            mt = trends["margin_trend"]
            parts.append(f"  Gross Margin: {mt['direction']} ({mt['change_pp']:+.1f}pp, now {mt['latest']:.1f}%)")
        if trends.get("cac_trend"):
            ct = trends["cac_trend"]
            parts.append(f"  CAC: {ct['direction']} (${ct['latest']:,.0f} currently)")

    sim = fin.get("latest_simulation")
    if sim:
        parts.append(f"\n=== LATEST SIMULATION ===")
        runway = sim.get("runway", {})
        survival = sim.get("survival", {})
        if runway:
            parts.append(f"  Runway: P10={runway.get('p10', 'N/A')}mo, P50={runway.get('p50', 'N/A')}mo, P90={runway.get('p90', 'N/A')}mo")
        if survival:
            parts.append(f"  Survival: 12mo={survival.get('12_month', 'N/A')}, 18mo={survival.get('18_month', 'N/A')}, 24mo={survival.get('24_month', 'N/A')}")
        if sim.get("computed_at"):
            parts.append(f"  Computed: {sim['computed_at']}")

    team = ctx.get("team", {})
    if team:
        parts.append(f"\n=== TEAM ===")
        if team.get("current_headcount"):
            parts.append(f"  Headcount: {team['current_headcount']}")
        if team.get("headcount_trend"):
            parts.append(f"  Trend: {team['headcount_trend']} ({team.get('headcount_change', 0):+d})")
        if team.get("avg_cost_per_employee"):
            parts.append(f"  Avg Cost/Employee: ${team['avg_cost_per_employee']:,.0f}/mo")
        if team.get("payroll_as_pct_of_revenue"):
            parts.append(f"  Payroll as % of Revenue: {team['payroll_as_pct_of_revenue']:.1f}%")

    customers = ctx.get("customers", {})
    if customers:
        parts.append(f"\n=== CUSTOMER DATA (from connectors) ===")
        for source, data in customers.items():
            parts.append(f"  [{source}]: {_summarize_dict(data)}")

    product = ctx.get("product", {})
    if product:
        parts.append(f"\n=== PRODUCT DATA (from connectors) ===")
        for source, data in product.items():
            parts.append(f"  [{source}]: {_summarize_dict(data)}")

    connectors = ctx.get("connectors", {})
    if connectors:
        parts.append(f"\n=== CONNECTED DATA SOURCES ===")
        for name, info in connectors.items():
            parts.append(f"  {name}: {info.get('status', 'unknown')} (last sync: {info.get('last_sync', 'N/A')})")

    gaps = ctx.get("data_gaps", [])
    if gaps:
        parts.append(f"\n=== DATA GAPS (would improve analysis) ===")
        for gap in gaps:
            parts.append(f"  - {gap}")

    return "\n".join(parts)


def _summarize_dict(data: Any, max_items: int = 5) -> str:
    if isinstance(data, dict):
        items = list(data.items())[:max_items]
        return ", ".join(f"{k}: {v}" for k, v in items)
    if isinstance(data, list):
        return f"{len(data)} items"
    return str(data)[:200]
