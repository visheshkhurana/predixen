"""Minor-unit money helpers shared by billing connectors.

Stripe, Chargebee and Recurly-style APIs send integer amounts in the
currency's smallest unit. For zero-decimal currencies that unit is the whole
currency, so dividing by 100 would make JPY 100x too small.
https://docs.stripe.com/currencies#zero-decimal
"""

from __future__ import annotations

from typing import Any, Optional

ZERO_DECIMAL_CURRENCIES = frozenset({
    "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf",
    "ugx", "vnd", "vuv", "xaf", "xof", "xpf",
})


def to_major(amount: Any, currency: Optional[str]) -> float:
    """Minor units -> major units for `currency`."""
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        return 0.0
    if (currency or "").lower() in ZERO_DECIMAL_CURRENCIES:
        return value
    return value / 100.0
