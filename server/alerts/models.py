"""
Alert data models for driver anomaly detection.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime


class AlertType(str, Enum):
    THRESHOLD_BREACH = "threshold_breach"
    ANOMALY_DETECTED = "anomaly_detected"
    TREND_CHANGE = "trend_change"
    COVENANT_VIOLATION = "covenant_violation"
    RUNWAY_WARNING = "runway_warning"
    GOAL_AT_RISK = "goal_at_risk"
    DATA_QUALITY = "data_quality"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertThreshold:
    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    percentage_change: Optional[float] = None
    lookback_months: int = 3


@dataclass
class AlertConfig:
    enabled: bool = True
    thresholds: List[AlertThreshold] = field(default_factory=list)
    anomaly_sensitivity: float = 2.0  # Standard deviations
    check_interval_hours: int = 24
    notification_channels: List[str] = field(default_factory=lambda: ["in_app"])


@dataclass
class Alert:
    id: str
    company_id: int
    type: AlertType
    severity: AlertSeverity
    metric: str
    message: str
    details: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        return self.resolved_at is None
    
    def acknowledge(self) -> None:
        self.acknowledged_at = datetime.utcnow()
    
    def resolve(self) -> None:
        self.resolved_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "type": self.type.value,
            "severity": self.severity.value,
            "metric": self.metric,
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_active": self.is_active,
        }


@dataclass
class DriverHealth:
    metric: str
    status: str  # "healthy", "warning", "critical"
    current_value: float
    historical_mean: float
    historical_std: float
    z_score: float
    trend_direction: str
    alerts: List[Alert] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "status": self.status,
            "current_value": self.current_value,
            "historical_mean": self.historical_mean,
            "z_score": self.z_score,
            "trend_direction": self.trend_direction,
            "alert_count": len(self.alerts),
        }
