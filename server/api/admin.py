from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, UserRole, Company, Subscription, AuditLog, TruthScan, Scenario

router = APIRouter(prefix="/api/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def log_action(db: Session, user_id, action: str, resource_type: Optional[str] = None, resource_id: Optional[int] = None, details: Optional[dict] = None, ip_address: Optional[str] = None):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address
    )
    db.add(audit_log)
    db.commit()

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserInvite(BaseModel):
    email: str
    role: str = "viewer"

class SubscriptionUpdate(BaseModel):
    plan: Optional[str] = None
    seats: Optional[int] = None
    status: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    company_count: int
    
class CompanyResponse(BaseModel):
    id: int
    name: str
    industry: Optional[str]
    stage: Optional[str]
    user_email: str
    created_at: datetime

class DashboardMetrics(BaseModel):
    total_users: int
    active_users: int
    total_companies: int
    total_subscriptions: int
    mrr: float
    active_simulations: int
    truth_scans_today: int

@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> DashboardMetrics:
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_companies = db.query(Company).count()
    total_subscriptions = db.query(Subscription).filter(Subscription.status == "active").count()
    
    mrr_result = db.query(func.sum(Subscription.monthly_price)).filter(
        Subscription.status == "active"
    ).scalar()
    mrr = float(mrr_result) if mrr_result else 0.0
    
    active_simulations = db.query(Scenario).filter(
        Scenario.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    truth_scans_today = db.query(TruthScan).filter(
        TruthScan.created_at >= today_start
    ).count()
    
    return DashboardMetrics(
        total_users=total_users,
        active_users=active_users,
        total_companies=total_companies,
        total_subscriptions=total_subscriptions,
        mrr=mrr,
        active_simulations=active_simulations,
        truth_scans_today=truth_scans_today
    )

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> List[UserResponse]:
    users = db.query(User).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role or "viewer",
            is_active=u.is_active if hasattr(u, 'is_active') and u.is_active is not None else True,
            created_at=u.created_at,
            company_count=len(u.companies) if u.companies else 0
        )
        for u in users
    ]

@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    changes = {}
    if update.role is not None:
        if update.role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=400, detail="Invalid role")
        changes['role'] = {'from': user.role, 'to': update.role}
        user.role = update.role
    
    if update.is_active is not None:
        changes['is_active'] = {'from': user.is_active, 'to': update.is_active}
        user.is_active = update.is_active
    
    db.commit()
    
    log_action(
        db, current_user.id, "user_updated", "user", user_id, 
        changes, request.client.host if request.client else None
    )
    
    return {"message": "User updated", "user_id": user_id}

@router.delete("/users/{user_id}")
def suspend_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot suspend yourself")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    db.commit()
    
    log_action(
        db, current_user.id, "user_suspended", "user", user_id,
        {"email": user.email}, request.client.host if request.client else None
    )
    
    return {"message": "User suspended", "user_id": user_id}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    db.commit()
    
    log_action(
        db, current_user.id, "user_activated", "user", user_id,
        {"email": user.email}, request.client.host if request.client else None
    )
    
    return {"message": "User activated", "user_id": user_id}

@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> List[CompanyResponse]:
    companies = db.query(Company).all()
    return [
        CompanyResponse(
            id=c.id,
            name=c.name,
            industry=c.industry,
            stage=c.stage,
            user_email=c.user.email if c.user else "Unknown",
            created_at=c.created_at
        )
        for c in companies
    ]

@router.get("/companies/{company_id}")
def get_company_details(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scans = db.query(TruthScan).filter(TruthScan.company_id == company_id).count()
    scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).count()
    
    return {
        "id": company.id,
        "name": company.name,
        "industry": company.industry,
        "stage": company.stage,
        "currency": company.currency,
        "website": company.website,
        "user_email": company.user.email if company.user else None,
        "created_at": company.created_at,
        "stats": {
            "truth_scans": truth_scans,
            "scenarios": scenarios
        }
    }

@router.get("/subscriptions")
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    subscriptions = db.query(Subscription).all()
    return [
        {
            "id": s.id,
            "user_email": s.user.email if s.user else None,
            "company_name": s.company.name if s.company else None,
            "plan": s.plan,
            "status": s.status,
            "seats": s.seats,
            "monthly_price": s.monthly_price,
            "current_period_end": s.current_period_end,
            "created_at": s.created_at
        }
        for s in subscriptions
    ]

@router.patch("/subscriptions/{subscription_id}")
def update_subscription(
    subscription_id: int,
    update: SubscriptionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    changes = {}
    if update.plan is not None:
        changes['plan'] = {'from': subscription.plan, 'to': update.plan}
        subscription.plan = update.plan
    if update.seats is not None:
        changes['seats'] = {'from': subscription.seats, 'to': update.seats}
        subscription.seats = update.seats
    if update.status is not None:
        changes['status'] = {'from': subscription.status, 'to': update.status}
        subscription.status = update.status
    
    db.commit()
    
    log_action(
        db, current_user.id, "subscription_updated", "subscription", subscription_id,
        changes, request.client.host if request.client else None
    )
    
    return {"message": "Subscription updated", "subscription_id": subscription_id}

@router.get("/metrics/aggregate")
def get_aggregate_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from server.models import FinancialRecord
    
    total_revenue = db.query(func.sum(FinancialRecord.revenue)).scalar() or 0
    avg_burn = db.query(func.avg(FinancialRecord.net_burn)).scalar() or 0
    avg_runway = db.query(func.avg(FinancialRecord.runway_months)).filter(
        FinancialRecord.runway_months.isnot(None)
    ).scalar() or 0
    
    users_by_role = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    companies_by_stage = db.query(Company.stage, func.count(Company.id)).group_by(Company.stage).all()
    
    return {
        "financial": {
            "total_revenue": float(total_revenue),
            "avg_burn": float(avg_burn),
            "avg_runway_months": float(avg_runway)
        },
        "users_by_role": {role or "viewer": count for role, count in users_by_role},
        "companies_by_stage": {stage or "unknown": count for stage, count in companies_by_stage}
    }

@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_email": log.user.email if log.user else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": json.loads(log.details) if log.details else None,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        for log in logs
    ]

@router.get("/me")
def get_current_admin(current_user: User = Depends(require_admin)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_admin": current_user.role in [UserRole.OWNER.value, UserRole.ADMIN.value]
    }
