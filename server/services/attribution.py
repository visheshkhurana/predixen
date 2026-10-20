"""Campaign parameters sent with a lead or a signup.

Values are trimmed and capped at the leads column width. This module does
not read the request IP and does not backfill existing rows.
"""

from typing import Mapping, Optional

ATTRIBUTION_MAX_LENGTH = 200

ATTRIBUTION_KEYS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "fbclid",
    "gclid",
)

# Nullable columns added to leads. The other keys stay on the request and on
# the PostHog event; they are not columns.
LEAD_UTM_COLUMNS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
)


def clean_attribution_value(value: object, limit: int = ATTRIBUTION_MAX_LENGTH) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = "".join(ch for ch in value.strip() if ord(ch) >= 32 and ord(ch) != 127)
    if not text:
        return None
    return text[:limit]


def attribution_properties(values: Optional[Mapping[str, object]]) -> dict[str, str]:
    """Known keys only, dropped when empty. Unknown keys are ignored."""
    if not values:
        return {}
    cleaned: dict[str, str] = {}
    for key in ATTRIBUTION_KEYS:
        text = clean_attribution_value(values.get(key))
        if text:
            cleaned[key] = text
    return cleaned
