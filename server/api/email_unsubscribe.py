"""Public, tokenized lifecycle unsubscribe.

This is the only new unauthenticated surface. The token is an HMAC of the
user id, so a link unsubscribes that account and cannot be rewritten to
another. GET shows state for the page. POST is the RFC 8058 one-click
action and the page confirm. Neither requires a session.

Password-reset and verification mail do not use this route.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.email.lifecycle_guard import (
    apply_unsubscribe,
    mask_email,
    user_opted_out,
    verify_unsubscribe_token,
)
from server.models.user import User

router = APIRouter(prefix="/email", tags=["email-unsubscribe"])


async def _token_from_request(request: Request, token: Optional[str]) -> str:
    if token:
        return token.strip()
    if request.method == "POST":
        try:
            form = await request.form()
        except Exception:
            form = None
        if form:
            posted = form.get("token")
            if posted:
                return str(posted).strip()
    return ""


@router.api_route("/unsubscribe", methods=["GET", "POST"])
async def unsubscribe(
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    raw = await _token_from_request(request, token)
    user_id = verify_unsubscribe_token(raw)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid or forged unsubscribe token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="This unsubscribe link is no longer valid")

    if request.method == "GET":
        return {
            "ok": True,
            "unsubscribed": user_opted_out(db, user_id),
            "masked_email": mask_email(user.email),
        }

    outcome = apply_unsubscribe(db, user_id)
    if outcome == "missing":
        raise HTTPException(status_code=404, detail="This unsubscribe link is no longer valid")
    return {
        "ok": True,
        "unsubscribed": True,
        "already": outcome == "already",
        "masked_email": mask_email(user.email),
    }
