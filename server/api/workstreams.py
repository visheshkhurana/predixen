"""Workstreams API for operating cadence management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.company_source import CompanyWorkstream, CompanyAlert
from server.models.truth_scan import TruthScan
import uuid

router = APIRouter(tags=["workstreams"])


DEFAULT_WORKSTREAMS = [
    {
        "name": "Weekly Metrics Review",
        "cadence": "weekly",
        "config": {
            "kpis": ["revenue", "burn", "runway", "growth"],
            "day_of_week": "monday"
        }
    },
    {
        "name": "Monthly Board Memo",
        "cadence": "monthly",
        "config": {
            "sections": ["financials", "kpis", "risks", "decisions"],
            "day_of_month": 1
        }
    },
    {
        "name": "Quarterly Strategy Refresh",
        "cadence": "quarterly",
        "config": {
            "focus": ["icp", "competitors", "pricing", "priorities"]
        }
    }
]


class WorkstreamCreate(BaseModel):
    name: str
    cadence: str
    enabled: bool = True
    config: Dict[str, Any] = {}


class WorkstreamUpdate(BaseModel):
    name: Optional[str] = None
    cadence: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/companies/{company_id}/workstreams")
def list_workstreams(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all workstreams for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    workstreams = db.query(CompanyWorkstream).filter(
        CompanyWorkstream.company_id == company_id
    ).all()
    
    return {"workstreams": [w.to_dict() for w in workstreams]}


@router.post("/companies/{company_id}/workstreams")
def create_workstream(
    company_id: int,
    data: WorkstreamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new workstream."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    workstream = CompanyWorkstream(
        company_id=company_id,
        name=data.name,
        cadence=data.cadence,
        enabled=data.enabled,
        config_json=data.config
    )
    db.add(workstream)
    db.commit()
    db.refresh(workstream)
    
    return workstream.to_dict()


@router.post("/companies/{company_id}/workstreams/defaults")
def create_default_workstreams(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create default workstream templates for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    created = []
    for template in DEFAULT_WORKSTREAMS:
        existing = db.query(CompanyWorkstream).filter(
            CompanyWorkstream.company_id == company_id,
            CompanyWorkstream.name == template["name"]
        ).first()
        
        if not existing:
            workstream = CompanyWorkstream(
                company_id=company_id,
                name=template["name"],
                cadence=template["cadence"],
                enabled=True,
                config_json=template["config"]
            )
            db.add(workstream)
            created.append(template["name"])
    
    db.commit()
    return {"created": created}


@router.patch("/companies/{company_id}/workstreams/{workstream_id}")
def update_workstream(
    company_id: int,
    workstream_id: str,
    data: WorkstreamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a workstream."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        ws_uuid = uuid.UUID(workstream_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workstream ID")
    
    workstream = db.query(CompanyWorkstream).filter(
        CompanyWorkstream.id == ws_uuid,
        CompanyWorkstream.company_id == company_id
    ).first()
    
    if not workstream:
        raise HTTPException(status_code=404, detail="Workstream not found")
    
    if data.name is not None:
        workstream.name = data.name
    if data.cadence is not None:
        workstream.cadence = data.cadence
    if data.enabled is not None:
        workstream.enabled = data.enabled
    if data.config is not None:
        workstream.config_json = data.config
    
    workstream.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workstream)
    
    return workstream.to_dict()


@router.get("/companies/{company_id}/alerts")
def list_alerts(
    company_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List alerts for a company, optionally filtered by status."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    query = db.query(CompanyAlert).filter(CompanyAlert.company_id == company_id)
    
    if status:
        query = query.filter(CompanyAlert.status == status)
    
    alerts = query.order_by(CompanyAlert.triggered_at.desc()).all()
    
    return {"alerts": [a.to_dict() for a in alerts]}


@router.post("/companies/{company_id}/alerts/evaluate")
def evaluate_alerts(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Evaluate alert rules and create new alerts if triggered."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        return {"evaluated": False, "reason": "No financial data available", "alerts_created": []}
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    alerts_created = []
    
    runway = metrics.get("runway_months")
    if runway is not None and runway < 9:
        existing = db.query(CompanyAlert).filter(
            CompanyAlert.company_id == company_id,
            CompanyAlert.type == "runway_drop",
            CompanyAlert.status == "open"
        ).first()
        
        if not existing:
            severity = "high" if runway < 6 else "medium"
            alert = CompanyAlert(
                company_id=company_id,
                type="runway_drop",
                severity=severity,
                message=f"Runway is at {runway:.1f} months, below the 9-month threshold",
                rule_json={"threshold_months": 9, "current": runway}
            )
            db.add(alert)
            alerts_created.append({
                "type": "runway_drop",
                "severity": severity,
                "message": alert.message
            })
    
    growth = metrics.get("revenue_growth_mom")
    prev_growth = metrics.get("prev_revenue_growth_mom")
    if growth is not None and growth < -10:
        existing = db.query(CompanyAlert).filter(
            CompanyAlert.company_id == company_id,
            CompanyAlert.type == "revenue_miss",
            CompanyAlert.status == "open"
        ).first()
        
        if not existing:
            alert = CompanyAlert(
                company_id=company_id,
                type="revenue_miss",
                severity="high",
                message=f"Revenue declined {abs(growth):.1f}% vs previous period",
                rule_json={"threshold_pct": -10, "current": growth}
            )
            db.add(alert)
            alerts_created.append({
                "type": "revenue_miss",
                "severity": "high",
                "message": alert.message
            })
    
    cac = metrics.get("cac")
    prev_cac = metrics.get("prev_cac")
    if cac is not None and prev_cac is not None and prev_cac > 0:
        cac_change = ((cac - prev_cac) / prev_cac) * 100
        if cac_change > 15:
            existing = db.query(CompanyAlert).filter(
                CompanyAlert.company_id == company_id,
                CompanyAlert.type == "cac_spike",
                CompanyAlert.status == "open"
            ).first()
            
            if not existing:
                alert = CompanyAlert(
                    company_id=company_id,
                    type="cac_spike",
                    severity="medium",
                    message=f"CAC increased {cac_change:.1f}% month-over-month",
                    rule_json={"threshold_pct": 15, "current_change": cac_change}
                )
                db.add(alert)
                alerts_created.append({
                    "type": "cac_spike",
                    "severity": "medium",
                    "message": alert.message
                })
    
    db.commit()
    
    return {
        "evaluated": True,
        "alerts_created": alerts_created,
        "total_open_alerts": db.query(CompanyAlert).filter(
            CompanyAlert.company_id == company_id,
            CompanyAlert.status == "open"
        ).count()
    }


@router.patch("/companies/{company_id}/alerts/{alert_id}")
def update_alert(
    company_id: int,
    alert_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update alert status (resolve, snooze)."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        a_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")
    
    alert = db.query(CompanyAlert).filter(
        CompanyAlert.id == a_uuid,
        CompanyAlert.company_id == company_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if status not in ["open", "resolved", "snoozed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    alert.status = status
    if status == "resolved":
        alert.resolved_at = datetime.utcnow()
    
    db.commit()
    return alert.to_dict()
