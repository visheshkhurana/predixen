from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from datetime import timedelta
from server.core.db import get_db
from server.core.security import get_password_hash, verify_password, create_access_token
from server.core.config import settings
from server.models.user import User
from server.models.login_history import LoginHistory
import re
import bcrypt
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

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError("Password must contain at least one special character")
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

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
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
    
    user = User(
        email=normalized_email,
        password_hash=get_password_hash(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_login_attempt(db, user.email, user.id, success=True, request=request)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email and user.email.lower().strip() == admin_email)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "viewer",
        is_platform_admin=is_platform_admin
    )

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
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
    
    # Only seed demo data if explicitly enabled via config (not on every login in production)
    if user.email == "demo@founderconsole.ai" and settings.should_seed_demo_data:
        try:
            from server.seed.seed_demo import seed_demo_data
            seed_demo_data(db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Demo seed on login failed: {e}")
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_platform_admin = bool(admin_email and user.email.lower().strip() == admin_email)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "viewer",
        is_platform_admin=is_platform_admin
    )


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
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
    
    access_token = create_access_token(
        data={"sub": str(user.id), "admin": True},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        role=user.role or "owner",
        is_platform_admin=True
    )
