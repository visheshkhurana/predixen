"""Best-effort server-side PostHog capture and alias.

There is no PostHog Python SDK in this repo. Browser identify
(client/src/lib/posthog.ts identifyUser) uses String(userId). Server events
for a logged-in user must use that same distinct_id. Signup also sends
$create_alias so a pre-signup lead or anonymous id joins that person.

Internal and test accounts are marked with the person property
``$internal_or_test_user``. The address used to decide that stays on the
server; it is not a PostHog property.

A failed send must never raise — the product action already succeeded by the
time this runs, and a visitor cannot do anything with a telemetry error.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# Same live project token the browser SDK ships. VITE_POSTHOG_KEY / POSTHOG_KEY
# historically pointed at a nonexistent project. An env value is used only when
# it matches this token. A different value is logged and ignored — never sent.
_DEFAULT_KEY = "phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M"
_DEFAULT_HOST = "https://us.i.posthog.com"
_MAX_DISTINCT_ID = 200
# Log a key choice once per process. A stale env token must be visible, not
# repeated on every lead.
_logged_choice: tuple | None = None


def _fingerprint(key: str) -> str:
    """Short id for logs. Never the full token."""
    if len(key) < 16:
        return f"len={len(key)}"
    return f"{key[:8]}…{key[-4:]}"


def _env_key() -> tuple[str, str]:
    """Return (value, source name) for the first non-empty env token."""
    primary = (os.environ.get("POSTHOG_KEY") or "").strip()
    if primary:
        return primary, "POSTHOG_KEY"
    secondary = (os.environ.get("POSTHOG_PROJECT_API_KEY") or "").strip()
    if secondary:
        return secondary, "POSTHOG_PROJECT_API_KEY"
    return "", ""


def _log_key_choice(signature: tuple, level: int, message: str, *args: object) -> None:
    global _logged_choice
    if signature == _logged_choice:
        return
    _logged_choice = signature
    logger.log(level, message, *args)


def _api_key() -> str:
    """Project token that matches the browser SDK.

    Logs which key is used, once per choice. A stale env token is not sent.
    """
    env_key, env_source = _env_key()
    if not env_key:
        _log_key_choice(
            ("default", _DEFAULT_KEY),
            logging.INFO,
            "[posthog] using default fingerprint=%s (browser project token)",
            _fingerprint(_DEFAULT_KEY),
        )
        return _DEFAULT_KEY
    if env_key == _DEFAULT_KEY:
        _log_key_choice(
            ("match", env_source, env_key),
            logging.INFO,
            "[posthog] using %s fingerprint=%s; matches the browser project token",
            env_source,
            _fingerprint(env_key),
        )
        return env_key
    _log_key_choice(
        ("refuse", env_source, env_key),
        logging.WARNING,
        "[posthog] refusing %s fingerprint=%s; it does not match the browser "
        "project token fingerprint=%s. Server events stay on the known-good token.",
        env_source,
        _fingerprint(env_key),
        _fingerprint(_DEFAULT_KEY),
    )
    return _DEFAULT_KEY


def _host() -> str:
    return (os.environ.get("POSTHOG_HOST") or _DEFAULT_HOST).rstrip("/")


def user_distinct_id(user_id: int) -> str:
    """Same id browser identifyUser sends: String(userId)."""
    return str(user_id)


# Local-part prefix used by apply-flow smoke accounts.
_SMOKE_LOCAL_PREFIX = "apply-smoke+"
# RFC 2606 documentation domain. Real founders do not sign up here.
_TEST_EMAIL_DOMAINS = frozenset({"example.com"})
# Demo login special-cased in auth, the demo seed, and the client.
_INTERNAL_ACCOUNT_EMAILS = frozenset({"demo@founderconsole.ai"})


def _normalized_email(email: object) -> Optional[tuple[str, str, str]]:
    """Return (address, local part, domain), lowercased, or None.

    The pieces stay in this process. Nothing here is a PostHog property.
    """
    if not isinstance(email, str):
        return None
    normalized = email.strip().lower()
    if not normalized or any(ch.isspace() for ch in normalized):
        return None
    local, sep, domain = normalized.rpartition("@")
    if not sep or not local or not domain:
        return None
    return normalized, local, domain


def _admin_master_email() -> str:
    """Existing platform-admin address from settings. Not a new env var."""
    try:
        from server.core.config import settings

        return (settings.ADMIN_MASTER_EMAIL or "").strip().lower()
    except Exception:
        return ""


def is_internal_or_test_account(
    email: Optional[str] = None,
    *,
    is_platform_admin: bool = False,
    is_master: bool = False,
) -> bool:
    """True when PostHog should treat this account as internal or test.

    Smoke addresses (``apply-smoke+...``), ``@example.com``, the demo
    account, the configured platform-admin address, and the existing
    platform-admin / master flags. A company role such as admin or owner
    is a customer role and does not qualify.

    The address is an input to this boolean only.
    """
    if is_platform_admin or is_master:
        return True
    parsed = _normalized_email(email)
    if parsed is None:
        return False
    full, local, domain = parsed
    if local.startswith(_SMOKE_LOCAL_PREFIX):
        return True
    if domain in _TEST_EMAIL_DOMAINS:
        return True
    if full in _INTERNAL_ACCOUNT_EMAILS:
        return True
    admin = _admin_master_email()
    return bool(admin) and full == admin


# Cohort 429335 ("Internal / Test users") is an exact match on this person
# property. It matches only when the property is set. The value has to be
# JSON boolean true — the string "true" is a different value, and false is
# not sent for everyone else.
_INTERNAL_OR_TEST_USER: bool = True


def set_internal_or_test_person(distinct_id: str) -> bool:
    """Set ``$internal_or_test_user`` on the person. Never raises.

    Signup capture forces ``$process_person_profile`` off, so this is its
    own ``$set`` and person processing stays on. The body is boolean true
    and the numeric distinct id — no address and no domain.
    """
    try:
        if not isinstance(distinct_id, str):
            return False
        cleaned = distinct_id.strip()
        if not cleaned or "@" in cleaned:
            return False
        key = _api_key()
        if not key:
            return False
        # bool, not str. json.dumps emits `true`, which is what the cohort matches.
        value: bool = _INTERNAL_OR_TEST_USER
        if type(value) is not bool or value is not True:
            return False
        payload = {
            "api_key": key,
            "event": "$set",
            "distinct_id": cleaned,
            "properties": {
                "$lib": "founderconsole-server",
                "$process_person_profile": True,
                "$set": {"$internal_or_test_user": value},
            },
        }
        return _post(payload, "$set")
    except Exception:
        logger.exception("[posthog] could not set internal-user flag")
        return False


def sync_internal_or_test_person(
    user_id: int,
    email: Optional[str] = None,
    *,
    is_platform_admin: bool = False,
    is_master: bool = False,
) -> bool:
    """Flag an internal or test account. A normal founder sends nothing.

    ``email`` is classified here and is not forwarded. Returns True only
    when a ``$set`` was handed to the network.
    """
    try:
        if not is_internal_or_test_account(
            email,
            is_platform_admin=is_platform_admin,
            is_master=is_master,
        ):
            return False
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return False
        if uid <= 0:
            return False
        return set_internal_or_test_person(user_distinct_id(uid))
    except Exception:
        logger.exception("[posthog] could not flag internal or test user")
        return False


def lead_distinct_id(email: str) -> str:
    """Stable fallback when the browser distinct_id was not sent.

    Hash, not the address. Same input with different case or surrounding
    space maps to one id.
    """
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:32]
    return f"lead:{digest}"


# Account ids are decimal (browser identify sends String(userId)) or the old
# server form user:<digits>. Neither is an anonymous browser id.
_USER_SCOPED_ID = re.compile(r"^(?:user:)?\d+$", re.IGNORECASE)


def _numeric_user_id(value: str) -> Optional[int]:
    if not _USER_SCOPED_ID.fullmatch(value):
        return None
    digits = value.split(":", 1)[1] if ":" in value else value
    try:
        return int(digits)
    except ValueError:
        return None


def _user_id_exists(user_id: int) -> bool:
    """True when this primary key is a user, or when that cannot be checked.

    An alias of an id we could not prove is free is refused. Anonymous browser
    ids never reach this lookup.
    """
    try:
        from server.core.db import SessionLocal
        from server.models.user import User

        db = SessionLocal()
        try:
            return db.query(User.id).filter(User.id == int(user_id)).first() is not None
        finally:
            db.close()
    except Exception:
        logger.warning("[posthog] could not check distinct id %s against users; refusing it", user_id)
        return True


def sanitize_distinct_id(value: object) -> Optional[str]:
    """Accept an anonymous browser distinct_id.

    Reject blanks, emails, over-long ids, all-digit ids, ``user:<digits>``,
    and any string that is an existing user's id. An invalid value becomes
    None so the caller can fall back. It must not fail the lead or signup.
    """
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > _MAX_DISTINCT_ID:
        return None
    if "@" in cleaned:
        return None
    # optin: is minted here for a lead with no browser id. A client who sends
    # that prefix did not receive it from us, and it must not be treated as
    # their browser distinct_id or later aliased onto an account.
    if cleaned.lower().startswith("optin:"):
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        return None
    user_id = _numeric_user_id(cleaned)
    if user_id is not None:
        # All-digit and user:<digits> are account ids. When that row exists,
        # the string belongs to someone else and must not be aliased here.
        _user_id_exists(user_id)
        return None
    return cleaned


def _account_distinct_id(value: object) -> Optional[str]:
    """The canonical id browser identify uses: the decimal user id."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned.isdigit() or len(cleaned) > 20:
        return None
    return cleaned


# Sign-in schedules this after the token is returned. A hung PostHog must
# not hold a worker. Two seconds is the cap; failures are logged and dropped.
_POST_TIMEOUT_SECONDS = 2


def _post(payload: dict, event_name: str) -> bool:
    try:
        req = urllib.request.Request(
            f"{_host()}/capture/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_POST_TIMEOUT_SECONDS) as resp:
            status = getattr(resp, "status", 200)
            return 200 <= int(status) < 300
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        logger.exception("[posthog] capture failed for %s", event_name)
        return False
    except Exception:
        logger.exception("[posthog] capture failed for %s", event_name)
        return False


def capture(
    event: str,
    distinct_id: str,
    properties: Optional[Mapping[str, Any]] = None,
) -> bool:
    """POST one event to /capture/. Returns True on 2xx. Never raises."""
    key = _api_key()
    if not key or not event or not distinct_id:
        return False

    payload = {
        "api_key": key,
        "event": event,
        "distinct_id": distinct_id,
        "properties": {
            "$lib": "founderconsole-server",
            # Do not create a person from the event itself. Alias and the
            # browser identify() call own person merges. An event whose
            # distinct_id already belongs to a person still lands on them.
            "$process_person_profile": False,
            **dict(properties or {}),
        },
    }
    return _post(payload, event)


def alias(*, previous_id: str, distinct_id: str) -> bool:
    """Merge previous_id into distinct_id via $create_alias. Never raises.

    Capture API: the event distinct_id is the id being merged away, and
    properties.alias becomes the canonical id (the one browser identify uses).
    Person processing stays on so the merge is applied.
    """
    # A client-supplied optin: id is rejected before sanitize, so a later
    # change to the sanitizer cannot start merging those ids into accounts.
    if isinstance(previous_id, str) and previous_id.strip().lower().startswith("optin:"):
        return False
    previous = sanitize_distinct_id(previous_id)
    # The canonical id is the account, which is numeric. The anonymous-only
    # sanitizer would reject it.
    canonical = _account_distinct_id(distinct_id)
    if not previous or not canonical or previous == canonical:
        return False
    key = _api_key()
    if not key:
        return False
    payload = {
        "api_key": key,
        "event": "$create_alias",
        "distinct_id": previous,
        "properties": {
            "alias": canonical,
            "$lib": "founderconsole-server",
        },
    }
    return _post(payload, "$create_alias")
