"""One definition of gross-margin units for every money path.

FinancialRecord.gross_margin and the truth scan's ``gross_margin`` are
percentages (65.0 means 65%). Uploaded spreadsheets and some legacy rows hold a
fraction (0.65). The old guess, ``pct = gm if gm > 1 else gm * 100``, treated
every negative percentage as a fraction, so a -56% margin became -5600% on the
dashboard and was then clamped to +10% inside the simulations.

Rule: a value with magnitude at most 1 is a fraction; anything larger is
already a percentage. That keeps 0.65 -> 65% and -0.4 -> -40%, and leaves
-56 -> -56%. (A genuine |margin| <= 1% is indistinguishable from a fraction;
writers should store percentages so the guess only runs at the ingest edge.)
"""

from __future__ import annotations

from typing import Optional

# Gross margin can be deeply negative early on (COGS above revenue), so the
# floor is far below zero; the old floor of +10% simulated loss-making
# companies as profitable. The 95% ceiling is kept from HAG-179 as a deliberate
# conservative cap on the top end.
GROSS_MARGIN_MIN_PCT = -200.0
GROSS_MARGIN_MAX_PCT = 95.0


def gross_margin_pct(value) -> Optional[float]:
    """Normalise a gross margin given as a fraction or a percentage to a percentage."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v * 100.0 if abs(v) <= 1.0 else v


def clamp_gross_margin_pct(value_pct: float) -> float:
    """Bound a percentage margin for simulation without flipping its sign."""
    return max(GROSS_MARGIN_MIN_PCT, min(GROSS_MARGIN_MAX_PCT, float(value_pct)))
