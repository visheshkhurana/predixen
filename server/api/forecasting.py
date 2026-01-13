"""
API endpoints for forecasting and time-series predictions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from server.core.db import get_db
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.forecasting import (
    create_forecast,
    forecast_revenue,
    detect_trend,
    ForecastConfig,
    SeasonalityType,
)
from server.forecasting.models import ForecastMethod

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


class ForecastRequest(BaseModel):
    metric: str = "revenue"
    horizon_months: int = 12
    method: str = "holt_winters"
    seasonality: str = "monthly"
    confidence_level: float = 0.9


class TrendRequest(BaseModel):
    values: List[float]


@router.post("/companies/{company_id}/forecast")
def create_company_forecast(
    company_id: int,
    request: ForecastRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a forecast for a company metric.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get historical financial data
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start)
        .all()
    )
    
    if len(records) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 months of data for forecasting"
        )
    
    # Extract values based on metric
    metric_map = {
        "revenue": lambda r: r.revenue or 0,
        "mrr": lambda r: (r.revenue or 0) / 12,
        "gross_profit": lambda r: r.gross_profit or 0,
        "cash": lambda r: r.cash_balance or 0,
        "burn": lambda r: r.net_burn or 0,
    }
    
    if request.metric not in metric_map:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {request.metric}")
    
    values = [metric_map[request.metric](r) for r in records]
    
    # Build config
    method_map = {
        "linear": ForecastMethod.LINEAR,
        "exponential": ForecastMethod.EXPONENTIAL,
        "holt_winters": ForecastMethod.HOLT_WINTERS,
    }
    seasonality_map = {
        "none": SeasonalityType.NONE,
        "monthly": SeasonalityType.MONTHLY,
        "quarterly": SeasonalityType.QUARTERLY,
    }
    
    config = ForecastConfig(
        method=method_map.get(request.method, ForecastMethod.HOLT_WINTERS),
        horizon_months=request.horizon_months,
        seasonality=seasonality_map.get(request.seasonality, SeasonalityType.MONTHLY),
        confidence_level=request.confidence_level,
    )
    
    # Get start date from first record
    start_date = records[0].period_start if records else datetime.utcnow()
    
    try:
        result = create_forecast(values, request.metric, config, start_date)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies/{company_id}/trend")
def analyze_company_trend(
    company_id: int,
    metric: str = "revenue",
    db: Session = Depends(get_db),
):
    """
    Analyze trend for a company metric.
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
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 months of data for trend analysis"
        )
    
    values = [float(r.revenue or 0) for r in records]
    trend = detect_trend(values)
    
    return {
        "direction": trend.direction,
        "strength": trend.strength,
        "growth_rate": trend.growth_rate,
        "acceleration": trend.acceleration,
        "inflection_points": trend.inflection_points,
    }


@router.post("/trend/analyze")
def analyze_trend(request: TrendRequest):
    """
    Analyze trend for arbitrary values.
    """
    if len(request.values) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 values for trend analysis"
        )
    
    trend = detect_trend(request.values)
    
    return {
        "direction": trend.direction,
        "strength": trend.strength,
        "growth_rate": trend.growth_rate,
        "acceleration": trend.acceleration,
        "inflection_points": trend.inflection_points,
    }
