import os
import secrets
import logging
import requests
from urllib.parse import urlencode
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.config import settings
from server.core.security import create_access_token
from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["oauth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


_oauth_states: dict = {}


def _get_base_url(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host and "localhost" not in forwarded_host and "127.0.0.1" not in forwarded_host:
        proto = request.headers.get("x-forwarded-proto", "https")
        return f"{proto}://{forwarded_host}"

    host = request.headers.get("host", "")
    if host and "localhost" not in host and "127.0.0.1" not in host:
        proto = request.headers.get("x-forwarded-proto", "https")
        return f"{proto}://{host}"

    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN") or os.environ.get("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit_domain:
        return f"https://{replit_domain}"

    override = os.environ.get("OAUTH_BASE_URL")
    if override:
        return override.rstrip("/")

    return "https://localhost:5000"


def _get_or_create_oauth_user(db: Session, email: str, provider: str, oauth_id: str,
                               display_name: str = None, avatar_url: str = None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        if not user.oauth_provider:
            user.oauth_provider = provider
            user.oauth_id = oauth_id
        if display_name and not user.display_name:
            user.display_name = display_name
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        password_hash=None,
        oauth_provider=provider,
        oauth_id=oauth_id,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _build_auth_redirect(request: Request, user: User) -> RedirectResponse:
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    is_admin = bool(admin_email and user.email.lower().strip() == admin_email)
    base = _get_base_url(request)
    params = urlencode({
        "token": access_token,
        "user_id": user.id,
        "email": user.email,
        "role": user.role or "viewer",
        "is_platform_admin": "true" if is_admin else "false",
    })
    return RedirectResponse(url=f"{base}/auth/callback?{params}", status_code=302)


@router.get("/google/start")
def google_start(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = "google"

    base = _get_base_url(request)
    redirect_uri = f"{base}/api/auth/google/callback"
    logger.info(f"Google OAuth start - base_url: {base}, redirect_uri: {redirect_uri}")

    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    })
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}", status_code=302)


@router.get("/google/callback")
def google_callback(request: Request, code: str = None, state: str = None, error: str = None,
                    db: Session = Depends(get_db)):
    if error:
        logger.warning(f"Google OAuth error: {error}")
        base = _get_base_url(request)
        return RedirectResponse(url=f"{base}/auth?error=google_denied", status_code=302)

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    stored = _oauth_states.pop(state, None)
    if stored != "google":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    base = _get_base_url(request)
    redirect_uri = f"{base}/api/auth/google/callback"

    try:
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=10)
        token_resp.raise_for_status()
        tokens = token_resp.json()
    except Exception as e:
        logger.error(f"Google token exchange failed: {e}")
        return RedirectResponse(url=f"{base}/auth?error=google_token_failed", status_code=302)

    access_token = tokens.get("access_token")
    if not access_token:
        return RedirectResponse(url=f"{base}/auth?error=google_no_token", status_code=302)

    try:
        user_resp = requests.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {access_token}",
        }, timeout=10)
        user_resp.raise_for_status()
        profile = user_resp.json()
    except Exception as e:
        logger.error(f"Google userinfo failed: {e}")
        return RedirectResponse(url=f"{base}/auth?error=google_profile_failed", status_code=302)

    email = profile.get("email")
    if not email:
        return RedirectResponse(url=f"{base}/auth?error=google_no_email", status_code=302)

    user = _get_or_create_oauth_user(
        db,
        email=email.lower().strip(),
        provider="google",
        oauth_id=profile.get("id", ""),
        display_name=profile.get("name"),
        avatar_url=profile.get("picture"),
    )
    return _build_auth_redirect(request, user)


