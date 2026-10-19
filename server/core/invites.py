"""Accepting invite tokens (workspace invites and admin platform invites).

Both kinds of invite email link to /auth?invite=<token>. The auth page sends
that token with login/register, or to POST /workspace/invites/accept when the
user is already signed in. A token only works for the address it was sent to.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class InviteError(ValueError):
    """The token is unknown, used, expired, revoked, or for another email."""


def _same_email(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b and a.strip().lower() == b.strip().lower())


def accept_invite(db: Session, user, token: str) -> dict:
    """Apply the invite to `user` and mark it accepted. Caller commits.

    Returns {"kind": "workspace", "company_id", "role"} or
    {"kind": "platform", "role"}. Raises InviteError when it does not apply.
    """
    from server.models.invite import Invite
    from server.models.workspace import WorkspaceInvite, WorkspaceMember

    token = (token or "").strip()
    if not token:
        raise InviteError("Missing invite token")
    now = datetime.utcnow()

    ws = db.query(WorkspaceInvite).filter(WorkspaceInvite.token == token).first()
    if ws is not None:
        if ws.status != "pending":
            raise InviteError("This invite has already been used or was revoked")
        if ws.expires_at and ws.expires_at < now:
            ws.status = "expired"
            raise InviteError("This invite has expired")
        if not _same_email(ws.email, user.email):
            raise InviteError("This invite was sent to a different email address")
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.company_id == ws.company_id,
            WorkspaceMember.user_id == user.id,
        ).first()
        if member is None:
            member = WorkspaceMember(
                company_id=ws.company_id,
                user_id=user.id,
                role=ws.role or "viewer",
                status="active",
                invited_by=ws.invited_by,
                invited_at=ws.invited_at or now,
                joined_at=now,
            )
            db.add(member)
        else:
            member.role = ws.role or member.role
            member.status = "active"
            member.joined_at = member.joined_at or now
        ws.status = "accepted"
        return {"kind": "workspace", "company_id": ws.company_id, "role": member.role}

    inv = db.query(Invite).filter(Invite.token == token).first()
    if inv is not None:
        if inv.accepted:
            raise InviteError("This invite has already been used")
        if inv.expires_at and inv.expires_at < now:
            raise InviteError("This invite has expired")
        if not _same_email(inv.email, user.email):
            raise InviteError("This invite was sent to a different email address")
        if inv.role:
            user.role = inv.role
        inv.accepted = True
        inv.accepted_at = now
        return {"kind": "platform", "role": inv.role}

    raise InviteError("Invite not found")


def accept_invite_quietly(db: Session, user, token: Optional[str]) -> Optional[dict]:
    """For login/register: a bad invite must never block signing in."""
    if not token:
        return None
    try:
        result = accept_invite(db, user, token)
        db.commit()
        return result
    except InviteError as e:
        db.commit()  # persist an "expired" status flip, if any
        logger.info("Invite not applied for user %s: %s", getattr(user, "id", None), e)
    except Exception as e:  # pragma: no cover - defensive
        db.rollback()
        logger.warning("Invite acceptance failed for user %s: %s", getattr(user, "id", None), e)
    return None
