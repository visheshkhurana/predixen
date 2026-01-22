"""Driver-based forecasting API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.company_source import CompanyDriverModel, DRIVER_TEMPLATES
from server.models.truth_scan import TruthScan
import uuid

router = APIRouter(tags=["driver-models"])


class DriverModelCreate(BaseModel):
    model_name: str
    template: str
    drivers: Dict[str, Any] = {}


class DriverModelUpdate(BaseModel):
    model_name: Optional[str] = None
    drivers: Optional[Dict[str, Any]] = None


@router.get("/companies/{company_id}/driver-models")
def list_driver_models(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all driver models for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    models = db.query(CompanyDriverModel).filter(
        CompanyDriverModel.company_id == company_id
    ).all()
    
    return {"driver_models": [m.to_dict() for m in models]}


@router.get("/companies/{company_id}/driver-models/templates")
def get_templates(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available driver model templates."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"templates": DRIVER_TEMPLATES}


@router.post("/companies/{company_id}/driver-models")
def create_driver_model(
    company_id: int,
    data: DriverModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new driver model."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if data.template not in DRIVER_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Invalid template: {data.template}")
    
    template = DRIVER_TEMPLATES[data.template]
    drivers = {}
    for key, spec in template["drivers"].items():
        drivers[key] = data.drivers.get(key, spec["default"])
    
    model = CompanyDriverModel(
        company_id=company_id,
        model_name=data.model_name,
        template=data.template,
        drivers_json=drivers
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    
    return model.to_dict()


@router.post("/companies/{company_id}/driver-models/{model_id}/run")
def run_driver_model(
    company_id: int,
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run a driver model forecast."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        m_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model ID")
    
    model = db.query(CompanyDriverModel).filter(
        CompanyDriverModel.id == m_uuid,
        CompanyDriverModel.company_id == company_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Driver model not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    metrics = {}
    if truth_scan:
        metrics = truth_scan.outputs_json.get("metrics", {})
    
    outputs, assumptions = run_forecast(
        model.template,
        model.drivers_json,
        metrics
    )
    
    model.outputs_json = outputs
    model.assumptions_json = assumptions
    model.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(model)
    
    return {
        "model": model.to_dict(),
        "forecast": outputs,
        "assumptions": assumptions
    }


def run_forecast(
    template: str,
    drivers: Dict[str, Any],
    current_metrics: Dict[str, Any]
) -> tuple:
    """Run a 12-month forecast based on driver model."""
    assumptions = []
    monthly_forecast = []
    
    cash_balance = current_metrics.get("cash_balance", 0)
    if cash_balance == 0:
        cash_balance = 500000
        assumptions.append("Assumed $500K starting cash (no data provided)")
    
    gross_margin = current_metrics.get("gross_margin", 70)
    if gross_margin == 0:
        gross_margin = 70
        assumptions.append("Assumed 70% gross margin (industry average)")
    
    opex = current_metrics.get("opex", 0)
    if opex == 0:
        opex = 50000
        assumptions.append("Assumed $50K monthly OpEx (no data provided)")
    
    if template == "saas":
        new_customers = drivers.get("new_customers_per_month", 10)
        arpa = drivers.get("arpa", 100)
        churn_pct = drivers.get("churn_pct", 3) / 100
        
        current_customers = current_metrics.get("customers", 100)
        if current_customers == 0:
            current_customers = 100
            assumptions.append("Assumed 100 starting customers (no data provided)")
        
        customers = current_customers
        
        for month in range(1, 13):
            churned = int(customers * churn_pct)
            customers = customers - churned + new_customers
            revenue = customers * arpa
            gross_profit = revenue * (gross_margin / 100)
            net_income = gross_profit - opex
            cash_balance += net_income
            
            monthly_forecast.append({
                "month": month,
                "customers": customers,
                "revenue": round(revenue, 2),
                "gross_profit": round(gross_profit, 2),
                "net_income": round(net_income, 2),
                "cash_balance": round(cash_balance, 2)
            })
    
    elif template == "marketplace":
        gmv = drivers.get("gmv", 100000)
        take_rate = drivers.get("take_rate", 15) / 100
        contribution_margin = drivers.get("contribution_margin_pct", 50) / 100
        
        gmv_growth = 0.05
        assumptions.append("Assumed 5% monthly GMV growth")
        
        for month in range(1, 13):
            revenue = gmv * take_rate
            gross_profit = revenue * contribution_margin
            net_income = gross_profit - opex
            cash_balance += net_income
            
            monthly_forecast.append({
                "month": month,
                "gmv": round(gmv, 2),
                "revenue": round(revenue, 2),
                "gross_profit": round(gross_profit, 2),
                "net_income": round(net_income, 2),
                "cash_balance": round(cash_balance, 2)
            })
            
            gmv *= (1 + gmv_growth)
    
    elif template == "services":
        headcount = drivers.get("billable_headcount", 10)
        utilization = drivers.get("utilization_pct", 75) / 100
        rate = drivers.get("blended_rate", 150)
        
        hours_per_month = 160
        
        for month in range(1, 13):
            billable_hours = headcount * hours_per_month * utilization
            revenue = billable_hours * rate
            gross_profit = revenue * (gross_margin / 100)
            net_income = gross_profit - opex
            cash_balance += net_income
            
            monthly_forecast.append({
                "month": month,
                "billable_hours": round(billable_hours, 0),
                "revenue": round(revenue, 2),
                "gross_profit": round(gross_profit, 2),
                "net_income": round(net_income, 2),
                "cash_balance": round(cash_balance, 2)
            })
    
    else:
        for month in range(1, 13):
            monthly_forecast.append({
                "month": month,
                "revenue": 0,
                "gross_profit": 0,
                "net_income": -opex,
                "cash_balance": round(cash_balance - (opex * month), 2)
            })
        assumptions.append("Unknown template - using baseline projection")
    
    runway_months = 0
    for entry in monthly_forecast:
        if entry["cash_balance"] > 0:
            runway_months = entry["month"]
        else:
            break
    
    outputs = {
        "monthly_forecast": monthly_forecast,
        "summary": {
            "final_revenue": monthly_forecast[-1]["revenue"] if monthly_forecast else 0,
            "final_cash": monthly_forecast[-1]["cash_balance"] if monthly_forecast else cash_balance,
            "runway_months": runway_months if runway_months < 12 else "12+",
            "total_revenue": sum(m["revenue"] for m in monthly_forecast)
        }
    }
    
    return outputs, assumptions


@router.patch("/companies/{company_id}/driver-models/{model_id}")
def update_driver_model(
    company_id: int,
    model_id: str,
    data: DriverModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a driver model."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        m_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model ID")
    
    model = db.query(CompanyDriverModel).filter(
        CompanyDriverModel.id == m_uuid,
        CompanyDriverModel.company_id == company_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Driver model not found")
    
    if data.model_name is not None:
        model.model_name = data.model_name
    if data.drivers is not None:
        model.drivers_json = data.drivers
    
    model.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(model)
    
    return model.to_dict()


@router.delete("/companies/{company_id}/driver-models/{model_id}")
def delete_driver_model(
    company_id: int,
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a driver model."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        m_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model ID")
    
    model = db.query(CompanyDriverModel).filter(
        CompanyDriverModel.id == m_uuid,
        CompanyDriverModel.company_id == company_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Driver model not found")
    
    db.delete(model)
    db.commit()
    
    return {"deleted": True}
