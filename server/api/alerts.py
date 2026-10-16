"""
API endpoints for alerts and anomaly detection.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.alerts import (
    detect_anomalies,
    check_thresholds,
    analyze_driver_health,
    AlertConfig,
)
from server.alerts.models import AlertThreshold
from server.core.burn import gross_burn
from server.alerts.detector import check_runway_warning, check_covenant_violations

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Runway sentinel for a company that is not burning cash; matches
# /metrics/computed (server/api/ingest.py) and the client's formatRunway (>= 900).
NOT_BURNING_RUNWAY = 999


class ThresholdConfig(BaseModel):
    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    percentage_change: Optional[float] = None
    lookback_months: int = 3


class AlertConfigRequest(BaseModel):
    thresholds: List[ThresholdConfig] = []
    anomaly_sensitivity: float = 2.0


class CovenantCheckRequest(BaseModel):
    covenants: Dict[str, float]
    actuals: Dict[str, float]


@router.get("/companies/{company_id}/alerts")
def get_company_alerts(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all active alerts for a company.
    Checks for anomalies, threshold breaches, and runway warnings.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get historical data
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start)
        .all()
    )
    
    if not records:
        return {"alerts": [], "health": {}}
    
    all_alerts = []
    health_status = {}
    
    # Extract metrics - calculate burn from available fields
    revenue_values = [float(r.revenue or 0) for r in records]
    # Calculate net burn as total costs minus revenue (negative means burn)
    burn_values = [gross_burn(r) - float(r.revenue or 0) for r in records]
    cash_values = [float(r.cash_balance or 0) for r in records]
    
    # Detect anomalies
    if len(revenue_values) >= 4:
        all_alerts.extend(detect_anomalies("revenue", revenue_values, company_id))
        health = analyze_driver_health("revenue", revenue_values, company_id)
        health_status["revenue"] = health.to_dict()
    
    if len(burn_values) >= 4:
        all_alerts.extend(detect_anomalies("burn_rate", burn_values, company_id))
        health = analyze_driver_health("burn_rate", burn_values, company_id)
        health_status["burn_rate"] = health.to_dict()
    
    # Check runway
    if len(records) > 0:
        latest = records[-1]
        burn = gross_burn(latest) - float(latest.revenue or 0)
        # No runway alert when profitable or when cash was never provided.
        if burn > 0 and latest.cash_balance is not None:
            runway_alert = check_runway_warning(float(latest.cash_balance), burn, company_id)
            if runway_alert:
                all_alerts.append(runway_alert)
    
    return {
        "alerts": [a.to_dict() for a in all_alerts],
        "health": health_status,
        "total_alerts": len(all_alerts),
        "critical_count": sum(1 for a in all_alerts if a.severity.value == "critical"),
        "warning_count": sum(1 for a in all_alerts if a.severity.value == "warning"),
    }


@router.get("/companies/{company_id}/analyze")
def get_company_health(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get health analysis for a company (simple GET endpoint).
    """
    return _perform_health_analysis(company_id, None, db, current_user)


@router.post("/companies/{company_id}/analyze")
def analyze_company_health(
    company_id: int,
    config: Optional[AlertConfigRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Comprehensive health analysis for a company with custom config.
    """
    return _perform_health_analysis(company_id, config, db, current_user)


def _perform_health_analysis(
    company_id: int,
    config: Optional[AlertConfigRequest],
    db: Session,
    current_user: User,
):
    """
    Shared implementation for health analysis.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start)
        .all()
    )
    
    if len(records) == 0:
        return {
            "overall_status": "unknown",
            "status": "unknown",
            "message": "No financial data available",
            "drivers": {},
            "recommendations": ["Add financial data through Data Input or connect a data source"],
        }
    
    # Even with 1 record, we can provide basic health metrics
    if len(records) == 1:
        record = records[0]
        # A cash balance nobody entered is unknown, not 0. Turning it into 0
        # made every runway test below false and the company "healthy".
        cash_known = record.cash_balance is not None
        cash = float(record.cash_balance) if cash_known else 0.0
        revenue = float(record.revenue or 0)
        total_costs = gross_burn(record)
        net_burn = total_costs - revenue
        # Not burning: report the same "sustainable" sentinel /metrics/computed
        # uses (999, rendered as "Sustainable"), never 0 months. Unknown cash
        # while still burning stays None rather than a fake runway.
        not_burning = net_burn <= 0
        runway = cash / net_burn if cash_known and net_burn > 0 else None
        runway_value = NOT_BURNING_RUNWAY if not_burning else runway
        gross_margin = (revenue - float(record.cogs or 0)) / max(revenue, 1) if revenue > 0 else 0

        # Determine status based on runway. Compare against None, not truthiness:
        # a real 0.0 (cash exhausted) is the most critical runway there is.
        if cash_known and runway is not None and runway < 6:
            overall = "critical"
        elif cash_known and runway is not None and runway < 12:
            overall = "warning"
        elif net_burn <= 0:
            overall = "healthy"
        elif not cash_known:
            overall = "unknown"
        else:
            overall = "warning" if runway is not None and runway < 18 else "healthy"
        
        drivers = {
            "runway_months": {
                "metric": "runway_months",
                "status": "critical" if runway is not None and runway < 6 else ("warning" if runway is not None and runway < 12 else ("unknown" if not cash_known and net_burn > 0 else "healthy")),
                "current_value": runway_value,
                "historical_mean": runway_value,
                "z_score": 0,
                "trend_direction": "flat",
                "alert_count": 1 if runway is not None and runway < 12 else 0,
                "history": [runway_value] if runway_value is not None else [],
            },
            "net_burn": {
                "metric": "net_burn",
                "status": "healthy" if net_burn <= 0 else ("critical" if net_burn > cash * 0.2 else "warning"),
                "current_value": net_burn,
                "historical_mean": net_burn,
                "z_score": 0,
                "trend_direction": "flat",
                "alert_count": 0,
                "history": [net_burn],
            },
            "gross_margin": {
                "metric": "gross_margin",
                "status": "healthy" if gross_margin >= 0.5 else ("warning" if gross_margin >= 0.3 else "critical"),
                "current_value": gross_margin,
                "historical_mean": gross_margin,
                "z_score": 0,
                "trend_direction": "flat",
                "alert_count": 0,
                "history": [gross_margin],
            },
        }
        
        recommendations = []
        if runway is not None and runway < 12:
            recommendations.append("Consider extending runway by reducing burn or raising capital")
        if not cash_known:
            recommendations.append("Add your cash balance so runway can be computed")
        if gross_margin < 0.5:
            recommendations.append("Focus on improving gross margin through pricing or COGS reduction")
        if not recommendations:
            recommendations.append("Add more historical data to enable trend analysis and anomaly detection")
        
        return {
            "overall_status": overall,
            "status": overall,
            "message": "Basic analysis available. Add more months of data for trend analysis.",
            "drivers": drivers,
            "recommendations": recommendations,
        }
    
    # Build alert config
    alert_config = AlertConfig(
        anomaly_sensitivity=config.anomaly_sensitivity if config else 2.0,
        thresholds=[
            AlertThreshold(
                metric=t.metric,
                min_value=t.min_value,
                max_value=t.max_value,
                percentage_change=t.percentage_change,
                lookback_months=t.lookback_months,
            )
            for t in (config.thresholds if config else [])
        ],
    )
    
    drivers = {}
    
    revenue_values = [float(r.revenue) if r.revenue else 0.0 for r in records]
    cash_values = [float(r.cash_balance) if r.cash_balance else 0.0 for r in records]
    gross_margin_values = [
        (float(r.revenue or 0) - float(r.cogs or 0)) / max(float(r.revenue or 1), 1.0)
        for r in records
    ]
    burn_values = []
    runway_values = []
    for r in records:
        rev = float(r.revenue or 0)
        total_costs = gross_burn(r)
        nb = total_costs - rev
        burn_values.append(nb)
        # Same split as the single-record branch above: known-ness is
        # `is not None`, and a real 0.0 (cash exhausted) is a runway of zero,
        # not a missing one.
        if nb > 0 and r.cash_balance is not None:
            runway_values.append(float(r.cash_balance) / nb)
        else:
            runway_values.append(None)
    
    raw_metrics = {
        "gross_margin": gross_margin_values,
        "net_burn": burn_values,
    }
    
    for name, values in raw_metrics.items():
        if len(values) >= 2:
            health = analyze_driver_health(name, values, company_id, alert_config)
            drivers[name] = health.to_dict()
    
    valid_runways = [v for v in runway_values if v is not None]
    if valid_runways:
        latest_runway = valid_runways[-1] if valid_runways else 0
        drivers["runway_months"] = {
            "metric": "runway_months",
            "status": "critical" if latest_runway < 6 else ("warning" if latest_runway < 12 else "healthy"),
            "current_value": latest_runway,
            "historical_mean": sum(valid_runways) / len(valid_runways),
            "z_score": 0,
            "trend_direction": "up" if len(valid_runways) >= 2 and valid_runways[-1] > valid_runways[-2] else ("down" if len(valid_runways) >= 2 and valid_runways[-1] < valid_runways[-2] else "flat"),
            "alert_count": 0,
            "history": valid_runways[-12:],
        }
    
    # Financial records carry no churned-customer counts, so there is no real
    # churn to report. Say so instead of a fixed "healthy" 3.2%.
    drivers["churn_rate"] = {
        "metric": "churn_rate",
        "status": "unknown",
        "current_value": None,
        "historical_mean": None,
        "z_score": 0,
        "trend_direction": "flat",
        "alert_count": 0,
        "history": [],
        "message": "Churn not available: no customer churn data imported",
    }
    
    # Overall status
    statuses = [d["status"] for d in drivers.values()]
    if "critical" in statuses:
        overall = "critical"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "healthy"
    
    return {
        "overall_status": overall,
        "drivers": drivers,
        "recommendations": _get_recommendations(drivers, overall),
    }


@router.post("/check/thresholds")
def check_metric_thresholds(
    metrics: Dict[str, float],
    thresholds: List[ThresholdConfig],
    company_id: int = 1,
):
    """
    Check metrics against custom thresholds.
    """
    threshold_objs = [
        AlertThreshold(
            metric=t.metric,
            min_value=t.min_value,
            max_value=t.max_value,
            percentage_change=t.percentage_change,
            lookback_months=t.lookback_months,
        )
        for t in thresholds
    ]
    
    alerts = check_thresholds(metrics, threshold_objs, company_id)
    return {"alerts": [a.to_dict() for a in alerts]}


@router.post("/check/covenants")
def check_debt_covenants(request: CovenantCheckRequest, company_id: int = 1):
    """
    Check for covenant violations.
    """
    alerts = check_covenant_violations(request.covenants, request.actuals, company_id)
    return {
        "alerts": [a.to_dict() for a in alerts],
        "violations": len(alerts),
        "in_compliance": len(alerts) == 0,
    }


def _get_recommendations(drivers: Dict[str, Any], overall: str) -> List[str]:
    """Generate recommendations based on driver health."""
    recommendations = []
    
    for name, health in drivers.items():
        if health["status"] == "critical":
            if name == "revenue":
                recommendations.append(
                    "Revenue shows critical deviation. Review sales pipeline and customer churn immediately."
                )
            elif name == "burn_rate":
                recommendations.append(
                    "Burn rate is critically high. Consider cost reduction measures."
                )
            elif name == "cash":
                recommendations.append(
                    "Cash position is critical. Evaluate runway and consider fundraising options."
                )
        elif health["status"] == "warning":
            if name == "revenue":
                recommendations.append(
                    "Revenue trend warrants attention. Monitor closely over next 30 days."
                )
            elif name == "gross_margin":
                recommendations.append(
                    "Gross margin is compressing. Review COGS and pricing strategy."
                )
    
    if not recommendations:
        recommendations.append("All metrics are within healthy ranges. Continue monitoring.")
    
    return recommendations
