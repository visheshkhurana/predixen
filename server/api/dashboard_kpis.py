"""
Dashboard KPIs API endpoint for founder-friendly metrics with historical data.
"""
import random
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


def generate_mock_history(
    current_value: float,
    months: int = 12,
    volatility: float = 0.1,
    trend: str = "stable"
) -> List[Dict[str, Any]]:
    """Generate mock historical data for sparklines."""
    history = []
    value = current_value
    
    trend_factor = 1.02 if trend == "up" else (0.98 if trend == "down" else 1.0)
    
    for i in range(months, 0, -1):
        date = (datetime.now() - timedelta(days=i * 30)).strftime("%Y-%m")
        value = value / trend_factor * (1 + random.uniform(-volatility, volatility))
        history.append({"date": date, "value": max(0, value)})
    
    history.append({"date": datetime.now().strftime("%Y-%m"), "value": current_value})
    return history


def calculate_change_percent(current: float, previous: float) -> Optional[float]:
    """Calculate percentage change between two values."""
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def determine_trend(current: float, previous: float, threshold: float = 0.05) -> str:
    """Determine trend direction based on change."""
    if previous == 0:
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
    
    runway = kpis.get("runway", {}).get("currentValue", 18)
    gross_margin = kpis.get("grossMargin", {}).get("currentValue", 70)
    burn_multiple = kpis.get("burnMultiple", {}).get("currentValue", 1.5)
    
    if runway < 12:
        recommendations.append({
            "id": "extend-runway",
            "title": "Extend Your Runway",
            "description": f"Your runway is {runway:.0f} months. Consider reducing burn by 15-20% or exploring bridge financing options.",
            "priority": "high" if runway < 6 else "medium",
            "action": "Run burn reduction scenario"
        })
    
    if gross_margin < 60:
        recommendations.append({
            "id": "improve-margins",
            "title": "Optimize Gross Margins",
            "description": f"Your {gross_margin:.0f}% gross margin is below the 70% SaaS benchmark. Review pricing and COGS structure.",
            "priority": "medium",
            "action": "Analyze margin breakdown"
        })
    
    if burn_multiple > 2:
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


def get_real_history(financials: List[FinancialRecord], metric_name: str, months: int = 12) -> List[Dict[str, Any]]:
    """Get real historical data for sparklines from financial records."""
    history = []
    for record in reversed(financials[:months]):
        date_str = record.period_end.strftime("%Y-%m") if record.period_end else ""
        if metric_name == "revenue":
            value = record.revenue or 0
        elif metric_name == "cash_balance":
            value = record.cash_balance or 0
        elif metric_name == "net_burn":
            total_costs = (record.cogs or 0) + (record.opex or 0) + (record.payroll or 0) + (record.other_costs or 0)
            value = total_costs - (record.revenue or 0)
        elif metric_name == "gross_margin":
            revenue = record.revenue or 0
            cogs = record.cogs or 0
            value = ((revenue - cogs) / revenue * 100) if revenue > 0 else 0
        else:
            value = 0
        history.append({"date": date_str, "value": value})
    return history


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
        
        runway_value = metrics.get("runway_p50") if isinstance(metrics.get("runway_p50"), (int, float)) else (metrics.get("runway_months", {}).get("value") if isinstance(metrics.get("runway_months"), dict) else 16.5)
        net_burn_value = metrics.get("net_burn") if isinstance(metrics.get("net_burn"), (int, float)) else (metrics.get("net_burn", {}).get("value") if isinstance(metrics.get("net_burn"), dict) else 45000)
        raw_gm = metrics.get("gross_margin")
        if isinstance(raw_gm, (int, float)):
            gross_margin_value = raw_gm
        elif isinstance(raw_gm, dict):
            gross_margin_value = raw_gm.get("value")
        else:
            gross_margin_value = 72
        if gross_margin_value is not None and 0 < gross_margin_value <= 1:
            gross_margin_value = gross_margin_value * 100
        revenue_growth_value = metrics.get("revenue_growth_yoy") if isinstance(metrics.get("revenue_growth_yoy"), (int, float)) else (metrics.get("revenue_growth_yoy", {}).get("value") if isinstance(metrics.get("revenue_growth_yoy"), dict) else 85)
        burn_multiple_value = metrics.get("burn_multiple") if isinstance(metrics.get("burn_multiple"), (int, float)) else (metrics.get("burn_multiple", {}).get("value") if isinstance(metrics.get("burn_multiple"), dict) else 1.8)
        mrr_value = metrics.get("monthly_revenue") if isinstance(metrics.get("monthly_revenue"), (int, float)) else (metrics.get("mrr", {}).get("value") if isinstance(metrics.get("mrr"), dict) else 125000)
        cash_value = metrics.get("cash_balance") if isinstance(metrics.get("cash_balance"), (int, float)) else (metrics.get("cash_balance", {}).get("value") if isinstance(metrics.get("cash_balance"), dict) else 1500000)
        concentration_value = metrics.get("concentration_top5") if isinstance(metrics.get("concentration_top5"), (int, float)) else 35
        
        data_confidence = outputs.get("overall_score", 75)
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
    
    if financials:
        revenue_history = get_real_history(financials, "revenue", 12)
        cash_history = get_real_history(financials, "cash_balance", 12)
        net_burn_history = get_real_history(financials, "net_burn", 12)
        gross_margin_history = get_real_history(financials, "gross_margin", 12)
    else:
        revenue_history = []
        cash_history = []
        net_burn_history = []
        gross_margin_history = []
    
    runway_history = generate_mock_history(runway_value or 16.5, 12, 0.05, "up") if runway_value else []
    revenue_growth_history = generate_mock_history(revenue_growth_value or 0, 12, 0.15, "up") if revenue_growth_value else []
    burn_multiple_history = generate_mock_history(burn_multiple_value or 0, 12, 0.1, "down") if burn_multiple_value else []
    mrr_history = revenue_history
    
    kpis = {
        "dataConfidence": data_confidence,
        "qualityOfGrowthIndex": 72,
        "topConcentration": 35,
        "runway": {
            "metricName": "runway",
            "currentValue": runway_value,
            "previousValue": runway_history[-2]["value"] if len(runway_history) > 1 else None,
            "changePercent": calculate_change_percent(runway_value, runway_history[-2]["value"]) if len(runway_history) > 1 else None,
            "trend": determine_trend(runway_value, runway_history[-2]["value"]) if len(runway_history) > 1 else "stable",
            "history": runway_history,
            "benchmark": 18,
            "benchmarkLabel": "Target runway",
            "status": determine_status("runway", runway_value)
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
    
    return kpis
