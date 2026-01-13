"""
Forecasting data models for time-series predictions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class SeasonalityType(str, Enum):
    NONE = "none"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ForecastMethod(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    ARIMA = "arima"
    HOLT_WINTERS = "holt_winters"
    PROPHET_LIKE = "prophet_like"


@dataclass
class ForecastConfig:
    method: ForecastMethod = ForecastMethod.HOLT_WINTERS
    horizon_months: int = 12
    seasonality: SeasonalityType = SeasonalityType.MONTHLY
    confidence_level: float = 0.9
    include_trend: bool = True
    include_seasonality: bool = True
    growth_cap: Optional[float] = None
    floor: float = 0.0


@dataclass
class ForecastPoint:
    month: int
    date: datetime
    value: float
    lower_bound: float
    upper_bound: float
    trend: float
    seasonal: float
    residual: float


@dataclass
class TrendAnalysis:
    direction: str  # "up", "down", "flat"
    strength: float  # 0-1 scale
    growth_rate: float  # monthly growth rate
    acceleration: float  # change in growth rate
    inflection_points: List[int] = field(default_factory=list)


@dataclass
class ForecastResult:
    metric_name: str
    method: ForecastMethod
    config: ForecastConfig
    historical: List[ForecastPoint]
    forecast: List[ForecastPoint]
    trend_analysis: TrendAnalysis
    accuracy_metrics: Dict[str, float]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def mape(self) -> float:
        """Mean Absolute Percentage Error"""
        return self.accuracy_metrics.get("mape", 0.0)
    
    @property
    def rmse(self) -> float:
        """Root Mean Square Error"""
        return self.accuracy_metrics.get("rmse", 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "method": self.method.value,
            "historical": [
                {
                    "month": p.month,
                    "value": p.value,
                    "lower_bound": p.lower_bound,
                    "upper_bound": p.upper_bound,
                }
                for p in self.historical
            ],
            "forecast": [
                {
                    "month": p.month,
                    "value": p.value,
                    "lower_bound": p.lower_bound,
                    "upper_bound": p.upper_bound,
                }
                for p in self.forecast
            ],
            "trend": {
                "direction": self.trend_analysis.direction,
                "strength": self.trend_analysis.strength,
                "growth_rate": self.trend_analysis.growth_rate,
            },
            "accuracy": self.accuracy_metrics,
        }
