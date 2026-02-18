from fastapi import HTTPException
from sqlalchemy.orm import Session
from server.models.company import Company
from server.models.user import User


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

    if getattr(user, 'is_platform_admin', False) or getattr(user, 'role', '') == 'admin':
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

    if getattr(user, 'is_platform_admin', False) or getattr(user, 'role', '') == 'admin':
        return "admin"

    raise HTTPException(status_code=403, detail="Access denied to this company")
