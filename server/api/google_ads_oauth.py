"""
"Connect with Google" for the Google Ads connector.

1. GET /connectors/google-ads/config            -> is the server set up?
2. GET /connectors/companies/{id}/google-ads/oauth-url -> Google consent URL
3. GET /connectors/google-ads/oauth/callback    -> exchange code, verify the
   login can read at least one ad account, store the refresh token encrypted
   under the company's connectors metadata, redirect back to /integrations.

The state parameter is HMAC-signed (company, user, expiry), so the callback
works on any server instance and can't be replayed for another company.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from server.connectors.base import ConnectorConfig
from server.connectors.google_ads import SCOPE, TOKEN_URL, GoogleAdsConnector, app_config, is_configured
from server.core.company_access import company_access_clause
from server.core.company_metadata import save_metadata_value
from server.core.config import settings
from server.core.db import get_db
from server.core.encryption import encrypt_credentials
from server.core.security import get_current_user
from server.models.company import Company
from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])

STATE_TTL_SECONDS = 15 * 60
CALLBACK_PATH = "/api/connectors/google-ads/oauth/callback"


def _sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def _verify(state: str) -> dict:
    try:
        body, sig = state.rsplit(".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid sign-in state")
    expected = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Invalid sign-in state")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=400, detail="The Google sign-in took too long. Try connecting again.")
    return payload


def _base_url(request: Request) -> str:
    from server.api.oauth import _get_base_url
    return _get_base_url(request)


def _require_editor(db: Session, company_id: int, user: User) -> None:
    # These are GET requests that end in a write, so the viewer read-only
    # middleware (which blocks writes by method) doesn't cover them.
    from server.core.company_access import get_user_company_role
    if get_user_company_role(db, company_id, user) not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="View-only members can't connect data sources.")


def _back(base: str, **params: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base}/integrations?{urlencode(params)}", status_code=302)


@router.get("/google-ads/config")
async def google_ads_config(current_user: User = Depends(get_current_user)):
    return {"configured": is_configured()}


@router.get("/companies/{company_id}/google-ads/oauth-url")
async def google_ads_oauth_url(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id, company_access_clause(current_user)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _require_editor(db, company_id, current_user)
    if not is_configured():
        raise HTTPException(status_code=503, detail="Google Ads isn't set up on this server yet.")
    from server.core.plan_usage import enforce_connector_limit
    enforce_connector_limit(db, current_user, company, "google_ads")

    state = _sign({"c": company_id, "u": current_user.id, "exp": int(time.time()) + STATE_TTL_SECONDS})
    params = urlencode({
        "client_id": app_config()["client_id"],
        "redirect_uri": f"{_base_url(request)}{CALLBACK_PATH}",
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",  # always return a refresh token
        "include_granted_scopes": "true",
        "state": state,
    })
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}"}


@router.get("/google-ads/oauth/callback")
async def google_ads_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = _base_url(request)
    if error:
        return _back(base, google_ads_error="Google sign-in was cancelled.")
    payload = _verify(state)
    if payload.get("u") != current_user.id:
        raise HTTPException(status_code=403, detail="This sign-in was started by a different user.")
    company_id = int(payload["c"])
    company = db.query(Company).filter(Company.id == company_id, company_access_clause(current_user)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _require_editor(db, company_id, current_user)

    cfg = app_config()
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(TOKEN_URL, data={
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": f"{base}{CALLBACK_PATH}",
            "grant_type": "authorization_code",
        })
    refresh_token = res.json().get("refresh_token") if res.status_code == 200 else None
    if not refresh_token:
        logger.warning("Google Ads OAuth: token exchange gave no refresh token (HTTP %s) for company %s",
                       res.status_code, company_id)
        return _back(base, google_ads_error="Google didn't grant offline access. Try connecting again.")

    creds = {"refresh_token": refresh_token}
    connector = GoogleAdsConnector(ConnectorConfig(
        provider_id="google_ads", company_id=company_id, credentials=creds, settings={},
    ))
    try:
        if not await connector.authenticate():
            logger.warning("Google Ads OAuth: connect failed for company %s: %s", company_id, connector.auth_error)
            return _back(base, google_ads_error=connector.auth_error or "Couldn't read any Google Ads account.")
        accounts = list(connector.accounts.values())
    finally:
        await connector.close()

    creds["customer_ids"] = ",".join(a["account_id"] for a in accounts)
    save_metadata_value(db, company, ("connectors", "google_ads"), {
        "connected": True,
        "credentials": encrypt_credentials(creds),
        "settings": {},
        "connected_at": datetime.utcnow().isoformat(),
        "account_hint": ", ".join(a["name"] for a in accounts)[:120],
    })
    logger.info("Connected Google Ads (%d accounts) for company %s", len(accounts), company_id)
    return _back(base, connected="google_ads")
