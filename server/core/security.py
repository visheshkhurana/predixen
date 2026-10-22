from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Union, Set
from jose import JWTError, jwt
import bcrypt
import uuid
from fastapi import Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from server.core.config import settings
from server.core.db import get_db
import json
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

AUTH_COOKIE_NAME = "auth_token"
REFRESH_COOKIE_NAME = "refresh_token"
AUTH_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7

# Per-process cache of revoked jtis. The database (RevokedAccessToken) is the
# source of truth; this only saves a query for tokens revoked in this process.
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


# Warnings already emitted, so a deploy window does not log one line per request.
_revocation_warned: Set[str] = set()

# How many times each exception class has been swallowed. The warning above is
# suppressed after the first occurrence of a class, which means the count is the
# only place a later, different failure is still visible. Read it through
# ``revocation_suppressed_counts()``.
_revocation_suppressed: Dict[str, int] = {}


def revocation_suppressed_counts() -> Dict[str, int]:
    """Exceptions swallowed by ``_guarded_revocation``, per class name.

    Revocation degrades rather than failing the request, so a swallowed error is
    intended. What must not be silent is a *different* error of the same class:
    the first warning names the class, this counter says how many have happened.
    """
    return dict(_revocation_suppressed)


def _guarded_revocation(db: Session, fn, default=None):
    """Run a statement against a revocation table, degrading to ``default`` when
    the table is missing or unreadable.

    The revocation tables are created in ``_run_deferred_startup`` (server/main.py),
    which runs *after* the app starts answering requests, so every deploy has a
    window where authenticated requests arrive before the tables exist. Ending a
    session is a hardening feature; losing it for a few seconds is much better
    than every authenticated request returning 500. With the tables present this
    is a plain query.

    The statement runs inside a SAVEPOINT, because on PostgreSQL a failed
    statement aborts the surrounding transaction and the request's own commit
    would then fail with a second, unrelated error. Pending work is flushed
    first so that rolling back to the savepoint cannot discard it.
    """
    try:
        db.flush()
        with db.begin_nested():
            return fn()
    except SQLAlchemyError as exc:
        name = exc.__class__.__name__
        seen = _revocation_suppressed.get(name, 0) + 1
        _revocation_suppressed[name] = seen
        if name not in _revocation_warned:
            _revocation_warned.add(name)
            logger.warning(
                "Session revocation unavailable (%s); treating revocation as off for now: %s",
                name, exc,
            )
        elif seen & (seen - 1) == 0:
            # Every second, fourth, eighth ... suppression is logged, so a class
            # that keeps failing is observable in the log and not only in the
            # counter. Between those points the counter carries the count.
            logger.warning(
                "Session revocation still unavailable (%s) - %d occurrences so far, "
                "latest: %s",
                name, seen, exc,
            )
        return default


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _from_epoch(value) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def revoke_token(jti: str, db: Optional[Session] = None, user_id: Optional[int] = None,
                 expires_at: Optional[datetime] = None):
    """Revoke one access token by its JTI. Persisted when a db session is given."""
    if not jti:
        return
    _revoked_tokens.add(jti)
    if db is None:
        return
    from server.models.session_revocation import RevokedAccessToken

    def _persist():
        if db.query(RevokedAccessToken).filter(RevokedAccessToken.jti == jti).first() is None:
            db.add(RevokedAccessToken(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at or (_utcnow_naive() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
            ))

    # The in-process set above already revoked it; a missing table must not turn
    # logout into a 500.
    _guarded_revocation(db, _persist)


def revoke_token_string(token: Optional[str], db: Session) -> None:
    """Revoke the access token in a cookie/header value, if it is one of ours."""
    payload = decode_token(token) if token else None
    if not payload or not payload.get("jti"):
        return
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        user_id = None
    revoke_token(payload["jti"], db=db, user_id=user_id, expires_at=_from_epoch(payload.get("exp")))


def revoke_all_sessions(db: Session, user_id: int) -> None:
    """End every session a user has: access tokens issued so far, and refresh tokens.

    Used on password reset and suspension. The cutoff is floored to the second
    because JWT ``iat`` is whole seconds; a token minted after this call (the
    next login) has iat >= cutoff and stays valid.
    """
    from server.models.session_revocation import UserSessionCutoff
    from server.models.user import RefreshToken

    cutoff = _utcnow_naive().replace(microsecond=0)

    def _write_cutoff():
        row = db.query(UserSessionCutoff).filter(UserSessionCutoff.user_id == user_id).first()
        if row is None:
            db.add(UserSessionCutoff(user_id=user_id, revoked_before=cutoff))
        else:
            row.revoked_before = cutoff

    _guarded_revocation(db, _write_cutoff)

    # Refresh tokens live in their own table, which predates this feature; the
    # reset or suspension must still end them even if the cutoff is unavailable.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,  # noqa: E712
    ).update({RefreshToken.revoked: True}, synchronize_session=False)


def is_token_revoked(jti: str, db: Optional[Session] = None) -> bool:
    """Check if a token has been revoked."""
    if not jti:
        return False
    if jti in _revoked_tokens:
        return True
    if db is None:
        return False
    from server.models.session_revocation import RevokedAccessToken

    found = _guarded_revocation(
        db,
        lambda: db.query(RevokedAccessToken).filter(RevokedAccessToken.jti == jti).first() is not None,
        False,
    )
    if found:
        _revoked_tokens.add(jti)
    return found


def _issued_before_cutoff(db: Session, user_id: int, iat) -> bool:
    from server.models.session_revocation import UserSessionCutoff

    row = _guarded_revocation(
        db,
        lambda: db.query(UserSessionCutoff).filter(UserSessionCutoff.user_id == user_id).first(),
        None,
    )
    if row is None:
        return False
    issued = _from_epoch(iat)
    # A token with no iat predates this check; treat it as issued before any cutoff.
    return issued is None or issued < row.revoked_before

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


def set_refresh_cookie(response: Response, token: str):
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/api/auth",
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth",
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
    if jti and is_token_revoked(jti, db):
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

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is suspended",
        )

    if _issued_before_cutoff(db, user.id, payload.get("iat")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has ended. Please sign in again.",
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
