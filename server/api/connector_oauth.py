"""
"Connect with <provider>" for OAuth connectors (Zoho Books, QuickBooks, Xero,
Gusto, Salesforce, HubSpot). Founders sign in to the provider instead of pasting client
secrets and tokens.

  GET /connectors/oauth/providers                       -> which providers are set up on this server
  GET /connectors/companies/{id}/oauth/{provider}/url    -> provider consent URL
  GET /connectors/oauth/{provider}/callback              -> exchange code, find the org/tenant/realm,
                                                            verify, store encrypted, back to /integrations

Each provider needs <PREFIX>_CLIENT_ID and <PREFIX>_CLIENT_SECRET on the
server (and optionally <PREFIX>_SCOPES), and the redirect URI
https://<host>/api/connectors/oauth/<provider_id>/callback registered with
the provider. The stored credentials have the same shape the connectors
already read, so sync code is unchanged; rotated refresh tokens are saved
after each sync (connectors.py::_persist_rotated_credentials).

State is the HMAC-signed blob used by the Google/Meta flows. The PKCE
verifier rides inside it, encrypted.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from server.api.google_ads_oauth import STATE_TTL_SECONDS, _base_url, _require_editor, _sign, _verify
from server.connectors.base import ConnectorConfig
from server.connectors.registry import ConnectorRegistry
from server.connectors.zoho_books import zoho_dc_from_accounts_server, zoho_urls
from server.core.company_access import company_access_clause
from server.core.company_metadata import save_metadata_value
from server.core.db import get_db
from server.core.encryption import decrypt_credentials, encrypt_credentials
from server.core.security import get_current_user
from server.models.company import Company
from server.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class OAuthConnectError(Exception):
    """A message safe to show the founder."""


Finalize = Callable[[httpx.AsyncClient, Dict[str, Any], Dict[str, str], Dict[str, str]], Awaitable[Dict[str, Any]]]


@dataclass
class OAuthProvider:
    id: str
    name: str
    env_prefix: str
    authorize_url: str
    token_url: str
    default_scopes: str
    # Provider wants client credentials as HTTP Basic auth at the token endpoint.
    basic_auth: bool = False
    pkce: bool = False
    scope_separator: str = " "
    extra_auth_params: Dict[str, str] = field(default_factory=dict)
    # Build the stored credentials from the token response and callback params.
    finalize: Optional[Finalize] = None

    def app(self) -> Dict[str, str]:
        p = self.env_prefix
        return {
            "client_id": os.getenv(f"{p}_CLIENT_ID", "").strip(),
            "client_secret": os.getenv(f"{p}_CLIENT_SECRET", "").strip(),
            "scopes": (os.getenv(f"{p}_SCOPES", "") or self.default_scopes).strip(),
        }

    def configured(self) -> bool:
        a = self.app()
        return bool(a["client_id"] and a["client_secret"])


# ---------------------------------------------------------------- finalizers

async def _finalize_zoho(client, token, params, app):
    # Zoho sends the user's data centre back on the callback; the code can only
    # be redeemed there, and the org only reached through that DC's API host.
    dc = zoho_dc_from_accounts_server(params.get("accounts-server", ""))
    token_url, api_base = zoho_urls(dc)
    res = await client.post(token_url, data={
        "grant_type": "authorization_code",
        "code": params["code"],
        "client_id": app["client_id"],
        "client_secret": app["client_secret"],
        "redirect_uri": params["redirect_uri"],
    })
    data = res.json() if res.status_code == 200 else {}
    if not data.get("refresh_token"):
        raise OAuthConnectError("Zoho didn't grant offline access. Try connecting again.")
    orgs = await client.get(f"{api_base}/organizations",
                            headers={"Authorization": f"Zoho-oauthtoken {data['access_token']}"})
    org_list = (orgs.json() or {}).get("organizations") or [] if orgs.status_code == 200 else []
    if not org_list:
        raise OAuthConnectError("This Zoho login has no Zoho Books organization.")
    default = next((o for o in org_list if o.get("is_default_org")), org_list[0])
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "refresh_token": data["refresh_token"], "access_token": data.get("access_token", ""),
        "organization_id": str(default.get("organization_id", "")), "dc": dc,
        "_hint": default.get("name") or "Zoho Books",
    }


async def _finalize_quickbooks(client, token, params, app):
    realm = params.get("realmId", "")
    if not realm:
        raise OAuthConnectError("QuickBooks didn't say which company you picked. Try again.")
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "realm_id": realm, "_hint": f"QuickBooks company {realm}",
    }


async def _finalize_xero(client, token, params, app):
    res = await client.get("https://api.xero.com/connections",
                           headers={"Authorization": f"Bearer {token['access_token']}"})
    tenants = [t for t in (res.json() if res.status_code == 200 else []) if t.get("tenantType") in (None, "ORGANISATION")]
    if not tenants:
        raise OAuthConnectError("No Xero organisation was shared. Pick one when Xero asks.")
    t = tenants[0]
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "tenant_id": t.get("tenantId", ""), "_hint": t.get("tenantName") or "Xero",
    }


async def _finalize_gusto(client, token, params, app):
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "_hint": "Gusto",
    }


async def _finalize_salesforce(client, token, params, app):
    instance = (token.get("instance_url") or "").rstrip("/")
    if not instance.startswith("https://"):
        raise OAuthConnectError("Salesforce didn't return your org's address. Try again.")
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "instance_url": instance, "_hint": instance.replace("https://", ""),
    }


async def _finalize_hubspot(client, token, params, app):
    info = await client.get(f"https://api.hubapi.com/oauth/v1/access-tokens/{token['access_token']}")
    hub = info.json() if info.status_code == 200 else {}
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "_hint": hub.get("hub_domain") or "HubSpot",
    }


async def _finalize_google_analytics(client, token, params, app):
    if not token.get("refresh_token"):
        raise OAuthConnectError("Google didn't grant offline access. Try connecting again.")
    # Pick the founder's first GA4 property (Admin API account summaries).
    res = await client.get("https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
                           headers={"Authorization": f"Bearer {token['access_token']}"}, params={"pageSize": 200})
    summaries = (res.json() or {}).get("accountSummaries", []) if res.status_code == 200 else []
    props = [p for acc in summaries for p in acc.get("propertySummaries", []) or []]
    if not props:
        raise OAuthConnectError("This Google account has no Google Analytics 4 property.")
    prop = props[0]
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token["refresh_token"],
        "property_id": str(prop.get("property", "")).split("/")[-1],
        "_hint": prop.get("displayName") or "Google Analytics",
    }


PROVIDERS: Dict[str, OAuthProvider] = {p.id: p for p in [
    OAuthProvider(
        id="zoho_books", name="Zoho", env_prefix="ZOHO",
        authorize_url="https://accounts.zoho.com/oauth/v2/auth",
        token_url="",  # per data centre, see _finalize_zoho
        default_scopes=("ZohoBooks.settings.READ,ZohoBooks.invoices.READ,ZohoBooks.accountants.READ,"
                        "ZohoBooks.expenses.READ,ZohoBooks.contacts.READ,ZohoBooks.banking.READ"),
        scope_separator=",",
        extra_auth_params={"access_type": "offline", "prompt": "consent"},
        finalize=_finalize_zoho,
    ),
    OAuthProvider(
        id="quickbooks", name="QuickBooks", env_prefix="QUICKBOOKS",
        authorize_url="https://appcenter.intuit.com/connect/oauth2",
        token_url="https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
        default_scopes="com.intuit.quickbooks.accounting", basic_auth=True,
        finalize=_finalize_quickbooks,
    ),
    OAuthProvider(
        id="xero", name="Xero", env_prefix="XERO",
        authorize_url="https://login.xero.com/identity/connect/authorize",
        token_url="https://identity.xero.com/connect/token",
        # Granular scopes: Xero apps created on/after 2 March 2026 cannot request
        # the broad accounting.transactions / accounting.reports.read scopes
        # (https://developer.xero.com/faq/granular-scopes). XERO_SCOPES overrides,
        # e.g. for an older app still on the broad scopes.
        default_scopes=("offline_access accounting.settings.read accounting.contacts.read "
                        "accounting.invoices.read accounting.banktransactions.read "
                        "accounting.reports.profitandloss.read accounting.reports.balancesheet.read"),
        basic_auth=True, finalize=_finalize_xero,
    ),
    OAuthProvider(
        id="gusto", name="Gusto", env_prefix="GUSTO",
        authorize_url="https://api.gusto.com/oauth/authorize",
        token_url="https://api.gusto.com/oauth/token",
        default_scopes="", finalize=_finalize_gusto,
    ),
    OAuthProvider(
        id="hubspot", name="HubSpot", env_prefix="HUBSPOT",
        authorize_url="https://app.hubspot.com/oauth/authorize",
        token_url="https://api.hubapi.com/oauth/v1/token",
        default_scopes="oauth crm.objects.deals.read crm.objects.contacts.read crm.objects.companies.read",
        finalize=_finalize_hubspot,
    ),
    OAuthProvider(
        id="google_analytics", name="Google", env_prefix="GOOGLE_ANALYTICS",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        default_scopes="https://www.googleapis.com/auth/analytics.readonly",
        extra_auth_params={"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"},
        finalize=_finalize_google_analytics,
    ),
    OAuthProvider(
        id="salesforce", name="Salesforce", env_prefix="SALESFORCE",
        authorize_url="https://login.salesforce.com/services/oauth2/authorize",
        token_url="https://login.salesforce.com/services/oauth2/token",
        default_scopes="api refresh_token", pkce=True, finalize=_finalize_salesforce,
    ),
]}


def _provider(provider_id: str) -> OAuthProvider:
    p = PROVIDERS.get(provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="This connector doesn't use sign-in.")
    return p


def _callback_path(provider_id: str) -> str:
    return f"/api/connectors/oauth/{provider_id}/callback"


def _back(base: str, **params: str) -> RedirectResponse:
    return RedirectResponse(url=f"{base}/integrations?{urlencode(params)}", status_code=302)


def _pkce_pair() -> tuple:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


async def exchange_code(provider: OAuthProvider, code: str, redirect_uri: str, verifier: str = "") -> Dict[str, Any]:
    """Standard authorization_code exchange. Returns the token JSON or raises OAuthConnectError."""
    app = provider.app()
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
    auth = None
    if provider.basic_auth:
        auth = (app["client_id"], app["client_secret"])
    else:
        data.update(client_id=app["client_id"], client_secret=app["client_secret"])
    if verifier:
        data["code_verifier"] = verifier
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(provider.token_url, data=data, auth=auth, headers={"Accept": "application/json"})
    token = res.json() if res.status_code == 200 else {}
    if not token.get("access_token"):
        logger.warning("%s OAuth: code exchange failed (HTTP %s)", provider.name, res.status_code)
        raise OAuthConnectError(f"{provider.name} didn't complete the sign-in. Try connecting again.")
    return token


@router.get("/oauth/providers")
async def oauth_providers(current_user: User = Depends(get_current_user)):
    return {pid: {"name": p.name, "configured": p.configured()} for pid, p in PROVIDERS.items()}


@router.get("/companies/{company_id}/oauth/{provider_id}/url")
async def oauth_url(
    company_id: int,
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = _provider(provider_id)
    company = db.query(Company).filter(Company.id == company_id, company_access_clause(current_user)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _require_editor(db, company_id, current_user)
    if not provider.configured():
        raise HTTPException(status_code=503, detail=f"{provider.name} sign-in isn't set up on this server yet.")
    from server.core.plan_usage import enforce_connector_limit
    enforce_connector_limit(db, current_user, company, provider_id)

    app = provider.app()
    payload: Dict[str, Any] = {"c": company_id, "u": current_user.id, "p": provider_id,
                               "exp": int(time.time()) + STATE_TTL_SECONDS}
    params: Dict[str, str] = {
        "client_id": app["client_id"],
        "redirect_uri": f"{_base_url(request)}{_callback_path(provider_id)}",
        "response_type": "code",
        **provider.extra_auth_params,
    }
    if app["scopes"]:
        params["scope"] = app["scopes"] if provider.scope_separator == " " else app["scopes"]
    if provider.pkce:
        verifier, challenge = _pkce_pair()
        payload["v"] = encrypt_credentials({"v": verifier})
        params.update(code_challenge=challenge, code_challenge_method="S256")
    params["state"] = _sign(payload)
    return {"url": f"{provider.authorize_url}?{urlencode(params)}"}


@router.get("/oauth/{provider_id}/callback")
async def oauth_callback(
    provider_id: str,
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = _provider(provider_id)
    base = _base_url(request)
    if error or not code:
        return _back(base, oauth_error=f"{provider.name} sign-in was cancelled.", provider=provider_id)
    payload = _verify(state)
    if payload.get("u") != current_user.id or payload.get("p") != provider_id:
        raise HTTPException(status_code=403, detail="This sign-in was started by a different user.")
    company_id = int(payload["c"])
    company = db.query(Company).filter(Company.id == company_id, company_access_clause(current_user)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    _require_editor(db, company_id, current_user)

    redirect_uri = f"{base}{_callback_path(provider_id)}"
    params = {k: v for k, v in request.query_params.items()}
    params["redirect_uri"] = redirect_uri
    verifier = ""
    if payload.get("v"):
        verifier = (decrypt_credentials(payload["v"]) or {}).get("v", "")

    app = provider.app()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token: Dict[str, Any] = {}
            if provider.token_url:  # Zoho redeems the code inside its finalizer
                token = await exchange_code(provider, code, redirect_uri, verifier)
            creds = await provider.finalize(client, token, params, app)
    except OAuthConnectError as exc:
        return _back(base, oauth_error=str(exc), provider=provider_id)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("%s OAuth: connect failed for company %s: %s", provider.name, company_id, exc)
        return _back(base, oauth_error=f"Couldn't finish connecting {provider.name}. Try again.", provider=provider_id)

    hint = str(creds.pop("_hint", provider.name))[:120]
    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    connector = connector_class(ConnectorConfig(provider_id=provider_id, company_id=company_id, credentials=creds, settings={}))
    try:
        ok = await connector.authenticate()
        creds = connector.rotated_credentials() or creds
    except Exception as exc:  # provider-side failure while verifying
        logger.warning("%s OAuth: verification error for company %s: %s", provider.name, company_id, exc)
        ok = False
    finally:
        close = getattr(connector, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:
                pass
    if not ok:
        return _back(base, oauth_error=f"Signed in, but couldn't read your {provider.name} data.", provider=provider_id)

    save_metadata_value(db, company, ("connectors", provider_id), {
        "connected": True,
        "credentials": encrypt_credentials(creds),
        "settings": {},
        "connected_at": datetime.utcnow().isoformat(),
        "account_hint": hint,
    })
    logger.info("Connected %s for company %s", provider.name, company_id)
    return _back(base, connected=provider_id)
