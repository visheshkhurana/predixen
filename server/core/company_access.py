import contextvars
import re
from typing import Optional, Tuple

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


# Viewers (workspace role "viewer") may read a company but not change it.
# The request's method and path are recorded per request by
# RequestContextMiddleware so the shared access checks below can tell a read
# from a write without every route passing its method in.
_REQUEST: contextvars.ContextVar[Optional[Tuple[str, str]]] = contextvars.ContextVar(
    "company_access_request", default=None
)
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Asking Copilot and exporting a report are reads even though they are POSTs.
_VIEWER_ALLOWED_WRITES = re.compile(r"/(chat|quick-chat)/?$|^(/api)?/export/|/board-export/")
VIEWER_READ_ONLY_DETAIL = (
    "You have view-only access to this company. Ask the owner to make you an "
    "editor to change anything."
)


class RequestContextMiddleware:
    """Pure ASGI middleware that records (method, path) for access checks."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        token = _REQUEST.set((scope.get("method", "GET").upper(), scope.get("path", "")))
        try:
            await self.app(scope, receive, send)
        finally:
            _REQUEST.reset(token)


def _is_restricted_write() -> bool:
    req = _REQUEST.get()
    if not req:
        return False
    method, path = req
    return method in _WRITE_METHODS and not _VIEWER_ALLOWED_WRITES.search(path)


def company_access_clause(user):
    """SQL filter: companies `user` owns or is an active workspace member of.

    Use in place of ``Company.user_id == current_user.id`` so invited
    teammates see the same companies get_user_company lets them open.
    Platform-admin access is not included; that stays explicit.
    """
    from sqlalchemy import or_, select
    from server.models.workspace import WorkspaceMember
    conditions = [
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.status == "active",
    ]
    if _is_restricted_write():
        conditions.append(WorkspaceMember.role != "viewer")
    member_company_ids = select(WorkspaceMember.company_id).where(*conditions)
    return or_(Company.user_id == user.id, Company.id.in_(member_company_ids))


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
    except Exception:
        member = None
    if member:
        if (member.role or "viewer") == "viewer" and _is_restricted_write():
            raise HTTPException(status_code=403, detail=VIEWER_READ_ONLY_DETAIL)
        return company

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
