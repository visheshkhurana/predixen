from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from datetime import timedelta, datetime
from server.core.db import get_db
from server.core.security import get_password_hash, verify_password, create_access_token, get_current_user, set_auth_cookie, clear_auth_cookie, set_refresh_cookie, REFRESH_COOKIE_NAME
from server.core.config import settings
from server.models.user import User, PasswordResetToken, EmailVerificationToken, RefreshToken
from server.models.login_history import LoginHistory
import re
import bcrypt
import uuid
import asyncio
import logging

auth_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string to extract device, browser, and OS info."""
    device_type = "Desktop"
    if "Mobile" in user_agent or "Android" in user_agent:
        device_type = "Mobile"
    elif "Tablet" in user_agent or "iPad" in user_agent:
        device_type = "Tablet"
    
    browser = "Unknown"
    if "Chrome" in user_agent and "Edg" not in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser = "Safari"
    elif "Edg" in user_agent:
        browser = "Edge"
    
    os = "Unknown"
    if "Windows" in user_agent:
        os = "Windows"
    elif "Mac OS" in user_agent:
        os = "macOS"
    elif "Linux" in user_agent:
        os = "Linux"
    elif "Android" in user_agent:
        os = "Android"
    elif "iOS" in user_agent or "iPhone" in user_agent:
        os = "iOS"
    
    return {"device_type": device_type, "browser": browser, "os": os}

def log_login_attempt(db: Session, email: str, user_id: int = None, success: bool = True, 
                      failure_reason: str = None, request: Request = None):
    """Log a login attempt to the database."""
    ip_address = None
    user_agent = None
    device_info = {"device_type": None, "browser": None, "os": None}
    
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        if user_agent:
            device_info = parse_user_agent(user_agent)
    
    try:
        login_record = LoginHistory(
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info["device_type"],
            browser=device_info["browser"],
            os=device_info["os"],
            success=success,
            failure_reason=failure_reason
        )
        db.add(login_record)
        db.commit()
    except Exception:
        db.rollback()

def _issue_refresh_token(db: Session, user_id: int) -> str:
    token = str(uuid.uuid4())
    refresh = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(refresh)
    db.commit()
    return token


def _issue_tokens(response: Response, db: Session, user_id: int):
    access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    set_auth_cookie(response, access_token)
    refresh = _issue_refresh_token(db, user_id)
    set_refresh_cookie(response, refresh)
    return access_token


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v):
        sanitized = re.sub(r'<[^>]*>', '', v).strip()
        return sanitized

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    role: str = "viewer"
    is_platform_admin: bool = False
    is_email_verified: bool = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    # Normalize email to lowercase
    normalized_email = req.email.lower().strip()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        log_login_attempt(db, req.email, success=False, 
                         failure_reason="Email already registered", request=request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    sanitized_name = req.name if req.name else None
    
    user = User(
        email=normalized_email,
        password_hash=get_password_hash(req.password),
        display_name=sanitized_name,
        is_email_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_login_attempt(db, user.email, user.id, success=True, request=request)
    
    try:
        token = str(uuid.uuid4())
        verification = EmailVerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(verification)
        db.commit()
        from server.email.service import send_email_verification
        await send_email_verification(user.email, token)
    except Exception as e:
        auth_logger.warning(f"Failed to send verification email: {e}")
    
    access_token = _issue_tokens(response, db, user.id)
    
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email and user.email.lower().strip() == admin_email)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "viewer",
        is_platform_admin=is_platform_admin,
        is_email_verified=False
    )

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        log_login_attempt(db, req.email, user.id if user else None, success=False,
                         failure_reason="Invalid credentials", request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        log_login_attempt(db, req.email, user.id, success=False,
                         failure_reason="Account suspended", request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support."
        )
    
    log_login_attempt(db, user.email, user.id, success=True, request=request)
    
    if user.email == "demo@founderconsole.ai" and settings.should_seed_demo_data:
        try:
            from server.seed.seed_demo import seed_demo_data
            seed_demo_data(db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Demo seed on login failed: {e}")
    
    access_token = _issue_tokens(response, db, user.id)
    
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email and user.email.lower().strip() == admin_email)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "viewer",
        is_platform_admin=is_platform_admin,
        is_email_verified=getattr(user, 'is_email_verified', True)
    )


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Admin-only login endpoint with master credentials support."""
    
    admin_email_config = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    req_email_lower = req.email.lower().strip()
    
    # Verify master credentials using bcrypt hash comparison (not plaintext)
    master_password_valid = False
    if admin_email_config and settings.ADMIN_MASTER_PASSWORD_HASH and req_email_lower == admin_email_config:
        try:
            master_password_valid = bcrypt.checkpw(
                req.password.encode('utf-8'),
                settings.ADMIN_MASTER_PASSWORD_HASH.encode('utf-8')
            )
        except (ValueError, TypeError) as e:
            auth_logger.error(f"Master password hash verification failed: {e}")

    if master_password_valid:
        log_login_attempt(db, req.email, None, success=True, request=request)

        access_token = create_access_token(
            data={"sub": "master", "admin": True, "is_master": True},
            expires_delta=timedelta(minutes=settings.MASTER_TOKEN_EXPIRE_MINUTES)
        )
        
        return TokenResponse(
            access_token=access_token,
            user_id=-1,
            email=settings.ADMIN_MASTER_EMAIL,
            role="owner",
            is_platform_admin=True
        )
    
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        log_login_attempt(db, req.email, user.id if user else None, success=False,
                         failure_reason="Invalid admin credentials", request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    admin_email_check = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email_check and user.email.lower().strip() == admin_email_check)
    
    if not is_platform_admin:
        log_login_attempt(db, req.email, user.id, success=False,
                         failure_reason="Not the platform administrator", request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only the platform owner can access the admin section."
        )
    
    if not user.is_active:
        log_login_attempt(db, req.email, user.id, success=False,
                         failure_reason="Account suspended", request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support."
        )
    
    log_login_attempt(db, user.email, user.id, success=True, request=request)
    
    access_token = _issue_tokens(response, db, user.id)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "owner",
        is_platform_admin=True
    )


@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    old_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not old_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    record = db.query(RefreshToken).filter(
        RefreshToken.token == old_token,
    ).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if record.revoked:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == record.user_id,
            RefreshToken.revoked == False,
        ).update({"revoked": True})
        db.commit()
        clear_auth_cookie(response)
        auth_logger.warning(f"Refresh token reuse detected for user {record.user_id} — all tokens revoked")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token reuse detected. Please log in again.")

    if record.expires_at < datetime.utcnow():
        record.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or suspended")

    record.revoked = True
    new_refresh = str(uuid.uuid4())
    record.replaced_by = new_refresh
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    set_auth_cookie(response, access_token)

    refresh_record = RefreshToken(
        user_id=user.id,
        token=new_refresh,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(refresh_record)
    db.commit()
    set_refresh_cookie(response, new_refresh)

    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email and user.email.lower().strip() == admin_email)

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "viewer",
        is_platform_admin=is_platform_admin,
        is_email_verified=getattr(user, 'is_email_verified', True),
    )


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        return {"message": "If an account with that email exists, a reset link has been sent."}
    
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})
    db.commit()
    
    token = str(uuid.uuid4())
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(reset_token)
    db.commit()
    
    try:
        from server.email.service import send_password_reset_email
        await send_password_reset_email(user.email, token)
    except Exception as e:
        auth_logger.warning(f"Failed to send password reset email: {e}")
    
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if token_record.expires_at < datetime.utcnow():
        token_record.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(req.new_password)
    token_record.used = True
    db.commit()
    
    return {"message": "Password has been reset successfully. You can now log in with your new password."}


@router.post("/send-verification")
async def send_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if getattr(current_user, 'is_email_verified', False):
        return {"message": "Email is already verified."}
    
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == current_user.id,
        EmailVerificationToken.used == False
    ).update({"used": True})
    db.commit()
    
    token = str(uuid.uuid4())
    verification = EmailVerificationToken(
        user_id=current_user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(verification)
    db.commit()
    
    try:
        from server.email.service import send_email_verification
        await send_email_verification(current_user.email, token)
    except Exception as e:
        auth_logger.warning(f"Failed to send verification email: {e}")
    
    return {"message": "Verification email sent. Check your inbox."}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.used == False
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    if token_record.expires_at < datetime.utcnow():
        token_record.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )
    
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    user.is_email_verified = True
    token_record.used = True
    db.commit()
    
    return {"message": "Email verified successfully. You can now use all features."}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    rt = request.cookies.get(REFRESH_COOKIE_NAME)
    if rt:
        record = db.query(RefreshToken).filter(RefreshToken.token == rt, RefreshToken.revoked == False).first()
        if record:
            record.revoked = True
            db.commit()
    clear_auth_cookie(response)
    return {"message": "Logged out successfully."}
