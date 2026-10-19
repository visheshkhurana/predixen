"""Turn a Termina report's extracted figures into stored cost lines.

The report gives revenue, some cost lines (COGS, opex, payroll) and a
headline net burn. Net burn is a *result* (costs - revenue), not a cost, so
storing it as ``other_costs`` counted it twice: burn $50K on opex $40K read
back as ~$90K+ of burn. Here ``other_costs`` only holds the costs the named
lines do not explain, so that ``cogs + opex + payroll + other_costs - revenue``
equals the extracted net burn.
"""
from typing import Dict, Optional


def termina_cost_lines(
    revenue: float,
    cogs: float,
    opex: float,
    payroll: float,
    net_burn: Optional[float],
) -> Dict[str, float]:
    revenue = float(revenue or 0)
    lines = {
        "cogs": max(0.0, float(cogs or 0)),
        "opex": max(0.0, float(opex or 0)),
        "payroll": max(0.0, float(payroll or 0)),
        "other_costs": 0.0,
    }
    if net_burn is None:
        return lines

    target_total = max(0.0, revenue + float(net_burn))
    named_total = lines["cogs"] + lines["opex"] + lines["payroll"]
    if target_total >= named_total:
        lines["other_costs"] = target_total - named_total
        return lines

    # The named lines exceed what the stated burn implies (e.g. COGS estimated
    # from a default margin that the opex figure already contains). Trust the
    # report's headline burn and trim the softest figures first.
    excess = named_total - target_total
    for key in ("cogs", "opex", "payroll"):
        cut = min(excess, lines[key])
        lines[key] -= cut
        excess -= cut
        if excess <= 0:
            break
    return lines
