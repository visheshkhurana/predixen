"""Best-effort server-side PostHog capture and alias.

There is no PostHog Python SDK in this repo. Browser identify
(client/src/lib/posthog.ts identifyUser) uses String(userId). Server events
for a logged-in user must use that same distinct_id. Signup also sends
$create_alias so a pre-signup lead or anonymous id joins that person.

A failed send must never raise — the product action already succeeded by the
time this runs, and a visitor cannot do anything with a telemetry error.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
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


def lead_distinct_id(email: str) -> str:
    """Stable fallback when the browser distinct_id was not sent.

    Hash, not the address. Same input with different case or surrounding
    space maps to one id.
    """
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:32]
    return f"lead:{digest}"


def sanitize_distinct_id(value: object) -> Optional[str]:
    """Accept a browser distinct_id. Reject blanks, emails, and over-long ids.

    An invalid value becomes None so the caller can fall back. It must not
    fail the lead or signup request.
    """
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > _MAX_DISTINCT_ID:
        return None
    if "@" in cleaned:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        return None
    return cleaned


def _post(payload: dict, event_name: str) -> bool:
    try:
        req = urllib.request.Request(
            f"{_host()}/capture/",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
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
    previous = sanitize_distinct_id(previous_id)
    canonical = sanitize_distinct_id(distinct_id)
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
