"""
"Connect with <provider>" for OAuth connectors (Zoho Books, QuickBooks, Xero,
Gusto, Salesforce, HubSpot, Amazon Seller Central). Founders sign in to the provider instead of pasting client
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
    # (authorize_url, token_url) for the provider's test environment, when the
    # founder's org lives there (Salesforce sandboxes sign in at test.salesforce.com).
    sandbox_urls: Optional[tuple] = None
    # Query parameter the provider puts the authorization code in.
    code_param: str = "code"
    # Replaces the standard client_id/response_type/scope consent parameters
    # (Amazon's consent page takes an application_id instead).
    authorize_params: Optional[Callable[[Dict[str, str]], Dict[str, str]]] = None
    # Extra env vars that must be set besides <PREFIX>_CLIENT_ID/_SECRET.
    required_env: tuple = ()

    def urls(self, sandbox: bool = False) -> tuple:
        if sandbox and self.sandbox_urls:
            return self.sandbox_urls
        return self.authorize_url, self.token_url

    def app(self) -> Dict[str, str]:
        p = self.env_prefix
        return {
            "client_id": os.getenv(f"{p}_CLIENT_ID", "").strip(),
            "client_secret": os.getenv(f"{p}_CLIENT_SECRET", "").strip(),
            "scopes": (os.getenv(f"{p}_SCOPES", "") or self.default_scopes).strip(),
        }

    def configured(self) -> bool:
        a = self.app()
        return bool(a["client_id"] and a["client_secret"]
                    and all(os.getenv(name, "").strip() for name in self.required_env))


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


async def _finalize_zoho_crm(client, token, params, app):
    # Same Zoho OAuth client as Books, CRM scopes; redeemed at the user's data centre.
    from server.connectors.zoho_crm import zoho_crm_urls

    dc = zoho_dc_from_accounts_server(params.get("accounts-server", ""))
    token_url, api_base = zoho_crm_urls(dc)
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
    org_res = await client.get(f"{api_base}/org",
                               headers={"Authorization": f"Zoho-oauthtoken {data['access_token']}"})
    if org_res.status_code != 200:
        raise OAuthConnectError("This Zoho login has no Zoho CRM organization (or didn't allow CRM access).")
    orgs = (org_res.json() or {}).get("org") or []
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "refresh_token": data["refresh_token"], "access_token": data.get("access_token", ""),
        "dc": dc,
        "_hint": (orgs[0].get("company_name") if orgs else None) or "Zoho CRM",
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


FRESHBOOKS_TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"


async def _finalize_freshbooks(client, token, params, app):
    # FreshBooks documents a JSON token body, so redeem the code here rather
    # than with the generic form-encoded exchange.
    res = await client.post(FRESHBOOKS_TOKEN_URL, json={
        "grant_type": "authorization_code", "code": params.get("code", ""),
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "redirect_uri": params["redirect_uri"],
    }, headers={"Content-Type": "application/json", "Api-Version": "alpha"})
    tok = res.json() if res.status_code == 200 else {}
    if not tok.get("access_token"):
        raise OAuthConnectError("FreshBooks didn't complete the sign-in. Try connecting again.")
    me = await client.get("https://api.freshbooks.com/auth/api/v1/users/me",
                          headers={"Authorization": f"Bearer {tok['access_token']}", "Api-Version": "alpha"})
    body = (me.json() or {}).get("response", {}) if me.status_code == 200 else {}
    accounts = [m.get("business") or {} for m in body.get("business_memberships") or []]
    accounts = [b for b in accounts if b.get("account_id")]
    if not accounts:
        raise OAuthConnectError("This FreshBooks login has no business with accounting access.")
    biz = accounts[0]
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", ""),
        "redirect_uri": params["redirect_uri"], "account_id": biz["account_id"],
        "_hint": biz.get("name") or "FreshBooks",
    }


async def _finalize_wave(client, token, params, app):
    # Wave's token response names the business the user picked.
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "business_id": token.get("businessId") or "",
        "_hint": token.get("businessName") or "Wave",
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
    # GET /oauth/v1/access-tokens/{token} is retired on 16 Feb 2027 and its
    # replacement (POST /oauth/2026-03/token/introspect) doesn't return the
    # portal, so read it from the account-info API instead.
    # https://developers.hubspot.com/changelog/v1-oauth-api-deprecation
    info = await client.get(
        "https://api.hubapi.com/account-info/v3/details",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    acct = info.json() if info.status_code == 200 else {}
    portal = acct.get("portalId")
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token.get("refresh_token", ""),
        "_hint": f"HubSpot portal {portal}" if portal else "HubSpot",
    }


GA4_PROPERTY_PROBE_LIMIT = 10


async def _ga4_busiest_property(client, access_token, props):
    """Pick the property with the most sessions in the last 30 days.

    Accounts often hold old or test properties with no traffic; taking the
    first one silently connects an empty property. Probe up to
    GA4_PROPERTY_PROBE_LIMIT with a one-metric runReport and keep the busiest.
    Falls back to the first property when there is one, or every probe fails.
    """
    if len(props) == 1:
        return props[0]
    best, best_sessions = props[0], -1.0
    for prop in props[:GA4_PROPERTY_PROBE_LIMIT]:
        pid = str(prop.get("property", "")).split("/")[-1]
        if not pid:
            continue
        try:
            res = await client.post(
                f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"dateRanges": [{"startDate": "30daysAgo", "endDate": "today"}],
                      "metrics": [{"name": "sessions"}]},
            )
            if res.status_code != 200:
                continue
            rows = (res.json() or {}).get("rows") or []
            sessions = float(rows[0]["metricValues"][0]["value"]) if rows else 0.0
        except Exception:
            continue
        if sessions > best_sessions:
            best, best_sessions = prop, sessions
    return best


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
    prop = await _ga4_busiest_property(client, token["access_token"], props)
    return {
        "client_id": app["client_id"], "client_secret": app["client_secret"],
        "access_token": token["access_token"], "refresh_token": token["refresh_token"],
        "property_id": str(prop.get("property", "")).split("/")[-1],
        "_hint": prop.get("displayName") or "Google Analytics",
    }


AMAZON_SELLER_CENTRAL = "https://sellercentral.amazon.in"


def _amazon_authorize_params(app: Dict[str, str]) -> Dict[str, str]:
    # https://developer-docs.amazon.com/sp-api/docs/website-authorization-workflow
    # version=beta authorizes a draft (unpublished) app; set AMAZON_SP_PUBLISHED=1
    # once the app is listed on the Appstore.
    params = {"application_id": os.getenv("AMAZON_SP_APP_ID", "").strip()}
    if os.getenv("AMAZON_SP_PUBLISHED", "").strip().lower() not in ("1", "true", "yes"):
        params["version"] = "beta"
    return params


async def _finalize_amazon(client, token, params, app):
    from server.connectors.amazon import SP_API_HOSTS, marketplaces_from_participations

    if not token.get("refresh_token"):
        raise OAuthConnectError("Amazon didn't grant ongoing access. Try connecting again.")
    seller = params.get("selling_partner_id", "")
    # India sellers are on the EU endpoint; try it first, then the others.
    for region in ("eu", "na", "fe"):
        res = await client.get(f"{SP_API_HOSTS[region]}/sellers/v1/marketplaceParticipations",
                               headers={"x-amz-access-token": token["access_token"]})
        if res.status_code == 200:
            marketplaces = marketplaces_from_participations(res.json() or {})
            if marketplaces:
                return {
                    "client_id": app["client_id"], "client_secret": app["client_secret"],
                    "refresh_token": token["refresh_token"], "selling_partner_id": seller,
                    "region": region, "marketplace_ids": marketplaces,
                    "_hint": f"Amazon seller {seller}" if seller else "Amazon Seller Central",
                }
    raise OAuthConnectError("This Amazon login has no active seller marketplace.")


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
        id="zoho_crm", name="Zoho", env_prefix="ZOHO",
        authorize_url="https://accounts.zoho.com/oauth/v2/auth",
        token_url="",  # per data centre, see _finalize_zoho_crm
        default_scopes=("ZohoCRM.org.READ,ZohoCRM.modules.deals.READ,"
                        "ZohoCRM.modules.accounts.READ,ZohoCRM.modules.contacts.READ"),
        scope_separator=",",
        extra_auth_params={"access_type": "offline", "prompt": "consent"},
        finalize=_finalize_zoho_crm,
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
        id="freshbooks", name="FreshBooks", env_prefix="FRESHBOOKS",
        authorize_url="https://auth.freshbooks.com/oauth/authorize",
        token_url="",  # redeemed with a JSON body in _finalize_freshbooks
        default_scopes=("user:profile:read user:invoices:read user:expenses:read "
                        "user:payments:read user:clients:read user:bills:read user:reports:read"),
        finalize=_finalize_freshbooks,
    ),
    OAuthProvider(
        id="wave", name="Wave", env_prefix="WAVE",
        authorize_url="https://api.waveapps.com/oauth2/authorize/",
        token_url="https://api.waveapps.com/oauth2/token/",
        default_scopes="business:read account:read invoice:read transaction:read user:read",
        finalize=_finalize_wave,
    ),
    OAuthProvider(
        id="hubspot", name="HubSpot", env_prefix="HUBSPOT",
        authorize_url="https://app.hubspot.com/oauth/authorize",
        # v1 token endpoint is retired 16 Feb 2027; same form body and response.
        token_url="https://api.hubapi.com/oauth/2026-03/token",
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
        # Sandboxes sign in at test.salesforce.com; refreshes then go to the
        # org's own instance_url, so only the first sign-in needs this host.
        sandbox_urls=("https://test.salesforce.com/services/oauth2/authorize",
                      "https://test.salesforce.com/services/oauth2/token"),
    ),
    OAuthProvider(
        # Login with Amazon client (AMAZON_SP_CLIENT_ID/SECRET) plus the SP-API
        # app id (AMAZON_SP_APP_ID, amzn1.sp.solution...) for the consent page.
        id="amazon", name="Amazon", env_prefix="AMAZON_SP",
        authorize_url=f"{AMAZON_SELLER_CENTRAL}/apps/authorize/consent",
        token_url="https://api.amazon.com/auth/o2/token",
        default_scopes="", code_param="spapi_oauth_code",
        authorize_params=_amazon_authorize_params, required_env=("AMAZON_SP_APP_ID",),
        finalize=_finalize_amazon,
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


async def exchange_code(provider: OAuthProvider, code: str, redirect_uri: str, verifier: str = "",
                        token_url: str = "") -> Dict[str, Any]:
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
        res = await client.post(token_url or provider.token_url, data=data, auth=auth, headers={"Accept": "application/json"})
    token = res.json() if res.status_code == 200 else {}
    if not token.get("access_token"):
        logger.warning("%s OAuth: code exchange failed (HTTP %s)", provider.name, res.status_code)
        raise OAuthConnectError(f"{provider.name} didn't complete the sign-in. Try connecting again.")
    return token


@router.get("/oauth/providers")
async def oauth_providers(current_user: User = Depends(get_current_user)):
    return {pid: {"name": p.name, "configured": p.configured(), "sandbox": bool(p.sandbox_urls)}
            for pid, p in PROVIDERS.items()}


@router.get("/companies/{company_id}/oauth/{provider_id}/url")
async def oauth_url(
    company_id: int,
    provider_id: str,
    request: Request,
    sandbox: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = _provider(provider_id)
    sandbox = sandbox and bool(provider.sandbox_urls)
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
    if sandbox:
        payload["sb"] = 1
    redirect_uri = f"{_base_url(request)}{_callback_path(provider_id)}"
    if provider.authorize_params:
        params: Dict[str, str] = {**provider.authorize_params(app), "redirect_uri": redirect_uri}
    else:
        params = {
            "client_id": app["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            **provider.extra_auth_params,
        }
    if app["scopes"] and not provider.authorize_params:
        params["scope"] = app["scopes"] if provider.scope_separator == " " else app["scopes"]
    if provider.pkce:
        verifier, challenge = _pkce_pair()
        payload["v"] = encrypt_credentials({"v": verifier})
        params.update(code_challenge=challenge, code_challenge_method="S256")
    params["state"] = _sign(payload)
    authorize_url, _ = provider.urls(sandbox)
    return {"url": f"{authorize_url}?{urlencode(params)}"}


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
    code = code or request.query_params.get(provider.code_param, "")
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
            _, token_url = provider.urls(bool(payload.get("sb")))
            if token_url:  # Zoho redeems the code inside its finalizer
                token = await exchange_code(provider, code, redirect_uri, verifier, token_url)
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
