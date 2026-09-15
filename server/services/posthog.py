"""Best-effort server-side PostHog capture.

There is no PostHog Python SDK in this repo and no identify/init on the
server. The browser SDK in client/src/lib/posthog.ts is unchanged.

A failed send must never raise — lead capture already succeeded by the time
this runs, and a marketing visitor cannot do anything with a telemetry error.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# Same live project token the browser SDK ships. VITE_POSTHOG_KEY historically
# pointed at a nonexistent project, so we do not fall back to it.
_DEFAULT_KEY = "phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M"
_DEFAULT_HOST = "https://us.i.posthog.com"


def _api_key() -> str:
    return (
        os.environ.get("POSTHOG_KEY")
        or os.environ.get("POSTHOG_PROJECT_API_KEY")
        or _DEFAULT_KEY
    ).strip()


def _host() -> str:
    return (os.environ.get("POSTHOG_HOST") or _DEFAULT_HOST).rstrip("/")


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
            # Capture only — do not create or merge a person profile.
            "$process_person_profile": False,
            **dict(properties or {}),
        },
    }
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
        logger.exception("[posthog] capture failed for %s", event)
        return False
    except Exception:
        logger.exception("[posthog] capture failed for %s", event)
        return False
