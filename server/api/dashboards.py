"""
API endpoints for KPI dashboards and widgets.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.dashboard import Dashboard, DashboardWidget
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.metrics import MetricEngine

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


class CreateDashboardRequest(BaseModel):
    name: str
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None


class UpdateDashboardRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None


class CreateWidgetRequest(BaseModel):
    widget_type: str
    metric_key: Optional[str] = None
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position: Dict[str, Any]


class UpdateWidgetRequest(BaseModel):
    widget_type: Optional[str] = None
    metric_key: Optional[str] = None
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None


@router.get("")
async def list_dashboards(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all dashboards for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    dashboards = db.query(Dashboard).filter(
        Dashboard.company_id == company_id
    ).order_by(Dashboard.created_at.desc()).all()
    
    return [d.to_dict() for d in dashboards]


@router.post("")
async def create_dashboard(
    company_id: int,
    request: CreateDashboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new dashboard."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    dashboard = Dashboard(
        company_id=company_id,
        name=request.name,
        description=request.description,
        layout_config=request.layout_config or {"columns": 12, "rowHeight": 80},
    )
    db.add(dashboard)
    db.commit()
    
    return dashboard.to_dict()


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a dashboard with its widgets."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return dashboard.to_dict(include_widgets=True)


@router.put("/{dashboard_id}")
async def update_dashboard(
    dashboard_id: int,
    request: UpdateDashboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dashboard."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if request.name is not None:
        dashboard.name = request.name
    if request.description is not None:
        dashboard.description = request.description
    if request.layout_config is not None:
        dashboard.layout_config = request.layout_config
    
    db.commit()
    return dashboard.to_dict()


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dashboard."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(dashboard)
    db.commit()
    return {"success": True}


@router.post("/{dashboard_id}/widgets")
async def create_widget(
    dashboard_id: int,
    request: CreateWidgetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a widget to a dashboard."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=request.widget_type,
        metric_key=request.metric_key,
        title=request.title,
        config=request.config,
        position=request.position,
    )
    db.add(widget)
    db.commit()
    
    return widget.to_dict()


@router.get("/{dashboard_id}/widgets")
async def list_widgets(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all widgets in a dashboard."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    widgets = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard_id
    ).all()
    
    return [w.to_dict() for w in widgets]


@router.put("/widgets/{widget_id}")
async def update_widget(
    widget_id: int,
    request: UpdateWidgetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a widget."""
    widget = db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    dashboard = db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if request.widget_type is not None:
        widget.widget_type = request.widget_type
    if request.metric_key is not None:
        widget.metric_key = request.metric_key
    if request.title is not None:
        widget.title = request.title
    if request.config is not None:
        widget.config = request.config
    if request.position is not None:
        widget.position = request.position
    
    db.commit()
    return widget.to_dict()


@router.delete("/widgets/{widget_id}")
async def delete_widget(
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a widget."""
    widget = db.query(DashboardWidget).filter(DashboardWidget.id == widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    dashboard = db.query(Dashboard).filter(Dashboard.id == widget.dashboard_id).first()
    company = db.query(Company).filter(
        Company.id == dashboard.company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(widget)
    db.commit()
    return {"success": True}
