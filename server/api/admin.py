from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.config import settings
from server.models import User, UserRole, Company, Subscription, AuditLog, TruthScan, Scenario, LoginHistory, Notification, Invite, LLMAuditLog, EvalRun, TeamMember
from server.models.financial import FinancialRecord

router = APIRouter(prefix="/admin", tags=["admin"])

def require_platform_admin(current_user: User = Depends(get_current_user)):
    """
    Ensures only the platform owner (whose email matches ADMIN_MASTER_EMAIL) 
    can access admin endpoints. This is NOT a company-level role check.
    """
    admin_email = settings.ADMIN_MASTER_EMAIL
    if not admin_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access is not configured"
        )
    
    user_email = getattr(current_user, 'email', '').lower().strip()
    admin_email_normalized = admin_email.lower().strip()
    
    if user_email != admin_email_normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the platform owner can access admin features."
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)):
    """Legacy function - redirects to require_platform_admin for security."""
    return require_platform_admin(current_user)

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
    
class InviteResponse(BaseModel):
    id: int
    email: str
    role: str
    invited_by_email: str
    accepted: bool
    expires_at: datetime
    created_at: datetime
    is_expired: bool

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

class MeResponse(BaseModel):
    id: int
    email: str
    role: str
    is_admin: bool

@router.get("/me")
def get_current_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
) -> MeResponse:
    """Returns admin info - only accessible to platform owner."""
    role = current_user.role or "owner"
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        role=role,
        is_admin=True
    )

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
    
    if mrr == 0:
        from sqlalchemy import desc
        latest_records = (
            db.query(FinancialRecord.company_id, func.max(FinancialRecord.period_end).label('latest'))
            .group_by(FinancialRecord.company_id)
            .subquery()
        )
        latest_mrr = (
            db.query(func.sum(FinancialRecord.mrr))
            .join(latest_records, 
                  (FinancialRecord.company_id == latest_records.c.company_id) & 
                  (FinancialRecord.period_end == latest_records.c.latest))
            .scalar()
        )
        if latest_mrr and latest_mrr > 0:
            mrr = float(latest_mrr)
    
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
    from sqlalchemy import text
    
    try:
        result = db.execute(text("""
            SELECT 
                COALESCE(SUM(revenue), 0) as total_revenue,
                COALESCE(AVG(cogs + opex + payroll + other_costs), 0) as avg_burn,
                COALESCE(AVG(cash_balance), 0) as avg_cash
            FROM financial_records
        """)).fetchone()
        
        total_revenue = float(result[0]) if result else 0
        avg_burn = float(result[1]) if result else 0
        avg_cash = float(result[2]) if result else 0
        avg_runway = avg_cash / avg_burn if avg_burn > 0 else 12
    except Exception:
        total_revenue = 0
        avg_burn = 0
        avg_runway = 12
    
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
    action_type: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(AuditLog)
    if action_type:
        query = query.filter(AuditLog.action == action_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
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

@router.get("/login-history")
def get_login_history(
    limit: int = 100,
    success_only: Optional[bool] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        from sqlalchemy import text
        
        query_sql = """
            SELECT id, user_id, email, ip_address, user_agent, device_type, browser, os, 
                   country, city, success, failure_reason, created_at
            FROM login_history
        """
        conditions = []
        params = {}
        
        if success_only is not None:
            conditions.append("success = :success")
            params["success"] = success_only
        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id
            
        if conditions:
            query_sql += " WHERE " + " AND ".join(conditions)
        
        query_sql += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = db.execute(text(query_sql), params).fetchall()
        
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "email": row[2],
                "ip_address": row[3],
                "user_agent": row[4],
                "device_type": row[5],
                "browser": row[6],
                "os": row[7],
                "country": row[8],
                "city": row[9],
                "success": row[10],
                "failure_reason": row[11],
                "created_at": row[12]
            }
            for row in result
        ]
    except Exception as e:
        return []

@router.post("/users/{user_id}/suspend")
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
    
    return {"message": f"User {user.email} suspended", "user_id": user_id}

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
    
    return {"message": f"User {user.email} activated", "user_id": user_id}

@router.get("/notifications")
def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT id, user_id, company_id, type, severity, title, message, read, created_at
            FROM notifications
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "company_id": row[2],
                "type": row[3],
                "severity": row[4],
                "title": row[5],
                "message": row[6],
                "read": row[7],
                "created_at": row[8]
            }
            for row in result
        ]
    except Exception:
        return []

@router.get("/stats/activity")
def get_activity_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        from sqlalchemy import text
        
        result = db.execute(text("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM login_history
            WHERE created_at >= NOW() - INTERVAL ':days days'
            AND success = true
            GROUP BY DATE(created_at)
            ORDER BY date
        """.replace(":days", str(days)))).fetchall()
        
        logins_by_date = {str(row[0]): row[1] for row in result}
        
        new_users = db.execute(text("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM users
            WHERE created_at >= NOW() - INTERVAL ':days days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """.replace(":days", str(days)))).fetchall()
        
        users_by_date = {str(row[0]): row[1] for row in new_users}
        
        return {
            "logins_by_date": logins_by_date,
            "new_users_by_date": users_by_date
        }
    except Exception:
        return {"logins_by_date": {}, "new_users_by_date": {}}

@router.get("/users/{user_id}/details")
def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        from sqlalchemy import text
        
        last_login = db.execute(text("""
            SELECT created_at, ip_address, device_type, browser
            FROM login_history
            WHERE user_id = :user_id AND success = true
            ORDER BY created_at DESC
            LIMIT 1
        """), {"user_id": user_id}).fetchone()
        
        login_count = db.execute(text("""
            SELECT COUNT(*) FROM login_history
            WHERE user_id = :user_id AND success = true
        """), {"user_id": user_id}).scalar() or 0
        
    except Exception:
        last_login = None
        login_count = 0
    
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role or "viewer",
        "is_active": user.is_active,
        "created_at": user.created_at,
        "company_count": len(user.companies) if user.companies else 0,
        "companies": [{"id": c.id, "name": c.name} for c in (user.companies or [])],
        "last_login": {
            "timestamp": last_login[0] if last_login else None,
            "ip_address": last_login[1] if last_login else None,
            "device_type": last_login[2] if last_login else None,
            "browser": last_login[3] if last_login else None
        } if last_login else None,
        "total_logins": login_count
    }


@router.get("/invites")
def list_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> List[InviteResponse]:
    invites = db.query(Invite).order_by(Invite.created_at.desc()).all()
    return [
        InviteResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role or "viewer",
            invited_by_email=inv.invited_by.email if inv.invited_by else "Unknown",
            accepted=inv.accepted,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            is_expired=datetime.utcnow() > inv.expires_at if inv.expires_at else False
        )
        for inv in invites
    ]


@router.post("/invites")
async def create_invite(
    invite_data: UserInvite,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from server.email.service import send_invite_email, is_email_configured
    
    existing_user = db.query(User).filter(User.email == invite_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    existing_invite = db.query(Invite).filter(
        Invite.email == invite_data.email,
        Invite.accepted == False
    ).first()
    
    if existing_invite:
        invite_is_expired = datetime.utcnow() > existing_invite.expires_at if existing_invite.expires_at else False
        if not invite_is_expired:
            raise HTTPException(status_code=400, detail="An active invite already exists for this email")
    
    if invite_data.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    invite = Invite.create_invite(
        email=invite_data.email,
        role=invite_data.role,
        invited_by_id=current_user.id
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    email_sent = False
    email_error = None
    
    if is_email_configured():
        email_result = await send_invite_email(
            to_email=invite_data.email,
            invite_token=invite.token,
            role=invite_data.role,
            invited_by_email=current_user.email,
            expires_at=invite.expires_at
        )
        email_sent = email_result.get("success", False)
        if not email_sent:
            email_error = email_result.get("error")
    
    log_action(
        db, current_user.id, "invite_created", "invite", invite.id,
        {"email": invite_data.email, "role": invite_data.role, "email_sent": email_sent},
        request.client.host if request.client else None
    )
    
    return {
        "message": f"Invite created for {invite_data.email}" + (" and email sent" if email_sent else ""),
        "invite_id": invite.id,
        "token": invite.token,
        "expires_at": invite.expires_at,
        "email_sent": email_sent,
        "email_error": email_error
    }


@router.delete("/invites/{invite_id}")
def revoke_invite(
    invite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    if invite.accepted:
        raise HTTPException(status_code=400, detail="Cannot revoke an accepted invite")
    
    email = invite.email
    db.delete(invite)
    db.commit()
    
    log_action(
        db, current_user.id, "invite_revoked", "invite", invite_id,
        {"email": email}, request.client.host if request.client else None
    )
    
    return {"message": f"Invite for {email} revoked"}


@router.post("/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from datetime import timedelta
    from server.email.service import send_invite_email, is_email_configured
    
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    if invite.accepted:
        raise HTTPException(status_code=400, detail="Cannot resend an accepted invite")
    
    invite.expires_at = datetime.utcnow() + timedelta(days=7)
    db.commit()
    
    email_sent = False
    email_error = None
    
    if is_email_configured():
        email_result = await send_invite_email(
            to_email=invite.email,
            invite_token=invite.token,
            role=invite.role,
            invited_by_email=current_user.email,
            expires_at=invite.expires_at
        )
        email_sent = email_result.get("success", False)
        if not email_sent:
            email_error = email_result.get("error")
    
    log_action(
        db, current_user.id, "invite_resent", "invite", invite_id,
        {"email": invite.email, "email_sent": email_sent}, request.client.host if request.client else None
    )
    
    return {
        "message": f"Invite for {invite.email} resent" + (" and email sent" if email_sent else ""),
        "expires_at": invite.expires_at,
        "email_sent": email_sent,
        "email_error": email_error
    }


class LLMAuditLogResponse(BaseModel):
    id: str
    company_id: Optional[int]
    user_id: Optional[int]
    endpoint: str
    model: str
    pii_mode: str
    prompt_hash: str
    input_chars_original: int
    input_chars_redacted: int
    pii_findings_json: Optional[List[dict]]
    redacted_prompt_preview: Optional[str]
    redacted_output_preview: Optional[str]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    latency_ms: Optional[int]
    created_at: datetime


class LLMAuditListResponse(BaseModel):
    logs: List[LLMAuditLogResponse]
    total: int
    page: int
    per_page: int


@router.get("/llm-audit")
def get_llm_audit_logs(
    company_id: Optional[int] = None,
    pii_mode: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get LLM audit logs with filtering."""
    query = db.query(LLMAuditLog)
    
    if company_id:
        query = query.filter(LLMAuditLog.company_id == company_id)
    if pii_mode:
        query = query.filter(LLMAuditLog.pii_mode == pii_mode)
    if start_date:
        query = query.filter(LLMAuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(LLMAuditLog.created_at <= end_date)
    
    total = query.count()
    logs = query.order_by(LLMAuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/llm-audit/{log_id}")
def get_llm_audit_log_detail(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get detailed LLM audit log."""
    import uuid
    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log ID format")
    
    log = db.query(LLMAuditLog).filter(LLMAuditLog.id == log_uuid).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return log.to_dict()


@router.get("/llm-audit/stats/summary")
def get_llm_audit_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get LLM audit statistics summary."""
    try:
        from sqlalchemy import func
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total_requests = db.query(func.count(LLMAuditLog.id)).filter(
            LLMAuditLog.created_at >= start_date
        ).scalar()
        
        total_tokens_in = db.query(func.sum(LLMAuditLog.tokens_in)).filter(
            LLMAuditLog.created_at >= start_date
        ).scalar() or 0
        
        total_tokens_out = db.query(func.sum(LLMAuditLog.tokens_out)).filter(
            LLMAuditLog.created_at >= start_date
        ).scalar() or 0
        
        avg_latency = db.query(func.avg(LLMAuditLog.latency_ms)).filter(
            LLMAuditLog.created_at >= start_date
        ).scalar() or 0
        
        pii_mode_breakdown = db.query(
            LLMAuditLog.pii_mode,
            func.count(LLMAuditLog.id)
        ).filter(
            LLMAuditLog.created_at >= start_date
        ).group_by(LLMAuditLog.pii_mode).all()
        
        try:
            requests_with_pii = db.query(func.count(LLMAuditLog.id)).filter(
                LLMAuditLog.created_at >= start_date,
                LLMAuditLog.pii_findings_json != None,
                func.jsonb_array_length(LLMAuditLog.pii_findings_json) > 0
            ).scalar() or 0
        except Exception:
            requests_with_pii = 0
        
        return {
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "avg_latency_ms": round(float(avg_latency), 2),
            "pii_mode_breakdown": {mode: count for mode, count in pii_mode_breakdown},
            "requests_with_pii_detected": requests_with_pii
        }
    except Exception:
        return {
            "period_days": days,
            "total_requests": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "avg_latency_ms": 0,
            "pii_mode_breakdown": {},
            "requests_with_pii_detected": 0
        }


class EvalRunRequest(BaseModel):
    suite_name: str
    inputs: Optional[dict] = None


class EvalRunResponse(BaseModel):
    id: str
    suite_name: str
    inputs_json: Optional[dict]
    outputs_json: Optional[dict]
    scores_json: Optional[dict]
    overall_score: Optional[float]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


@router.get("/evals/runs")
def get_eval_runs(
    suite_name: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get evaluation runs with filtering."""
    query = db.query(EvalRun)
    
    if suite_name:
        query = query.filter(EvalRun.suite_name == suite_name)
    if status:
        query = query.filter(EvalRun.status == status)
    
    total = query.count()
    runs = query.order_by(EvalRun.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "runs": [run.to_dict() for run in runs],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/evals/runs/{run_id}")
def get_eval_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get detailed eval run."""
    import uuid
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    run = db.query(EvalRun).filter(EvalRun.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    
    return run.to_dict()


@router.post("/evals/run")
async def run_eval_suite(
    request: EvalRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Run an evaluation suite."""
    from server.lib.evals.eval_runner import run_evaluation_suite
    
    eval_run = EvalRun(
        suite_name=request.suite_name,
        inputs_json=request.inputs or {},
        status="running"
    )
    db.add(eval_run)
    db.commit()
    db.refresh(eval_run)
    
    try:
        results = await run_evaluation_suite(request.suite_name, request.inputs or {}, db)
        
        eval_run.outputs_json = results.get("outputs", {})
        eval_run.scores_json = results.get("scores", {})
        eval_run.overall_score = results.get("overall_score", 0)
        eval_run.status = "completed"
        eval_run.completed_at = datetime.utcnow()
        db.commit()
        
        return eval_run.to_dict()
    except Exception as e:
        eval_run.status = "failed"
        eval_run.error_message = str(e)
        eval_run.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Eval suite failed: {str(e)}")


@router.get("/evals/suites")
def get_available_eval_suites(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    """Get list of available evaluation suites."""
    return {
        "suites": [
            {
                "name": "copilot_quality",
                "description": "Tests Copilot response quality, citation coverage, and structure compliance",
                "metrics": ["citation_coverage", "structure_compliance", "hallucination_risk", "pii_leak_check"]
            },
            {
                "name": "extraction_accuracy", 
                "description": "Tests financial data extraction accuracy from documents",
                "metrics": ["field_accuracy", "numeric_tolerance", "currency_normalization"]
            },
            {
                "name": "pii_redaction",
                "description": "Tests PII redaction effectiveness across different data types",
                "metrics": ["email_redaction", "phone_redaction", "card_redaction", "token_redaction"]
            }
        ]
    }


class TeamMemberCreate(BaseModel):
    name: str
    email: str
    role: str
    type: str = "full_time"
    department: str = "Engineering"
    status: str = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    salary_range: Optional[str] = None
    skills: Optional[List[str]] = []
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    salary_range: Optional[str] = None
    skills: Optional[List[str]] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None


@router.get("/team")
def list_team_members(
    type: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    query = db.query(TeamMember)
    if type:
        query = query.filter(TeamMember.type == type)
    if department:
        query = query.filter(TeamMember.department == department)
    if status:
        query = query.filter(TeamMember.status == status)
    else:
        query = query.filter(TeamMember.status != "offboarded")
    members = query.order_by(TeamMember.created_at.desc()).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "type": m.type,
            "department": m.department,
            "status": m.status,
            "start_date": m.start_date,
            "end_date": m.end_date,
            "salary_range": m.salary_range,
            "skills": m.skills or [],
            "github_url": m.github_url,
            "linkedin_url": m.linkedin_url,
            "notes": m.notes,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in members
    ]


@router.post("/team")
def create_team_member(
    data: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    member = TeamMember(
        name=data.name,
        email=data.email,
        role=data.role,
        type=data.type,
        department=data.department,
        status=data.status,
        start_date=data.start_date,
        end_date=data.end_date,
        salary_range=data.salary_range,
        skills=data.skills or [],
        github_url=data.github_url,
        linkedin_url=data.linkedin_url,
        notes=data.notes,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "role": member.role,
        "type": member.type,
        "department": member.department,
        "status": member.status,
        "start_date": member.start_date,
        "end_date": member.end_date,
        "salary_range": member.salary_range,
        "skills": member.skills or [],
        "github_url": member.github_url,
        "linkedin_url": member.linkedin_url,
        "notes": member.notes,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
    }


@router.put("/team/{member_id}")
def update_team_member(
    member_id: int,
    data: TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)
    member.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(member)
    return {
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "role": member.role,
        "type": member.type,
        "department": member.department,
        "status": member.status,
        "start_date": member.start_date,
        "end_date": member.end_date,
        "salary_range": member.salary_range,
        "skills": member.skills or [],
        "github_url": member.github_url,
        "linkedin_url": member.linkedin_url,
        "notes": member.notes,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
    }


@router.delete("/team/{member_id}")
def delete_team_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin)
):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    member.status = "offboarded"
    member.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Team member offboarded"}
