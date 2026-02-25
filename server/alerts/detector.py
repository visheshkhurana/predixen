"""
Anomaly detection and threshold monitoring for financial drivers.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from server.lib.lazy_imports import np
from .models import (
    Alert,
    AlertType,
    AlertSeverity,
    AlertConfig,
    AlertThreshold,
    DriverHealth,
)


def detect_anomalies(
    metric_name: str,
    values: List[float],
    company_id: int,
    sensitivity: float = 2.0,
) -> List[Alert]:
    """
    Detect statistical anomalies in a time series.
    Uses Z-score method to identify outliers.
    
    Args:
        metric_name: Name of the metric
        values: Historical values (most recent last)
        company_id: Company ID for alert
        sensitivity: Number of standard deviations for anomaly threshold
        
    Returns:
        List of alerts for detected anomalies
    """
    if len(values) < 4:
        return []
    
    alerts = []
    arr = np.array(values)
    
    # Calculate rolling statistics (exclude last point)
    historical = arr[:-1]
    current = arr[-1]
    
    mean = np.mean(historical)
    std = np.std(historical)
    
    if std > 0:
        z_score = (current - mean) / std
    else:
        z_score = 0
    
    # Check for anomaly
    if abs(z_score) > sensitivity:
        direction = "spike" if z_score > 0 else "drop"
        severity = AlertSeverity.CRITICAL if abs(z_score) > sensitivity * 1.5 else AlertSeverity.WARNING
        
        alerts.append(Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            type=AlertType.ANOMALY_DETECTED,
            severity=severity,
            metric=metric_name,
            message=f"Unusual {direction} detected in {metric_name}",
            details={
                "current_value": float(current),
                "historical_mean": float(mean),
                "historical_std": float(std),
                "z_score": float(z_score),
                "direction": direction,
            },
        ))
    
    # Check for trend change
    if len(values) >= 6:
        recent_trend = np.mean(arr[-3:]) - np.mean(arr[-6:-3])
        older_trend = np.mean(arr[-6:-3]) - np.mean(arr[-9:-6]) if len(arr) >= 9 else 0
        
        if older_trend != 0 and recent_trend * older_trend < 0:
            alerts.append(Alert(
                id=str(uuid.uuid4()),
                company_id=company_id,
                type=AlertType.TREND_CHANGE,
                severity=AlertSeverity.INFO,
                metric=metric_name,
                message=f"Trend reversal detected in {metric_name}",
                details={
                    "old_trend": "up" if older_trend > 0 else "down",
                    "new_trend": "up" if recent_trend > 0 else "down",
                },
            ))
    
    return alerts


def check_thresholds(
    metrics: Dict[str, float],
    thresholds: List[AlertThreshold],
    company_id: int,
    historical: Optional[Dict[str, List[float]]] = None,
) -> List[Alert]:
    """
    Check metrics against defined thresholds.
    
    Args:
        metrics: Current metric values
        thresholds: List of threshold definitions
        company_id: Company ID for alerts
        historical: Optional historical values for percentage change checks
        
    Returns:
        List of threshold breach alerts
    """
    alerts = []
    
    for threshold in thresholds:
        if threshold.metric not in metrics:
            continue
        
        value = metrics[threshold.metric]
        
        # Check min threshold
        if threshold.min_value is not None and value < threshold.min_value:
            alerts.append(Alert(
                id=str(uuid.uuid4()),
                company_id=company_id,
                type=AlertType.THRESHOLD_BREACH,
                severity=AlertSeverity.WARNING,
                metric=threshold.metric,
                message=f"{threshold.metric} below minimum threshold",
                details={
                    "current_value": value,
                    "threshold": threshold.min_value,
                    "type": "below_min",
                },
            ))
        
        # Check max threshold
        if threshold.max_value is not None and value > threshold.max_value:
            alerts.append(Alert(
                id=str(uuid.uuid4()),
                company_id=company_id,
                type=AlertType.THRESHOLD_BREACH,
                severity=AlertSeverity.WARNING,
                metric=threshold.metric,
                message=f"{threshold.metric} exceeds maximum threshold",
                details={
                    "current_value": value,
                    "threshold": threshold.max_value,
                    "type": "above_max",
                },
            ))
        
        # Check percentage change
        if threshold.percentage_change is not None and historical:
            if threshold.metric in historical:
                hist_values = historical[threshold.metric]
                lookback = min(threshold.lookback_months, len(hist_values))
                if lookback > 0:
                    baseline = np.mean(hist_values[-lookback:])
                    if baseline > 0:
                        pct_change = ((value - baseline) / baseline) * 100
                        if abs(pct_change) > threshold.percentage_change:
                            alerts.append(Alert(
                                id=str(uuid.uuid4()),
                                company_id=company_id,
                                type=AlertType.THRESHOLD_BREACH,
                                severity=AlertSeverity.WARNING,
                                metric=threshold.metric,
                                message=f"{threshold.metric} changed by {pct_change:.1f}%",
                                details={
                                    "current_value": value,
                                    "baseline": float(baseline),
                                    "percentage_change": float(pct_change),
                                    "threshold": threshold.percentage_change,
                                },
                            ))
    
    return alerts


def check_runway_warning(
    cash: float,
    monthly_burn: float,
    company_id: int,
    warning_months: int = 6,
    critical_months: int = 3,
) -> Optional[Alert]:
    """
    Check if runway is below warning thresholds.
    """
    if monthly_burn <= 0:
        return None
    
    runway_months = cash / monthly_burn
    
    if runway_months < critical_months:
        return Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            type=AlertType.RUNWAY_WARNING,
            severity=AlertSeverity.CRITICAL,
            metric="runway",
            message=f"Critical: Only {runway_months:.1f} months of runway remaining",
            details={
                "runway_months": runway_months,
                "cash": cash,
                "monthly_burn": monthly_burn,
            },
        )
    elif runway_months < warning_months:
        return Alert(
            id=str(uuid.uuid4()),
            company_id=company_id,
            type=AlertType.RUNWAY_WARNING,
            severity=AlertSeverity.WARNING,
            metric="runway",
            message=f"Warning: {runway_months:.1f} months of runway remaining",
            details={
                "runway_months": runway_months,
                "cash": cash,
                "monthly_burn": monthly_burn,
            },
        )
    
    return None


def check_covenant_violations(
    covenants: Dict[str, float],
    actuals: Dict[str, float],
    company_id: int,
) -> List[Alert]:
    """
    Check for debt covenant violations.
    """
    alerts = []
    
    covenant_checks = {
        "min_cash": lambda c, a: a.get("cash", 0) >= c,
        "max_leverage": lambda c, a: (a.get("debt", 0) / max(a.get("arr", 1), 1)) <= c,
        "min_revenue_growth": lambda c, a: a.get("revenue_growth", 0) >= c,
        "min_gross_margin": lambda c, a: a.get("gross_margin", 0) >= c,
    }
    
    for covenant_name, threshold in covenants.items():
        if covenant_name in covenant_checks:
            check_fn = covenant_checks[covenant_name]
            if not check_fn(threshold, actuals):
                alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    company_id=company_id,
                    type=AlertType.COVENANT_VIOLATION,
                    severity=AlertSeverity.CRITICAL,
                    metric=covenant_name,
                    message=f"Covenant violation: {covenant_name}",
                    details={
                        "covenant": covenant_name,
                        "threshold": threshold,
                        "actual": actuals.get(covenant_name.replace("min_", "").replace("max_", ""), None),
                    },
                ))
    
    return alerts


def analyze_driver_health(
    driver_name: str,
    values: List[float],
    company_id: int,
    config: Optional[AlertConfig] = None,
) -> DriverHealth:
    """
    Comprehensive health analysis for a single driver.
    """
    if config is None:
        config = AlertConfig()
    
    if len(values) < 2:
        return DriverHealth(
            metric=driver_name,
            status="unknown",
            current_value=values[-1] if values else 0,
            historical_mean=values[-1] if values else 0,
            historical_std=0,
            z_score=0,
            trend_direction="flat",
            alerts=[],
        )
    
    arr = np.array(values)
    current = arr[-1]
    historical = arr[:-1]
    
    mean = float(np.mean(historical))
    std = float(np.std(historical))
    z_score = float((current - mean) / std) if std > 0 else 0
    
    # Determine trend
    if len(arr) >= 3:
        recent_change = arr[-1] - arr[-2]
        if abs(recent_change) < 0.01 * mean:
            trend_direction = "flat"
        elif recent_change > 0:
            trend_direction = "up"
        else:
            trend_direction = "down"
    else:
        trend_direction = "flat"
    
    # Determine status
    if abs(z_score) > config.anomaly_sensitivity * 1.5:
        status = "critical"
    elif abs(z_score) > config.anomaly_sensitivity:
        status = "warning"
    else:
        status = "healthy"
    
    # Collect alerts
    alerts = detect_anomalies(driver_name, values, company_id, config.anomaly_sensitivity)
    
    return DriverHealth(
        metric=driver_name,
        status=status,
        current_value=float(current),
        historical_mean=mean,
        historical_std=std,
        z_score=z_score,
        trend_direction=trend_direction,
        alerts=alerts,
    )
