"""
API endpoints for alerts and anomaly detection.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from server.core.db import get_db
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.alerts import (
    detect_anomalies,
    check_thresholds,
    analyze_driver_health,
    AlertConfig,
)
from server.alerts.models import AlertThreshold
from server.alerts.detector import check_runway_warning, check_covenant_violations

router = APIRouter(prefix="/alerts", tags=["alerts"])


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
):
    """
    Get all active alerts for a company.
    Checks for anomalies, threshold breaches, and runway warnings.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
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
    
    # Extract metrics
    revenue_values = [float(r.revenue or 0) for r in records]
    burn_values = [float(r.net_burn or 0) for r in records]
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
        cash = float(latest.cash_balance) if latest.cash_balance else 0.0
        burn = float(latest.net_burn) if latest.net_burn else 0.0
        runway_alert = check_runway_warning(cash, burn, company_id)
        if runway_alert:
            all_alerts.append(runway_alert)
    
    return {
        "alerts": [a.to_dict() for a in all_alerts],
        "health": health_status,
        "total_alerts": len(all_alerts),
        "critical_count": sum(1 for a in all_alerts if a.severity.value == "critical"),
        "warning_count": sum(1 for a in all_alerts if a.severity.value == "warning"),
    }


@router.post("/companies/{company_id}/analyze")
def analyze_company_health(
    company_id: int,
    config: Optional[AlertConfigRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Comprehensive health analysis for a company.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start)
        .all()
    )
    
    if len(records) < 2:
        return {
            "status": "insufficient_data",
            "message": "Need at least 2 months of data for analysis",
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
    
    # Analyze each driver
    drivers = {}
    metrics = {
        "revenue": [float(r.revenue) if r.revenue else 0.0 for r in records],
        "burn_rate": [float(r.net_burn) if r.net_burn else 0.0 for r in records],
        "cash": [float(r.cash_balance) if r.cash_balance else 0.0 for r in records],
        "gross_margin": [
            (float(r.revenue or 0) - float(r.cogs or 0)) / max(float(r.revenue or 1), 1.0)
            for r in records
        ],
    }
    
    for name, values in metrics.items():
        if len(values) >= 2:
            health = analyze_driver_health(name, values, company_id, alert_config)
            drivers[name] = health.to_dict()
    
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
