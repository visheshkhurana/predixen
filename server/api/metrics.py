"""
API endpoints for metrics management, DSL validation, and computation.
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
    formula: Optional[str] = None
    definition: Optional[str] = None
    source_connector: Optional[str] = None
    grain: str = "monthly"
    unit: Optional[str] = None
    format_type: str = "number"
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    owners: Optional[List[str]] = None


class UpdateMetricRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    formula: Optional[str] = None
    definition: Optional[str] = None
    source_connector: Optional[str] = None
    grain: Optional[str] = None
    unit: Optional[str] = None
    format_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    owners: Optional[List[str]] = None


class ValidateRequest(BaseModel):
    definition: str


class ComputeRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def _get_company_or_404(company_id: int, user: User, db: Session) -> Company:
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def _get_metric_or_404(company_id: int, metric_key: str, db: Session) -> MetricDefinition:
    metric = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id,
        MetricDefinition.key == metric_key
    ).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


@router.get("")
async def list_metrics(
    company_id: int,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all metric definitions for a company with optional filters."""
    _get_company_or_404(company_id, current_user, db)
    
    query = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id
    )
    
    if status:
        query = query.filter(MetricDefinition.status == status)
    
    metrics = query.order_by(MetricDefinition.name).all()
    
    if tag:
        metrics = [m for m in metrics if m.tags and tag in m.tags]
    
    result = []
    for m in metrics:
        last_computed = db.query(MetricValue).filter(
            MetricValue.metric_id == m.id
        ).order_by(MetricValue.computed_at.desc()).first()
        
        metric_dict = m.to_dict()
        metric_dict["last_computed_at"] = last_computed.computed_at.isoformat() if last_computed else None
        metric_dict["latest_value"] = last_computed.value if last_computed else None
        result.append(metric_dict)
    
    return result


@router.post("")
async def create_metric(
    company_id: int,
    request: CreateMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new metric definition."""
    _get_company_or_404(company_id, current_user, db)
    
    existing = db.query(MetricDefinition).filter(
        MetricDefinition.company_id == company_id,
        MetricDefinition.key == request.key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Metric key already exists")
    
    if request.definition:
        engine = MetricEngine(db)
        validation = engine.validate_definition(request.definition)
        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=validation)
    
    metric = MetricDefinition(
        company_id=company_id,
        key=request.key,
        name=request.name,
        description=request.description,
        formula=request.formula,
        definition=request.definition,
        source_connector=request.source_connector,
        grain=request.grain,
        unit=request.unit,
        format_type=request.format_type,
        config=request.config,
        tags=request.tags,
        owners=request.owners,
        status="draft",
        version=1,
    )
    db.add(metric)
    db.commit()
    
    return metric.to_dict()


@router.get("/{metric_key}")
async def get_metric(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single metric definition."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    result = metric.to_dict()
    
    last_value = db.query(MetricValue).filter(
        MetricValue.metric_id == metric.id
    ).order_by(MetricValue.period_start.desc()).first()
    
    if last_value:
        result["latest_value"] = last_value.value
        result["last_computed_at"] = last_value.computed_at.isoformat() if last_value.computed_at else None
    
    return result


@router.put("/{metric_key}")
async def update_metric(
    metric_key: str,
    company_id: int,
    request: UpdateMetricRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a metric definition."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system metrics")
    
    if request.definition is not None:
        engine = MetricEngine(db)
        validation = engine.validate_definition(request.definition)
        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=validation)
        metric.definition = request.definition
        metric.status = "draft"
    
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
    if request.tags is not None:
        metric.tags = request.tags
    if request.owners is not None:
        metric.owners = request.owners
    
    db.commit()
    return metric.to_dict()


@router.delete("/{metric_key}")
async def delete_metric(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a metric definition and its values."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system metrics")
    
    db.query(MetricValue).filter(MetricValue.metric_id == metric.id).delete()
    db.delete(metric)
    db.commit()
    
    return {"success": True}


@router.post("/{metric_key}/validate")
async def validate_metric(
    metric_key: str,
    company_id: int,
    request: Optional[ValidateRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate metric DSL definition."""
    _get_company_or_404(company_id, current_user, db)
    
    if request and request.definition:
        definition = request.definition
    else:
        metric = _get_metric_or_404(company_id, metric_key, db)
        if not metric.definition:
            return {
                "is_valid": True,
                "message": "Metric uses formula mode, no DSL to validate",
            }
        definition = metric.definition
    
    engine = MetricEngine(db)
    result = engine.validate_definition(definition)
    
    return result


@router.post("/{metric_key}/publish")
async def publish_metric(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a metric (increment version, mark as certified)."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot publish system metrics")
    
    if metric.definition:
        engine = MetricEngine(db)
        validation = engine.validate_definition(metric.definition)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Metric definition is invalid", "validation": validation}
            )
    
    metric.version += 1
    metric.status = "certified"
    metric.published_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "version": metric.version,
        "status": metric.status,
        "published_at": metric.published_at.isoformat(),
    }


@router.post("/{metric_key}/deprecate")
async def deprecate_metric(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deprecate a metric."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    if metric.is_system:
        raise HTTPException(status_code=400, detail="Cannot deprecate system metrics")
    
    metric.status = "deprecated"
    db.commit()
    
    return {"success": True, "status": metric.status}


@router.post("/{metric_key}/compute")
async def compute_metric(
    metric_key: str,
    company_id: int,
    request: Optional[ComputeRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually compute a metric for a date range."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    engine = MetricEngine(db)
    
    start_date = None
    end_date = None
    if request:
        if request.start_date:
            start_date = datetime.fromisoformat(request.start_date)
        if request.end_date:
            end_date = datetime.fromisoformat(request.end_date)
    
    try:
        result = engine.compute_metric(metric, start_date, end_date)
        return {
            "success": True,
            "metric_key": metric_key,
            "value": result.value,
            "period_start": result.period_start.isoformat(),
            "period_end": result.period_end.isoformat(),
            "computed_at": result.computed_at.isoformat() if result.computed_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{metric_key}/values")
async def get_metric_values(
    metric_key: str,
    company_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get computed values for a metric over time."""
    _get_company_or_404(company_id, current_user, db)
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    engine = MetricEngine(db)
    results = engine.get_metric_timeseries(company_id, metric_key, start, end, limit)
    
    return {"metric_key": metric_key, "data": results}


@router.get("/{metric_key}/latest")
async def get_metric_latest(
    metric_key: str,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest value for a metric."""
    _get_company_or_404(company_id, current_user, db)
    
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
    """Get historical values for a metric (alias for /values)."""
    _get_company_or_404(company_id, current_user, db)
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    engine = MetricEngine(db)
    results = engine.get_metric_timeseries(company_id, metric_key, start, end, limit)
    
    return {"metric_key": metric_key, "data": results}


@router.get("/{metric_key}/lineage")
async def get_metric_lineage(
    metric_key: str,
    company_id: int,
    time_bucket: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lineage information for a metric value."""
    _get_company_or_404(company_id, current_user, db)
    metric = _get_metric_or_404(company_id, metric_key, db)
    
    engine = MetricEngine(db)
    lineage = engine.get_metric_lineage(company_id, metric_key, time_bucket)
    
    if not lineage:
        return {
            "metric_key": metric_key,
            "message": "No computed values found for this metric",
        }
    
    result = {
        "metric_key": metric_key,
        "metric_version": metric.version,
        "definition_version": lineage.get("metric_version"),
        "status": metric.status,
        **lineage,
    }
    
    if current_user.role == "admin" and lineage.get("compiled_sql"):
        result["compiled_sql"] = lineage["compiled_sql"]
    
    return result


@router.post("/recompute")
async def recompute_metrics(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recompute all metrics for a company."""
    _get_company_or_404(company_id, current_user, db)
    
    engine = MetricEngine(db)
    results = engine.recompute_all_metrics(company_id)
    
    return results


@router.post("/initialize")
async def initialize_metrics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initialize system metrics for a company."""
    _get_company_or_404(company_id, current_user, db)
    
    engine = MetricEngine(db)
    created = engine.create_system_metrics(company_id)
    
    return {
        "success": True,
        "created_count": len(created),
        "metrics": [m.to_dict() for m in created]
    }
