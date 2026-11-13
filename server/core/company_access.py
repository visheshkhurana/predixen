from fastapi import HTTPException
from sqlalchemy.orm import Session
from server.models.company import Company
from server.models.user import User


def is_platform_admin(user) -> bool:
    """Cross-company access is for the platform owner only.

    The master session, or the verified account whose email matches
    ADMIN_MASTER_EMAIL (the same rule require_platform_admin applies, plus
    the verified-email check). A company-level role such as "admin" is not
    platform access and must never open other tenants' companies.
    """
    if user is None:
        return False
    from server.core.security import is_master_user
    if is_master_user(user):
        return True
    from server.core.config import settings
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    if not admin_email:
        return False
    user_email = (getattr(user, "email", "") or "").lower().strip()
    return user_email == admin_email and getattr(user, "is_email_verified", False) is True


def get_user_company(db: Session, company_id: int, user: User) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.user_id == user.id:
        return company

    try:
        from server.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.company_id == company_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active"
        ).first()
        if member:
            return company
    except Exception:
        pass

    if is_platform_admin(user):
        return company

    raise HTTPException(status_code=403, detail="Access denied to this company")


def get_user_company_role(db: Session, company_id: int, user: User) -> str:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.user_id == user.id:
        return "owner"

    try:
        from server.models.workspace import WorkspaceMember
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.company_id == company_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active"
        ).first()
        if member:
            return member.role or "viewer"
    except Exception:
        pass

    if is_platform_admin(user):
        return "admin"

    raise HTTPException(status_code=403, detail="Access denied to this company")
