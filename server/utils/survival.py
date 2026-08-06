"""Tolerant access to simulation survival probabilities.

The Monte Carlo engine (``server/simulate/simulation_engine.py``) emits survival
under the keys ``"6m"``, ``"12m"``, ``"18m"`` and ``"24m"``, as percentages in
0-100. Several consumers were written against key names that the engine has
never produced — ``"12_month"`` in ``server/api/copilot.py`` and
``server/copilot/business_context.py``, ``"probability_18m"`` in
``server/api/decisions.py``, ``"12_month"`` in ``server/api/metric_trends.py``.
Each of those reads silently returned ``None``/``"N/A"``, which is why the
copilot fell back to hardcoded constants and disagreed with the simulator that
was sitting right next to it on screen.

Read survival through these helpers rather than indexing the dict directly, so a
future key rename degrades to "still works" instead of "silently N/A".
"""

from typing import Any, Mapping, Optional

# Every spelling that has appeared in this codebase or its stored payloads,
# most-canonical first.
_ALIASES = {
    6: ("6m", "6_month", "probability_6m", "survival_6m", "month_6"),
    12: ("12m", "12_month", "probability_12m", "survival_12m", "month_12"),
    18: ("18m", "18_month", "probability_18m", "survival_18m", "month_18"),
    24: ("24m", "24_month", "probability_24m", "survival_24m", "month_24"),
}


def survival_pct(survival: Optional[Mapping[str, Any]], months: int) -> Optional[float]:
    """Return the survival probability at ``months`` as a percentage (0-100).

    Returns ``None`` when the simulation genuinely has no value for that
    horizon. Callers should say so rather than substituting a constant — a made
    up 65% is worse than an honest "not simulated yet".
    """
    if not survival or not isinstance(survival, Mapping):
        return None
    for key in _ALIASES.get(months, ()):
        value = survival.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        # Some older payloads stored fractions (0-1) rather than percentages.
        if 0.0 <= value <= 1.0 and key.startswith("probability"):
            value *= 100.0
        return round(value, 1)
    return None


def survival_summary(survival: Optional[Mapping[str, Any]]) -> dict:
    """The three horizons the copilot quotes, normalised. ``None`` = not simulated."""
    return {months: survival_pct(survival, months) for months in (12, 18, 24)}


def format_survival_line(survival: Optional[Mapping[str, Any]]) -> Optional[str]:
    """One prompt-ready line, or ``None`` if nothing has been simulated.

    Returning ``None`` matters: it lets the prompt builder omit the section
    entirely instead of shipping "12m=N/A 18m=N/A 24m=N/A", which the model
    reads as a real (bad) result.
    """
    values = survival_summary(survival)
    if all(v is None for v in values.values()):
        return None
    parts = [
        f"{months}m={values[months]:.1f}%" if values[months] is not None else f"{months}m=not simulated"
        for months in (12, 18, 24)
    ]
    return "  Survival probability: " + " ".join(parts)
