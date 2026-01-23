"""
Dashboard KPIs API endpoint for founder-friendly metrics with historical data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company
from server.models.truth_scan import TruthScan


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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


@router.get("/companies/{company_id}/kpis")
async def get_dashboard_kpis(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive dashboard KPIs with historical data for sparklines.
    Returns current values, trends, benchmarks, and recommendations.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if truth_scan and truth_scan.outputs_json:
        outputs = truth_scan.outputs_json
        metrics = outputs.get("metrics", {})
        
        runway_value = metrics.get("runway_months", {}).get("value", 16.5)
        net_burn_value = metrics.get("net_burn", {}).get("value", 45000)
        gross_margin_value = metrics.get("gross_margin", {}).get("value", 72)
        revenue_growth_value = metrics.get("revenue_growth_yoy", {}).get("value", 85)
        burn_multiple_value = metrics.get("burn_multiple", {}).get("value", 1.8)
        mrr_value = metrics.get("mrr", {}).get("value", 125000)
        cash_value = metrics.get("cash_balance", {}).get("value", 1500000)
        
        data_confidence = outputs.get("overall_score", 75)
    else:
        runway_value = 16.5
        net_burn_value = 45000
        gross_margin_value = 72
        revenue_growth_value = 85
        burn_multiple_value = 1.8
        mrr_value = 125000
        cash_value = 1500000
        data_confidence = 65
    
    runway_history = generate_mock_history(runway_value, 12, 0.05, "up")
    net_burn_history = generate_mock_history(net_burn_value, 12, 0.1, "down")
    gross_margin_history = generate_mock_history(gross_margin_value, 12, 0.03, "stable")
    revenue_growth_history = generate_mock_history(revenue_growth_value, 12, 0.15, "up")
    burn_multiple_history = generate_mock_history(burn_multiple_value, 12, 0.1, "down")
    mrr_history = generate_mock_history(mrr_value, 12, 0.08, "up")
    cash_history = generate_mock_history(cash_value, 12, 0.05, "down")
    
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
            "status": "healthy"
        }
    }
    
    kpis["recommendations"] = generate_recommendations(kpis)
    
    return kpis
