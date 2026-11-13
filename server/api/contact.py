"""Public contact form.

The /contact page used to wait a second and show "Message sent" without
sending anything, so every enquiry was lost. This route delivers it to the
team inbox.

The route is public, so it can only ever mail our own inbox (CONTACT_INBOX),
never an address from the request. The visitor's address goes in Reply-To,
which EmailStr has already rejected if it carries a line break. Every field is
escaped before it reaches HTML, the subject comes from a fixed list, and
callers share the lead-capture rate limiter's bucket logic with their own
store.
"""

import html
import logging
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from server.api.leads import lead_client_key, lead_rate_limited

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_SECONDS = 3600
_CONTACT_HITS: dict[str, list[float]] = {}


class ContactRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    subject: Literal["General Inquiry", "Sales", "Support", "Partnership"]
    message: str = Field(min_length=10, max_length=5000)
    # Honeypot. Hidden from people, filled in by naive bots.
    website: str = Field(default="", max_length=200)


def _contact_inbox() -> str:
    return (os.getenv("CONTACT_INBOX") or "hello@founderconsole.ai").strip()


def _render(data: ContactRequest) -> str:
    name = html.escape(data.name.strip(), quote=True)
    email = html.escape(str(data.email), quote=True)
    message = html.escape(data.message.strip(), quote=True).replace("\n", "<br>")
    return (
        f"<p><strong>{html.escape(data.subject)}</strong> enquiry from the website contact form.</p>"
        f"<p>Name: {name}<br>Email: {email}</p>"
        f"<p>{message}</p>"
    )


@router.post("")
async def submit_contact(data: ContactRequest, request: Request) -> dict:
    if lead_rate_limited(
        lead_client_key(request),
        limit=CONTACT_RATE_LIMIT,
        window=CONTACT_RATE_WINDOW_SECONDS,
        store=_CONTACT_HITS,
    ):
        raise HTTPException(status_code=429, detail="Too many messages. Please email us directly.")
    if data.website:
        # Pretend success so the bot moves on.
        return {"status": "ok"}

    from server.email.service import send_email

    name = " ".join(data.name.split())[:80]
    result = await send_email(
        to=_contact_inbox(),
        subject=f"[Contact] {data.subject} from {name}",
        html_content=_render(data),
        headers={"Reply-To": str(data.email)},
    )
    if not result or result.get("success") is False:
        logger.error("[contact] delivery failed: %s", (result or {}).get("error"))
        raise HTTPException(status_code=502, detail="Could not send your message. Please email us directly.")
    return {"status": "ok"}
