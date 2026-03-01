from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Set
from jose import JWTError, jwt
import bcrypt
import uuid
from fastapi import Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from server.core.config import settings
from server.core.db import get_db
import json
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

AUTH_COOKIE_NAME = "auth_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7

_revoked_tokens: Set[str] = set()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),  # Unique token ID for revocation
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def revoke_token(jti: str):
    """Revoke a token by its JTI (JWT ID)."""
    _revoked_tokens.add(jti)


def is_token_revoked(jti: str) -> bool:
    """Check if a token has been revoked."""
    return jti in _revoked_tokens

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

class MasterUser:
    """Virtual user object for master admin authentication - represents platform-level admin."""
    def __init__(self):
        self.id = -1
        self.email = settings.ADMIN_MASTER_EMAIL
        self.role = "owner"
        self.is_active = True
        self.is_platform_admin = True
        self._is_master_user = True

def set_auth_cookie(response: Response, token: str):
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=AUTH_COOKIE_MAX_AGE,
        path="/",
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    from server.models.user import User

    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    if user_id == "master" and payload.get("is_master"):
        return MasterUser()

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user.is_platform_admin = False
    user._is_master_user = False
    return user

def is_master_user(user) -> bool:
    """Check if user is the MasterUser (platform admin)."""
    return hasattr(user, '_is_master_user') and user._is_master_user

def log_audit(db: Session, user_id: int, action: str, resource_type: Optional[str] = None,
              resource_id: Optional[int] = None, company_id: Optional[int] = None,
              details: Optional[dict] = None, ip_address: Optional[str] = None):
    """Log audit events, especially for MasterUser access to company data."""
    from server.models.audit_log import AuditLog

    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps({
                "company_id": company_id,
                **(details or {})
            }) if company_id or details else None,
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log audit event: {e}")
        try:
            db.rollback()
        except Exception:
            pass

def require_company_access(company_id: int):
    """
    Factory function that creates a dependency for validating company access.

    Rules:
    - MasterUser (id=-1) can access any company
    - Regular users can only access their own companies
    - All access by MasterUser is logged for audit purposes
    """
    async def _require_company_access(
        current_user: Union['User', MasterUser] = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Union['User', MasterUser]:
        from server.models.company import Company

        # MasterUser can access any company
        if is_master_user(current_user):
            # Verify the company exists
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found"
                )

            # Log MasterUser access for audit purposes
            log_audit(
                db,
                user_id=current_user.id,
                action="master_user_company_access",
                resource_type="company",
                resource_id=company_id,
                company_id=company_id,
                details={"accessed_by_master": True}
            )
            return current_user

        # Regular users can only access their own companies
        company = db.query(Company).filter(
            Company.id == company_id,
            Company.user_id == current_user.id
        ).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to access this company."
            )

        return current_user

    return _require_company_access

def require_investor_mode():
    if not settings.FEATURE_INVESTOR_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Investor mode is not enabled"
        )
