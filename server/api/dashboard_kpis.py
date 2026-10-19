"""
Dashboard KPIs API endpoint for founder-friendly metrics with historical data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.core.burn import burn_summary, net_burn as record_net_burn


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class TimePeriod(str, Enum):
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"
    LAST_12_MONTHS = "last_12_months"


METRIC_DEFINITIONS = {
    "net_burn": {
        "name": "Net Burn",
        "formula": "Total Operating Expenses - Revenue",
        "description": "Monthly cash consumption after accounting for revenue. Positive = burning cash, Negative = profitable.",
        "unit": "currency",
        "data_sources": ["P&L Statement", "Cash Flow Statement"]
    },
    "revenue_growth_yoy": {
        "name": "Revenue Growth (YoY)",
        "formula": "(Current Period Revenue - Prior Year Revenue) / Prior Year Revenue × 100",
        "description": "Year-over-year revenue growth percentage.",
        "unit": "percent",
        "data_sources": ["P&L Statement"]
    },
    "burn_multiple": {
        "name": "Burn Multiple",
        "formula": "Net Burn / Net New ARR",
        "description": "Measures capital efficiency - how much you burn to generate each dollar of new ARR. Lower is better.",
        "unit": "multiple",
        "data_sources": ["P&L Statement", "ARR/MRR Data"]
    },
    "concentration_top5": {
        "name": "Top-5 Concentration",
        "formula": "Revenue from Top 5 Customers / Total Revenue × 100",
        "description": "Percentage of revenue from your largest 5 customers. Lower concentration = lower risk.",
        "unit": "percent",
        "data_sources": ["Customer Revenue Data"]
    },
    "runway": {
        "name": "Runway",
        "formula": "Cash on Hand / Monthly Net Burn",
        "description": "Months of operation remaining at current burn rate.",
        "unit": "months",
        "data_sources": ["Balance Sheet", "P&L Statement"]
    },
    "gross_margin": {
        "name": "Gross Margin",
        "formula": "(Revenue - COGS) / Revenue × 100",
        "description": "Percentage of revenue remaining after direct costs.",
        "unit": "percent",
        "data_sources": ["P&L Statement"]
    }
}


def calculate_change_percent(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Calculate percentage change between two values."""
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def determine_trend(current: Optional[float], previous: Optional[float], threshold: float = 0.05) -> str:
    """Determine trend direction based on change."""
    if current is None or previous is None or previous == 0:
        return "stable"
    change = (current - previous) / abs(previous)
    if change > threshold:
        return "up"
    elif change < -threshold:
        return "down"
    return "stable"


def determine_status(
    metric_name: str,
    value: float,
    benchmark: Optional[float] = None
) -> str:
    """Determine health status based on metric and value."""
    if value is None:
        return "missing"
    
    thresholds = {
        "runway": {"critical": 6, "warning": 12},
        "grossMargin": {"critical": 40, "warning": 60},
        "burnMultiple": {"critical": 3, "warning": 2},
    }
    
    if metric_name in thresholds:
        t = thresholds[metric_name]
        if metric_name == "burnMultiple":
            if value > t["critical"]:
                return "critical"
            elif value > t["warning"]:
                return "warning"
        else:
            if value < t["critical"]:
                return "critical"
            elif value < t["warning"]:
                return "warning"
    
    return "healthy"


def generate_recommendations(kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate context-aware recommendations based on KPIs."""
    recommendations = []
    
    runway = kpis.get("runway", {}).get("currentValue")
    gross_margin = kpis.get("grossMargin", {}).get("currentValue")
    burn_multiple = kpis.get("burnMultiple", {}).get("currentValue")
    
    if runway is not None and runway < 12:
        recommendations.append({
            "id": "extend-runway",
            "title": "Extend Your Runway",
            "description": f"Your runway is {runway:.0f} months. Consider reducing burn by 15-20% or exploring bridge financing options.",
            "priority": "high" if runway < 6 else "medium",
            "action": "Run burn reduction scenario"
        })
    
    if gross_margin is not None and gross_margin < 60:
        recommendations.append({
            "id": "improve-margins",
            "title": "Optimize Gross Margins",
            "description": f"Your {gross_margin:.0f}% gross margin is below the 70% SaaS benchmark. Review pricing and COGS structure.",
            "priority": "medium",
            "action": "Analyze margin breakdown"
        })
    
    if burn_multiple is not None and burn_multiple > 2:
        recommendations.append({
            "id": "improve-efficiency",
            "title": "Improve Capital Efficiency",
            "description": f"Burn multiple of {burn_multiple:.1f}x indicates inefficient growth. Focus on revenue acceleration or cost optimization.",
            "priority": "high" if burn_multiple > 3 else "medium",
            "action": "View efficiency analysis"
        })
    
    if not recommendations:
        recommendations.append({
            "id": "maintain-course",
            "title": "Maintain Current Trajectory",
            "description": "Your metrics are healthy. Continue monitoring and consider accelerating growth.",
            "priority": "low",
            "action": "Explore growth scenarios"
        })
    
    return recommendations[:3]


def _metric_from_record(record: FinancialRecord, metric_name: str, prev: Optional[FinancialRecord],
                        year_ago: Optional[FinancialRecord]) -> Optional[float]:
    """One real metric value for one FinancialRecord, or None when the record
    does not carry enough data to compute it (never a filler 0)."""
    revenue = record.revenue
    if metric_name == "revenue":
        return float(revenue) if revenue is not None else None
    if metric_name == "cash_balance":
        return float(record.cash_balance) if record.cash_balance is not None else None
    if metric_name == "net_burn":
        return record_net_burn(record)
    if metric_name == "gross_margin":
        if not revenue or revenue <= 0 or record.cogs is None:
            return None
        return (revenue - record.cogs) / revenue * 100
    if metric_name == "runway":
        # Finite runway only; profitable/unknown cash has no point on the line.
        return burn_summary(record)["runway_months"]
    if metric_name == "revenue_growth_yoy":
        if year_ago is None or not year_ago.revenue or year_ago.revenue <= 0 or revenue is None:
            return None
        return (revenue - year_ago.revenue) / year_ago.revenue * 100
    if metric_name == "burn_multiple":
        if prev is None or prev.revenue is None or revenue is None:
            return None
        burn = record_net_burn(record)
        net_new_arr = (revenue - prev.revenue) * 12
        if burn is None or burn <= 0 or net_new_arr <= 0:
            return None
        return round(burn / net_new_arr, 2)
    return None


def get_real_history(financials: List[FinancialRecord], metric_name: str, months: int = 12) -> List[Dict[str, Any]]:
    """Sparkline points built from real FinancialRecord rows, oldest first.

    `financials` is ordered newest first. A record whose metric cannot be
    computed is skipped. Fewer than 2 points -> [] (no sparkline), so the UI
    never draws a trend that the data does not support.
    """
    by_period = {}
    for r in financials:
        if r.period_end is not None:
            by_period.setdefault(r.period_end.strftime("%Y-%m"), r)

    history: List[Dict[str, Any]] = []
    for idx in range(min(months, len(financials)) - 1, -1, -1):
        record = financials[idx]
        if record.period_end is None:
            continue
        prev = financials[idx + 1] if idx + 1 < len(financials) else None
        pe = record.period_end
        year_ago = by_period.get(f"{pe.year - 1:04d}-{pe.month:02d}")
        value = _metric_from_record(record, metric_name, prev, year_ago)
        if value is None:
            continue
        history.append({"date": pe.strftime("%Y-%m"), "value": value})
    return history if len(history) >= 2 else []


@router.get("/companies/{company_id}/kpis")
async def get_dashboard_kpis(
    company_id: int,
    period: Optional[TimePeriod] = Query(None, description="Time period filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard KPIs with historical data for sparklines.
    Returns current values, trends, benchmarks, recommendations, and validation info.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    from server.core.cache import cache_get, cache_set, cache_key
    period_str = period.value if period else "default"
    ck = cache_key("kpis", f"{company_id}:{current_user.id}:{period_str}")
    cached = cache_get(ck)
    if cached:
        return cached
    
    now = datetime.now()
    period_start = None
    period_end = now
    
    if period == TimePeriod.LAST_MONTH:
        period_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        period_end = now.replace(day=1) - timedelta(days=1)
    elif period == TimePeriod.THIS_QUARTER:
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        period_start = now.replace(month=quarter_month, day=1)
    elif period == TimePeriod.LAST_QUARTER:
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        period_start = (now.replace(month=quarter_month, day=1) - timedelta(days=1)).replace(day=1)
        period_start = period_start.replace(month=((period_start.month - 1) // 3) * 3 + 1, day=1)
        period_end = now.replace(month=quarter_month, day=1) - timedelta(days=1)
    elif period == TimePeriod.THIS_YEAR:
        period_start = now.replace(month=1, day=1)
    elif period == TimePeriod.LAST_12_MONTHS or period is None:
        period_start = now - timedelta(days=365)
    
    financials_query = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    )
    
    if period_start:
        financials_query = financials_query.filter(FinancialRecord.period_end >= period_start)
    if period_end:
        financials_query = financials_query.filter(FinancialRecord.period_end <= period_end)
    
    financials = financials_query.order_by(FinancialRecord.period_end.desc()).limit(24).all()
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    missing_data = []
    data_source_info = None
    
    if truth_scan and truth_scan.outputs_json:
        outputs = truth_scan.outputs_json
        metrics = outputs.get("metrics", {})
        
        runway_value = metrics.get("runway_p50") if isinstance(metrics.get("runway_p50"), (int, float)) else (metrics.get("runway_months", {}).get("value") if isinstance(metrics.get("runway_months"), dict) else None)
        net_burn_value = metrics.get("net_burn") if isinstance(metrics.get("net_burn"), (int, float)) else (metrics.get("net_burn", {}).get("value") if isinstance(metrics.get("net_burn"), dict) else None)
        raw_gm = metrics.get("gross_margin")
        if isinstance(raw_gm, (int, float)):
            gross_margin_value = raw_gm
        elif isinstance(raw_gm, dict):
            gross_margin_value = raw_gm.get("value")
        else:
            gross_margin_value = None
        if gross_margin_value is not None and 0 < gross_margin_value <= 1:
            gross_margin_value = gross_margin_value * 100
        revenue_growth_value = metrics.get("revenue_growth_yoy") if isinstance(metrics.get("revenue_growth_yoy"), (int, float)) else (metrics.get("revenue_growth_yoy", {}).get("value") if isinstance(metrics.get("revenue_growth_yoy"), dict) else None)
        burn_multiple_value = metrics.get("burn_multiple") if isinstance(metrics.get("burn_multiple"), (int, float)) else (metrics.get("burn_multiple", {}).get("value") if isinstance(metrics.get("burn_multiple"), dict) else None)
        mrr_value = metrics.get("monthly_revenue") if isinstance(metrics.get("monthly_revenue"), (int, float)) else (metrics.get("mrr", {}).get("value") if isinstance(metrics.get("mrr"), dict) else None)
        cash_value = metrics.get("cash_balance") if isinstance(metrics.get("cash_balance"), (int, float)) else (metrics.get("cash_balance", {}).get("value") if isinstance(metrics.get("cash_balance"), dict) else None)
        concentration_value = metrics.get("concentration_top5") if isinstance(metrics.get("concentration_top5"), (int, float)) else None
        
        data_confidence = outputs.get("data_confidence_score") or outputs.get("overall_score") or 0
        validation = metrics.get("data_validation", {})
        missing_data = validation.get("missing_data", [])
        
        data_source_info = {
            "last_updated": truth_scan.created_at.isoformat() if truth_scan.created_at else None,
            "source": "Truth Scan Analysis"
        }
    else:
        runway_value = None
        net_burn_value = None
        gross_margin_value = None
        revenue_growth_value = None
        burn_multiple_value = None
        mrr_value = None
        cash_value = None
        concentration_value = None
        data_confidence = 0
        missing_data = [{"field": "all", "message": "No financial data uploaded. Please upload your P&L or financial statements."}]
    
    # Burn/runway from the latest record via the shared rule, so this page agrees
    # with alerts, KPI board and copilot. Profitable -> runway null + status.
    runway_status = None
    if financials:
        burn = burn_summary(financials[0])
        if burn["net_burn"] is not None:
            net_burn_value = burn["net_burn"]
            runway_value = burn["runway_months"]
            runway_status = burn["runway_status"]
            if burn["is_profitable"]:
                burn_multiple_value = None
    elif net_burn_value is not None and net_burn_value <= 0:
        runway_value = None
        runway_status = "profitable"

    # Every sparkline comes from real FinancialRecord rows by period; with
    # fewer than 2 computable points the history is [] and no line is drawn.
    revenue_history = get_real_history(financials, "revenue", 12)
    cash_history = get_real_history(financials, "cash_balance", 12)
    net_burn_history = get_real_history(financials, "net_burn", 12)
    gross_margin_history = get_real_history(financials, "gross_margin", 12)
    runway_history = get_real_history(financials, "runway", 12)
    revenue_growth_history = get_real_history(financials, "revenue_growth_yoy", 12)
    burn_multiple_history = get_real_history(financials, "burn_multiple", 12)
    mrr_history = revenue_history
    
    kpis = {
        "dataConfidence": data_confidence,
        "qualityOfGrowthIndex": outputs.get("quality_of_growth_index", 0) if truth_scan else 0,
        "topConcentration": concentration_value if concentration_value is not None else 35,
        "runway": {
            "metricName": "runway",
            "currentValue": runway_value,
            "previousValue": runway_history[-2]["value"] if len(runway_history) > 1 else None,
            "changePercent": calculate_change_percent(runway_value, runway_history[-2]["value"]) if len(runway_history) > 1 else None,
            "trend": determine_trend(runway_value, runway_history[-2]["value"]) if len(runway_history) > 1 else "stable",
            "history": runway_history,
            "benchmark": 18,
            "benchmarkLabel": "Target runway",
            "status": determine_status("runway", runway_value),
            "runwayStatus": runway_status,
            "isProfitable": runway_status == "profitable",
        },
        "netBurn": {
            "metricName": "netBurn",
            "currentValue": net_burn_value,
            "previousValue": net_burn_history[-2]["value"] if len(net_burn_history) > 1 else None,
            "changePercent": calculate_change_percent(net_burn_value, net_burn_history[-2]["value"]) if len(net_burn_history) > 1 else None,
            "trend": determine_trend(net_burn_value, net_burn_history[-2]["value"]) if len(net_burn_history) > 1 else "stable",
            "history": net_burn_history,
            "benchmark": None,
            "status": "healthy"
        },
        "grossMargin": {
            "metricName": "grossMargin",
            "currentValue": gross_margin_value,
            "previousValue": gross_margin_history[-2]["value"] if len(gross_margin_history) > 1 else None,
            "changePercent": calculate_change_percent(gross_margin_value, gross_margin_history[-2]["value"]) if len(gross_margin_history) > 1 else None,
            "trend": determine_trend(gross_margin_value, gross_margin_history[-2]["value"]) if len(gross_margin_history) > 1 else "stable",
            "history": gross_margin_history,
            "benchmark": 70,
            "benchmarkLabel": "SaaS benchmark",
            "status": determine_status("grossMargin", gross_margin_value)
        },
        "revenueGrowth": {
            "metricName": "revenueGrowth",
            "currentValue": revenue_growth_value,
            "previousValue": revenue_growth_history[-2]["value"] if len(revenue_growth_history) > 1 else None,
            "changePercent": calculate_change_percent(revenue_growth_value, revenue_growth_history[-2]["value"]) if len(revenue_growth_history) > 1 else None,
            "trend": determine_trend(revenue_growth_value, revenue_growth_history[-2]["value"]) if len(revenue_growth_history) > 1 else "stable",
            "history": revenue_growth_history,
            "benchmark": 100,
            "benchmarkLabel": "T2D3 target",
            "status": "healthy"
        },
        "burnMultiple": {
            "metricName": "burnMultiple",
            "currentValue": burn_multiple_value,
            "previousValue": burn_multiple_history[-2]["value"] if len(burn_multiple_history) > 1 else None,
            "changePercent": calculate_change_percent(burn_multiple_value, burn_multiple_history[-2]["value"]) if len(burn_multiple_history) > 1 else None,
            "trend": determine_trend(burn_multiple_value, burn_multiple_history[-2]["value"]) if len(burn_multiple_history) > 1 else "stable",
            "history": burn_multiple_history,
            "benchmark": 1.5,
            "benchmarkLabel": "Efficient growth",
            "status": determine_status("burnMultiple", burn_multiple_value)
        },
        "mrr": {
            "metricName": "mrr",
            "currentValue": mrr_value,
            "previousValue": mrr_history[-2]["value"] if len(mrr_history) > 1 else None,
            "changePercent": calculate_change_percent(mrr_value, mrr_history[-2]["value"]) if len(mrr_history) > 1 else None,
            "trend": determine_trend(mrr_value, mrr_history[-2]["value"]) if len(mrr_history) > 1 else "stable",
            "history": mrr_history,
            "benchmark": None,
            "status": "healthy"
        },
        "cashOnHand": {
            "metricName": "cashOnHand",
            "currentValue": cash_value,
            "previousValue": cash_history[-2]["value"] if len(cash_history) > 1 else None,
            "changePercent": calculate_change_percent(cash_value, cash_history[-2]["value"]) if len(cash_history) > 1 else None,
            "trend": determine_trend(cash_value, cash_history[-2]["value"]) if len(cash_history) > 1 else "stable",
            "history": cash_history,
            "benchmark": None,
            "status": "healthy" if cash_value and cash_value > 0 else "missing"
        }
    }
    
    for metric_key in ["runway", "netBurn", "grossMargin", "revenueGrowth", "burnMultiple"]:
        if metric_key in kpis:
            definition_key = {
                "runway": "runway",
                "netBurn": "net_burn",
                "grossMargin": "gross_margin",
                "revenueGrowth": "revenue_growth_yoy",
                "burnMultiple": "burn_multiple"
            }.get(metric_key)
            if definition_key and definition_key in METRIC_DEFINITIONS:
                kpis[metric_key]["definition"] = METRIC_DEFINITIONS[definition_key]
    
    for metric_key in ["runway", "netBurn", "grossMargin", "revenueGrowth", "burnMultiple", "mrr", "cashOnHand"]:
        if metric_key in kpis and kpis[metric_key].get("currentValue") is None:
            kpis[metric_key]["status"] = "missing"
    
    kpis["recommendations"] = generate_recommendations(kpis)
    kpis["missingData"] = missing_data
    kpis["dataSource"] = data_source_info
    kpis["topConcentration"] = concentration_value
    kpis["metricDefinitions"] = METRIC_DEFINITIONS
    kpis["period"] = period.value if period else "last_12_months"
    
    cache_set(ck, kpis, ttl=180)
    return kpis
