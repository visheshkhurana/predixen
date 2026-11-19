"""
"Connect with Facebook" for the Meta Ads connector (Facebook Login for Business).

1. GET /connectors/meta-ads/config                    -> is the server set up?
2. GET /connectors/companies/{id}/meta-ads/oauth-url  -> Facebook login dialog URL
3. GET /connectors/meta-ads/oauth/callback            -> exchange the code for a
   user token, swap it for a long-lived one (~60 days), find the ad accounts the
   founder can read, store the token encrypted, redirect back to /integrations.

Server setup (Railway): META_APP_ID, META_APP_SECRET, META_LOGIN_CONFIG_ID (the
Facebook Login for Business configuration that asks for ads_read). Without them
the card falls back to pasting a token by hand.

State is the same HMAC-signed (company, user, expiry) blob the Google flow uses.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from server.api.google_ads_oauth import STATE_TTL_SECONDS, _base_url, _require_editor, _sign, _verify
from server.connectors.base import ConnectorConfig
from server.connectors.meta_ads import BASE_URL, GRAPH_API_VERSION, MetaAdsConnector
from server.core.company_access import company_access_clause
from server.core.company_metadata import save_metadata_value
from server.core.db import get_db
from server.core.encryption import encrypt_credentials
from server.core.security import get_current_user
from server.models.company import Company
from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])

CALLBACK_PATH = "/api/connectors/meta-ads/oauth/callback"
DIALOG_URL = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth"

# Ad account statuses that can never return spend: 2 disabled, 101 closed.
DEAD_ACCOUNT_STATUSES = {2, 101}
MAX_ACCOUNTS = 25


def app_config() -> Dict[str, str]:
    return {
        "app_id": os.getenv("META_APP_ID", "").strip(),
        "app_secret": os.getenv("META_APP_SECRET", "").strip(),
        "config_id": os.getenv("META_LOGIN_CONFIG_ID", "").strip(),
    }


def is_configured() -> bool:
    cfg = app_config()
    return bool(cfg["app_id"] and cfg["app_secret"] and cfg["config_id"])


def _back(base: str, **params: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base}/integrations?{urlencode(params)}", status_code=302)


async def exchange_code(client: httpx.AsyncClient, code: str, redirect_uri: str) -> Dict[str, Any]:
    """code -> short-lived user token -> long-lived user token. Returns {access_token, expires_in}."""
    cfg = app_config()
    res = await client.get(f"{BASE_URL}/oauth/access_token", params={
        "client_id": cfg["app_id"],
        "client_secret": cfg["app_secret"],
        "redirect_uri": redirect_uri,
        "code": code,
    })
    short = res.json().get("access_token") if res.status_code == 200 else None
    if not short:
        raise ValueError(f"code exchange failed (HTTP {res.status_code})")
    res = await client.get(f"{BASE_URL}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": cfg["app_id"],
        "client_secret": cfg["app_secret"],
        "fb_exchange_token": short,
    })
    if res.status_code == 200 and res.json().get("access_token"):
        return res.json()
    # The short-lived token still works for a first sync; the founder reconnects sooner.
    logger.warning("Meta Ads OAuth: long-lived exchange failed (HTTP %s); keeping the short-lived token", res.status_code)
    return {"access_token": short, "expires_in": 3600}


async def list_ad_accounts(connector: MetaAdsConnector) -> List[Dict[str, Any]]:
    """Every ad account the token can see, minus disabled/closed ones."""
    rows, _ = await connector._paged("/me/adaccounts", {"fields": "account_id,name,account_status", "limit": 100})
    live = [r for r in rows if r.get("account_status") not in DEAD_ACCOUNT_STATUSES and r.get("account_id")]
    return live[:MAX_ACCOUNTS]


@router.get("/meta-ads/config")
async def meta_ads_config(current_user: User = Depends(get_current_user)):
    return {"configured": is_configured()}


@router.get("/companies/{company_id}/meta-ads/oauth-url")
async def meta_ads_oauth_url(
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
        raise HTTPException(status_code=503, detail="Meta Ads sign-in isn't set up on this server yet.")
    from server.core.plan_usage import enforce_connector_limit
    enforce_connector_limit(db, current_user, company, "meta_ads")

    cfg = app_config()
    state = _sign({"c": company_id, "u": current_user.id, "p": "meta", "exp": int(time.time()) + STATE_TTL_SECONDS})
    params = urlencode({
        "client_id": cfg["app_id"],
        "redirect_uri": f"{_base_url(request)}{CALLBACK_PATH}",
        "config_id": cfg["config_id"],
        "response_type": "code",
        "override_default_response_type": "true",
        "state": state,
    })
    return {"url": f"{DIALOG_URL}?{params}"}


@router.get("/meta-ads/oauth/callback")
async def meta_ads_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = _base_url(request)
    if error or not code:
        return _back(base, meta_ads_error="Facebook sign-in was cancelled.")
    payload = _verify(state)
    if payload.get("u") != current_user.id or payload.get("p") != "meta":
        raise HTTPException(status_code=403, detail="This sign-in was started by a different user.")
    company_id = int(payload["c"])
    company = db.query(Company).filter(Company.id == company_id, company_access_clause(current_user)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _require_editor(db, company_id, current_user)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = await exchange_code(client, code, f"{base}{CALLBACK_PATH}")
    except (ValueError, httpx.HTTPError) as exc:
        logger.warning("Meta Ads OAuth: %s for company %s", exc, company_id)
        return _back(base, meta_ads_error="Facebook didn't complete the sign-in. Try connecting again.")

    creds: Dict[str, Any] = {"access_token": token["access_token"]}
    connector = MetaAdsConnector(ConnectorConfig(provider_id="meta_ads", company_id=company_id, credentials=creds, settings={}))
    try:
        try:
            accounts = await list_ad_accounts(connector)
        except Exception as exc:  # MetaAPIError or transport error
            logger.warning("Meta Ads OAuth: listing ad accounts failed for company %s: %s", company_id, exc)
            return _back(base, meta_ads_error="Couldn't list your ad accounts. Make sure you allowed ad access.")
        if not accounts:
            return _back(base, meta_ads_error="This Facebook login has no active ad accounts.")
        connector._raw_accounts = ",".join(f"act_{a['account_id']}" for a in accounts)
        if not await connector.authenticate():
            logger.warning("Meta Ads OAuth: connect failed for company %s: %s", company_id, connector.auth_error)
            return _back(base, meta_ads_error=connector.auth_error or "Couldn't read your ad accounts.")
        names = [a["name"] for a in connector.accounts.values()]
    finally:
        await connector.close()

    creds["ad_account_ids"] = connector._raw_accounts
    expires_in = int(token.get("expires_in") or 0)
    if expires_in:
        creds["token_expires_at"] = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    save_metadata_value(db, company, ("connectors", "meta_ads"), {
        "connected": True,
        "credentials": encrypt_credentials(creds),
        "settings": {},
        "connected_at": datetime.utcnow().isoformat(),
        "account_hint": ", ".join(names)[:120],
    })
    logger.info("Connected Meta Ads (%d ad accounts) for company %s", len(names), company_id)
    return _back(base, connected="meta_ads")
