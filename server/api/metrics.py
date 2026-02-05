"""
API endpoints for metrics management and computation.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.metrics import MetricEngine

router = APIRouter(prefix="/metrics", tags=["metrics"])


class CreateMetricRequest(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    formula: str
    source_connector: Optional[str] = None
    grain: str = "monthly"
    unit: Optional[str] = None
    format_type: str = "number"
    config: Optional[Dict[str, Any]] = None


class UpdateMetricRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    formula: Optional[str] = None
    source_connector: Optional[str] = None
    grain: Optional[str] = None
    unit: Optional[str] = None
    format_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


@router.get("")
async def list_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all metric definitions for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metrics = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id
    ).order_by(MetricDefinition.name).all()
    
    return [m.to_dict() for m in metrics]


@router.post("")
async def create_metric(
    company_id: int,
    request: CreateMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new metric definition."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    existing = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id,
        MetricDefinition.key == request.key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Metric key already exists")
    
    metric = MetricDefinition(
        company_id=company_id,
        key=request.key,
        name=request.name,
        description=request.description,
        formula=request.formula,
        source_connector=request.source_connector,
        grain=request.grain,
        unit=request.unit,
        format_type=request.format_type,
        config=request.config,
    )
    db.add(metric)
    db.commit()
    
    return metric.to_dict()


@router.get("/{metric_key}/latest")
async def get_metric_latest(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest value for a metric."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    engine = MetricEngine(db)
    result = engine.get_metric_latest(company_id, metric_key)
    
    if not result:
        raise HTTPException(status_code=404, detail="Metric not found or no data available")
    
    return result


@router.get("/{metric_key}/timeseries")
async def get_metric_timeseries(
    metric_key: str,
    company_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical values for a metric."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    engine = MetricEngine(db)
    results = engine.get_metric_timeseries(
        company_id, metric_key, 
        start_date=start, end_date=end, limit=limit
    )
    
    return {"metric_key": metric_key, "data": results}


@router.put("/{metric_key}")
async def update_metric(
    metric_key: str,
    company_id: int,
    request: UpdateMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a metric definition."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metric = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id,
        MetricDefinition.key == metric_key
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system metrics")
    
    if request.name is not None:
        metric.name = request.name
    if request.description is not None:
        metric.description = request.description
    if request.formula is not None:
        metric.formula = request.formula
    if request.source_connector is not None:
        metric.source_connector = request.source_connector
    if request.grain is not None:
        metric.grain = request.grain
    if request.unit is not None:
        metric.unit = request.unit
    if request.format_type is not None:
        metric.format_type = request.format_type
    if request.config is not None:
        metric.config = request.config
    
    db.commit()
    return metric.to_dict()


@router.delete("/{metric_key}")
async def delete_metric(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a metric definition."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metric = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id,
        MetricDefinition.key == metric_key
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system metrics")
    
    db.query(MetricValue).filter(MetricValue.metric_id == metric.id).delete()
    db.delete(metric)
    db.commit()
    
    return {"success": True}


@router.post("/recompute")
async def recompute_metrics(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recompute all metrics for a company.
    This is idempotent and safe to re-run.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    engine = MetricEngine(db)
    results = engine.recompute_all_metrics(company_id)
    
    return results


@router.post("/initialize")
async def initialize_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize system metrics for a company.
    Creates default metric definitions if they don't exist.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    engine = MetricEngine(db)
    created = engine.create_system_metrics(company_id)
    
    return {
        "success": True,
        "created_count": len(created),
        "metrics": [m.to_dict() for m in created]
    }
