"""
Predixen-side hooks to tie existing user flows into lead-gen.

Place at: server/hooks/lead_gen_hooks.py

Two things this does:

1. When a new user signs up on founderconsole.ai, fire the activation-drip
   webhook in n8n (which sends the welcome email, waits 48h, sends a nudge).

2. When a user completes their first simulation, call predixen's own
   /webhooks/lead-gen/simulation endpoint so the 48h nudge skips them
   AND their P50 number lands in the Leads table (useful for personalized
   replies later).

Both hooks are SAFE NO-OPS if lead-gen is disabled — they check the
`lead_gen_settings.is_enabled` flag first. So you can import + call them
from any existing signup / simulation handler without side effects.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from server.models.lead_gen import LeadGenSettings
from server.services.credentials import CredentialEncryption

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.environ.get("LEAD_GEN_WEBHOOK_SECRET", "")
PREDIXEN_HOST = os.environ.get("PREDIXEN_HOST", "http://localhost:5000")


def _sign(body: dict) -> tuple[str, str]:
    """Return (canonical_body_string, hex_signature)."""
    canonical = json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    sig = hmac.new(WEBHOOK_SECRET.encode(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return canonical, sig


def _get_settings(db: Session) -> Optional[LeadGenSettings]:
    return db.get(LeadGenSettings, 1)


async def on_user_signup(
    db: Session,
    *,
    email: str,
    first_name: Optional[str] = None,
    company_name: Optional[str] = None,
    signup_source: str = "web",
) -> None:
    """
    Call this from your signup endpoint AFTER the user row is committed.
    Fire-and-forget — never raises. Logs warnings on failure.
    """
    settings = _get_settings(db)
    if not settings or not settings.is_enabled or not settings.activation_webhook_url:
        return

    payload = {
        "email": email,
        "first_name": first_name or "",
        "company_name": company_name or "",
        "signup_source": signup_source,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # n8n's public webhook doesn't require HMAC (it's an inbound webhook,
            # not a call TO predixen), so no signing here.
            r = await client.post(settings.activation_webhook_url, json=payload)
            if r.status_code >= 400:
                logger.warning("Activation webhook non-2xx: %d — %s", r.status_code, r.text[:200])
    except httpx.HTTPError as e:
        logger.warning("Activation webhook failed: %s", e)


async def on_simulation_completed(
    db: Session,
    *,
    email: str,
    p50_survival: Optional[int] = None,
) -> None:
    """
    Call this from your /api/simulate endpoint (or wherever a user's first
    successful simulation is detected). Updates the Lead row's
    has_simulated=true so the 48h activation nudge skips them.

    Idempotent: safe to call on every simulation, but cheap — we hit our
    own webhook which upserts.
    """
    settings = _get_settings(db)
    if not settings or not settings.is_enabled:
        return

    payload: dict[str, Any] = {"email": email}
    if p50_survival is not None:
        payload["p50_survival"] = int(p50_survival)

    canonical, sig = _sign(payload)
    url = f"{PREDIXEN_HOST}/webhooks/lead-gen/simulation"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.post(
                url,
                content=canonical.encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Predixen-Signature": sig,
                },
            )
            if r.status_code >= 400:
                logger.warning("Simulation hook non-2xx: %d — %s", r.status_code, r.text[:200])
    except httpx.HTTPError as e:
        logger.warning("Simulation hook failed: %s", e)


# ============================================================
# Usage example — plug into your existing endpoints
# ============================================================
"""
# In server/api/auth.py (or wherever new users are created):

from server.hooks.lead_gen_hooks import on_user_signup

@router.post("/signup")
async def signup(data: SignupIn, db: Session = Depends(get_db)):
    user = create_user(db, data)
    db.commit()

    # Fire-and-forget lead-gen hook
    import asyncio
    asyncio.create_task(on_user_signup(
        db,
        email=user.email,
        first_name=user.display_name.split()[0] if user.display_name else None,
        company_name=data.company_name,
        signup_source="web",
    ))

    return {"user": user}


# In server/api/simulations.py (or wherever sims complete):

from server.hooks.lead_gen_hooks import on_simulation_completed

@router.post("/simulate")
async def simulate(data: SimulateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = run_simulation(data)
    db.commit()

    # Lead-gen hook — skip the 48h nudge and stash P50
    if result.is_first_for_user:
        import asyncio
        asyncio.create_task(on_simulation_completed(
            db,
            email=user.email,
            p50_survival=int(result.p50 * 100),
        ))

    return result
"""
