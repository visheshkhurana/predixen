"""
Cap Table Engine - Compute dilution and economics across fundraising scenarios.

This module provides pure functions for cap table calculations:
- Fully diluted share calculations
- Equity round modeling with option pool refresh
- SAFE/Convertible note conversion
- Ownership summary comparisons
- Exit waterfall analysis (participating/non-participating preferred)
- As-converted and as-exercised views
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class DilutionSummary:
    founder_dilution_percent: float
    new_investor_ownership_percent: float
    option_pool_post_percent: float
    pre_money_valuation: float
    post_money_valuation: float
    raise_amount: float
    price_per_share: float
    new_shares_issued: int
    warnings: List[str]


@dataclass
class ConversionOutput:
    shares_issued: int
    ownership_percent: float
    conversion_price: float
    discount_applied: bool
    cap_applied: bool
    effective_valuation: float


@dataclass
class OwnershipRow:
    holder: str
    holder_type: str
    shares_before: int
    percent_before: float
    shares_after: int
    percent_after: float
    dilution_percent: float


def compute_fully_diluted(cap_table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute fully diluted share counts and ownership percentages.
    
    Args:
        cap_table: Canonical cap table JSON structure
        
    Returns:
        Dictionary with total shares and ownership breakdown
    """
    total_shares = 0
    breakdown = []
    
    common = cap_table.get("common", [])
    for holder in common:
        shares = holder.get("shares", 0)
        total_shares += shares
        breakdown.append({
            "holder": holder.get("holder", "Unknown"),
            "type": "common",
            "shares": shares,
            "percent": 0.0
        })
    
    preferred = cap_table.get("preferred", [])
    for holder in preferred:
        shares = holder.get("shares", 0)
        total_shares += shares
        breakdown.append({
            "holder": holder.get("holder", "Unknown"),
            "type": "preferred",
            "series": holder.get("series", ""),
            "shares": shares,
            "percent": 0.0,
            "liquidation_pref": holder.get("liquidation_pref", "1x non-participating")
        })
    
    options = cap_table.get("options", {})
    pool_percent = options.get("pool_percent", 0.0)
    allocated_percent = options.get("allocated_percent", 0.0)
    
    if pool_percent > 0 and total_shares > 0:
        pool_shares = int(total_shares * pool_percent / (100 - pool_percent))
        total_shares += pool_shares
        breakdown.append({
            "holder": "Option Pool (Unallocated)",
            "type": "options",
            "shares": int(pool_shares * (1 - allocated_percent / pool_percent)) if pool_percent > 0 else 0,
            "percent": 0.0
        })
        breakdown.append({
            "holder": "Option Pool (Allocated)",
            "type": "options",
            "shares": int(pool_shares * allocated_percent / pool_percent) if pool_percent > 0 else 0,
            "percent": 0.0
        })
    
    for item in breakdown:
        if total_shares > 0:
            item["percent"] = round((item["shares"] / total_shares) * 100, 2)
    
    notes = cap_table.get("notes", [])
    outstanding_notes = []
    for note in notes:
        outstanding_notes.append({
            "holder": note.get("holder", "Unknown"),
            "principal": note.get("principal", 0),
            "conversion_cap": note.get("conversion_cap"),
            "discount": note.get("discount", 0.0)
        })
    
    return {
        "fully_diluted_shares": total_shares,
        "breakdown": breakdown,
        "outstanding_notes": outstanding_notes,
        "option_pool_percent": pool_percent,
        "option_pool_allocated_percent": allocated_percent
    }


def apply_equity_round(
    cap_table: Dict[str, Any],
    pre_money: float,
    raise_amount: float,
    option_pool_refresh_percent: float = 0.0,
    new_investor_name: str = "New Investor"
) -> Tuple[Dict[str, Any], DilutionSummary]:
    """
    Apply an equity financing round to a cap table.
    
    The option pool refresh is applied BEFORE the new investment (as is standard).
    This means founders bear the dilution from the option pool expansion.
    
    Args:
        cap_table: Current cap table JSON
        pre_money: Pre-money valuation
        raise_amount: Amount being raised
        option_pool_refresh_percent: Target option pool % post-money (0-100)
        new_investor_name: Name for the new investor entry
        
    Returns:
        Tuple of (updated_cap_table, dilution_summary)
    """
    warnings = []
    updated_cap_table = deepcopy(cap_table)
    
    before_fd = compute_fully_diluted(cap_table)
    total_shares_before = before_fd["fully_diluted_shares"]
    
    if total_shares_before == 0:
        total_shares_before = 10000000
        updated_cap_table["common"] = [{"holder": "Founders", "shares": total_shares_before, "percent": 100.0}]
    
    current_pool_percent = before_fd.get("option_pool_percent", 0.0)
    
    post_money = pre_money + raise_amount
    
    new_investor_percent = (raise_amount / post_money) * 100
    
    pool_expansion_percent = 0.0
    if option_pool_refresh_percent > current_pool_percent:
        pool_expansion_percent = option_pool_refresh_percent - current_pool_percent
        
        if pool_expansion_percent > 15:
            warnings.append(f"Option pool refresh of {pool_expansion_percent:.1f}% is unusually high (typical: 5-10%)")
    
    founders_pre_dilution_percent = 100 - current_pool_percent
    
    remaining_for_founders = 100 - new_investor_percent - option_pool_refresh_percent
    founder_dilution = founders_pre_dilution_percent - remaining_for_founders
    
    price_per_share = pre_money / total_shares_before if total_shares_before > 0 else 0
    new_shares_for_investor = int(raise_amount / price_per_share) if price_per_share > 0 else 0
    
    total_shares_post = total_shares_before + new_shares_for_investor
    
    if option_pool_refresh_percent > current_pool_percent:
        pool_shares_needed = int(total_shares_post * option_pool_refresh_percent / 100)
        current_pool_shares = int(total_shares_before * current_pool_percent / 100)
        additional_pool_shares = pool_shares_needed - current_pool_shares
        total_shares_post += additional_pool_shares
    
    scale_factor = total_shares_before / total_shares_post if total_shares_post > 0 else 1
    
    for holder in updated_cap_table.get("common", []):
        holder["shares"] = int(holder["shares"])
        holder["percent"] = round((holder["shares"] / total_shares_post) * 100, 2)
    
    for holder in updated_cap_table.get("preferred", []):
        holder["shares"] = int(holder["shares"])
        holder["percent"] = round((holder["shares"] / total_shares_post) * 100, 2)
    
    new_investor = {
        "series": new_investor_name,
        "holder": new_investor_name,
        "shares": new_shares_for_investor,
        "percent": round(new_investor_percent, 2),
        "liquidation_pref": "1x non-participating"
    }
    
    if "preferred" not in updated_cap_table:
        updated_cap_table["preferred"] = []
    updated_cap_table["preferred"].append(new_investor)
    
    updated_cap_table["options"] = {
        "pool_percent": option_pool_refresh_percent if option_pool_refresh_percent > 0 else current_pool_percent,
        "allocated_percent": updated_cap_table.get("options", {}).get("allocated_percent", 0.0)
    }
    
    updated_cap_table["fully_diluted_shares"] = total_shares_post
    
    summary = DilutionSummary(
        founder_dilution_percent=round(founder_dilution, 2),
        new_investor_ownership_percent=round(new_investor_percent, 2),
        option_pool_post_percent=round(option_pool_refresh_percent if option_pool_refresh_percent > 0 else current_pool_percent, 2),
        pre_money_valuation=pre_money,
        post_money_valuation=post_money,
        raise_amount=raise_amount,
        price_per_share=round(price_per_share, 4),
        new_shares_issued=new_shares_for_investor,
        warnings=warnings
    )
    
    return updated_cap_table, summary


def apply_safe_or_note(
    cap_table: Dict[str, Any],
    principal: float,
    cap: Optional[float],
    discount: float,
    next_round_pre_money: float,
    holder_name: str = "SAFE Holder"
) -> Tuple[Dict[str, Any], ConversionOutput]:
    """
    Convert a SAFE or convertible note into equity at a priced round.
    
    Args:
        cap_table: Current cap table JSON
        principal: Amount invested in SAFE/note
        cap: Valuation cap (None for uncapped)
        discount: Discount rate (0.0-1.0, e.g., 0.2 for 20% discount)
        next_round_pre_money: Pre-money valuation of the converting round
        holder_name: Name for the converting holder
        
    Returns:
        Tuple of (updated_cap_table, conversion_output)
    """
    updated_cap_table = deepcopy(cap_table)
    
    before_fd = compute_fully_diluted(cap_table)
    total_shares_before = before_fd["fully_diluted_shares"]
    
    if total_shares_before == 0:
        total_shares_before = 10000000
    
    discount_price = next_round_pre_money * (1 - discount) / total_shares_before
    
    cap_applied = False
    discount_applied = False
    
    if cap is not None:
        cap_price = cap / total_shares_before
        if cap_price < discount_price:
            conversion_price = cap_price
            cap_applied = True
            effective_valuation = cap
        else:
            conversion_price = discount_price
            discount_applied = True
            effective_valuation = next_round_pre_money * (1 - discount)
    else:
        conversion_price = discount_price
        discount_applied = True
        effective_valuation = next_round_pre_money * (1 - discount)
    
    shares_issued = int(principal / conversion_price) if conversion_price > 0 else 0
    
    total_shares_after = total_shares_before + shares_issued
    ownership_percent = (shares_issued / total_shares_after * 100) if total_shares_after > 0 else 0
    
    new_preferred = {
        "series": f"SAFE Conversion - {holder_name}",
        "holder": holder_name,
        "shares": shares_issued,
        "percent": round(ownership_percent, 2),
        "liquidation_pref": "1x non-participating"
    }
    
    if "preferred" not in updated_cap_table:
        updated_cap_table["preferred"] = []
    updated_cap_table["preferred"].append(new_preferred)
    
    updated_cap_table["notes"] = [
        n for n in updated_cap_table.get("notes", [])
        if n.get("holder") != holder_name
    ]
    
    for holder in updated_cap_table.get("common", []):
        holder["percent"] = round((holder["shares"] / total_shares_after) * 100, 2)
    for holder in updated_cap_table.get("preferred", []):
        holder["percent"] = round((holder["shares"] / total_shares_after) * 100, 2)
    
    updated_cap_table["fully_diluted_shares"] = total_shares_after
    
    output = ConversionOutput(
        shares_issued=shares_issued,
        ownership_percent=round(ownership_percent, 2),
        conversion_price=round(conversion_price, 4),
        discount_applied=discount_applied,
        cap_applied=cap_applied,
        effective_valuation=effective_valuation
    )
    
    return updated_cap_table, output


def compute_ownership_summary(
    before: Dict[str, Any],
    after: Dict[str, Any]
) -> List[OwnershipRow]:
    """
    Compare ownership before and after a transaction.
    
    Args:
        before: Cap table before the transaction
        after: Cap table after the transaction
        
    Returns:
        List of OwnershipRow showing changes for each holder
    """
    before_fd = compute_fully_diluted(before)
    after_fd = compute_fully_diluted(after)
    
    before_map = {}
    for item in before_fd["breakdown"]:
        key = (item["holder"], item["type"])
        before_map[key] = item
    
    after_map = {}
    for item in after_fd["breakdown"]:
        key = (item["holder"], item["type"])
        after_map[key] = item
    
    all_keys = set(before_map.keys()) | set(after_map.keys())
    
    rows = []
    for key in sorted(all_keys):
        holder, holder_type = key
        
        before_item = before_map.get(key, {"shares": 0, "percent": 0.0})
        after_item = after_map.get(key, {"shares": 0, "percent": 0.0})
        
        shares_before = before_item.get("shares", 0)
        percent_before = before_item.get("percent", 0.0)
        shares_after = after_item.get("shares", 0)
        percent_after = after_item.get("percent", 0.0)
        
        dilution = percent_before - percent_after
        
        rows.append(OwnershipRow(
            holder=holder,
            holder_type=holder_type,
            shares_before=shares_before,
            percent_before=round(percent_before, 2),
            shares_after=shares_after,
            percent_after=round(percent_after, 2),
            dilution_percent=round(dilution, 2)
        ))
    
    return rows


def simulate_round_scenarios(
    cap_table: Dict[str, Any],
    rounds: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Simulate multiple fundraising scenarios and compare outcomes.
    
    Args:
        cap_table: Starting cap table
        rounds: List of round configurations, each containing:
            - instrument: "equity", "safe", or "note"
            - raise: Amount being raised
            - For equity: pre_money, option_pool_refresh_percent
            - For SAFE/note: cap, discount, next_round_pre_money
            
    Returns:
        Comparison of all scenarios with key metrics
    """
    results = []
    
    for i, round_config in enumerate(rounds):
        instrument = round_config.get("instrument", "equity")
        raise_amount = round_config.get("raise", 0)
        
        if instrument == "equity":
            pre_money = round_config.get("pre_money", 0)
            pool_refresh = round_config.get("option_pool_refresh_percent", 0)
            
            updated_cap, summary = apply_equity_round(
                cap_table,
                pre_money=pre_money,
                raise_amount=raise_amount,
                option_pool_refresh_percent=pool_refresh,
                new_investor_name=f"Round {i+1} Investor"
            )
            
            results.append({
                "scenario_index": i,
                "instrument": instrument,
                "raise_amount": raise_amount,
                "pre_money": pre_money,
                "post_money": summary.post_money_valuation,
                "founder_dilution_percent": summary.founder_dilution_percent,
                "new_investor_ownership_percent": summary.new_investor_ownership_percent,
                "option_pool_post_percent": summary.option_pool_post_percent,
                "price_per_share": summary.price_per_share,
                "warnings": summary.warnings,
                "updated_cap_table": updated_cap
            })
            
        elif instrument in ("safe", "note"):
            cap = round_config.get("cap")
            discount = round_config.get("discount", 0.0)
            next_round_pre = round_config.get("next_round_pre_money", cap or raise_amount * 10)
            
            updated_cap, conversion = apply_safe_or_note(
                cap_table,
                principal=raise_amount,
                cap=cap,
                discount=discount,
                next_round_pre_money=next_round_pre,
                holder_name=f"SAFE Holder {i+1}"
            )
            
            results.append({
                "scenario_index": i,
                "instrument": instrument,
                "raise_amount": raise_amount,
                "cap": cap,
                "discount": discount,
                "shares_issued": conversion.shares_issued,
                "ownership_percent": conversion.ownership_percent,
                "conversion_price": conversion.conversion_price,
                "cap_applied": conversion.cap_applied,
                "discount_applied": conversion.discount_applied,
                "effective_valuation": conversion.effective_valuation,
                "updated_cap_table": updated_cap
            })
    
    best_for_founders = None
    worst_for_founders = None
    
    equity_results = [r for r in results if r["instrument"] == "equity"]
    if equity_results:
        best_for_founders = min(equity_results, key=lambda x: x["founder_dilution_percent"])
        worst_for_founders = max(equity_results, key=lambda x: x["founder_dilution_percent"])
    
    return {
        "scenarios": results,
        "best_for_founders": best_for_founders,
        "worst_for_founders": worst_for_founders,
        "total_scenarios": len(results)
    }


@dataclass
class WaterfallTranche:
    holder: str
    share_class: str
    series: str
    shares: float
    payout: float
    payout_percent: float
    method: str


@dataclass
class WaterfallResult:
    exit_value: float
    total_distributed: float
    tranches: List[WaterfallTranche]
    common_payout_per_share: float
    preferred_total: float
    common_total: float
    remaining: float


def run_waterfall(
    exit_value: float,
    cap_table: Dict[str, Any],
    scenarios: Optional[List[Dict[str, Any]]] = None
) -> WaterfallResult:
    """
    Run a liquidation preference waterfall analysis.

    The waterfall proceeds in order:
    1. Return preferences by seniority (highest seniority first)
    2. Participation for participating preferred (with optional caps)
    3. Remaining proceeds to common shareholders

    Non-participating preferred holders choose the better of:
    - Their liquidation preference, OR
    - Converting to common and sharing pro-rata

    Args:
        exit_value: Total exit proceeds to distribute
        cap_table: Cap table with holdings including liquidation preference fields
        scenarios: Optional scenario overrides

    Returns:
        WaterfallResult with per-tranche payouts
    """
    remaining = exit_value
    tranches = []

    holdings = cap_table.get("holdings", [])
    preferred_holdings = [h for h in holdings if h.get("share_class") == "preferred"]
    common_holdings = [h for h in holdings if h.get("share_class") == "common"]

    total_common_shares = sum(h.get("shares", 0) for h in common_holdings)
    total_preferred_shares = sum(h.get("shares", 0) for h in preferred_holdings)
    total_all_shares = total_common_shares + total_preferred_shares

    seniority_groups = {}
    for h in preferred_holdings:
        sen = h.get("seniority", 1)
        if sen not in seniority_groups:
            seniority_groups[sen] = []
        seniority_groups[sen].append(h)

    preferred_payouts = {}
    participating_holders = []

    for seniority_level in sorted(seniority_groups.keys(), reverse=True):
        group = seniority_groups[seniority_level]
        for h in group:
            holder = h.get("holder", "Unknown")
            shares = h.get("shares", 0)
            pps = h.get("price_per_share", 0) or 0
            liq_mult = h.get("liquidation_preference_multiple", 1.0) or 1.0
            is_participating = h.get("is_participating", False)

            preference_amount = shares * pps * liq_mult

            if is_participating:
                payout = min(preference_amount, remaining)
                remaining -= payout
                preferred_payouts[holder] = payout
                participating_holders.append(h)
                tranches.append(WaterfallTranche(
                    holder=holder,
                    share_class="preferred",
                    series=h.get("series", ""),
                    shares=shares,
                    payout=payout,
                    payout_percent=round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                    method="liquidation_preference"
                ))
            else:
                as_converted_shares = shares
                as_converted_payout = (as_converted_shares / total_all_shares * exit_value) if total_all_shares > 0 else 0

                if preference_amount >= as_converted_payout:
                    payout = min(preference_amount, remaining)
                    remaining -= payout
                    preferred_payouts[holder] = payout
                    tranches.append(WaterfallTranche(
                        holder=holder,
                        share_class="preferred",
                        series=h.get("series", ""),
                        shares=shares,
                        payout=payout,
                        payout_percent=round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                        method="liquidation_preference"
                    ))
                else:
                    payout = min(as_converted_payout, remaining)
                    remaining -= payout
                    preferred_payouts[holder] = payout
                    tranches.append(WaterfallTranche(
                        holder=holder,
                        share_class="preferred",
                        series=h.get("series", ""),
                        shares=shares,
                        payout=payout,
                        payout_percent=round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                        method="as_converted"
                    ))

    if remaining > 0 and participating_holders:
        participating_shares = sum(h.get("shares", 0) for h in participating_holders)
        shares_for_participation = total_common_shares + participating_shares

        if shares_for_participation > 0:
            for h in participating_holders:
                holder = h.get("holder", "Unknown")
                shares = h.get("shares", 0)
                participation_cap = h.get("participation_cap")

                pro_rata_share = (shares / shares_for_participation) * remaining
                if participation_cap is not None:
                    max_participation = participation_cap * shares * (h.get("price_per_share", 0) or 0)
                    already_received = preferred_payouts.get(holder, 0)
                    max_additional = max(0, max_participation - already_received)
                    pro_rata_share = min(pro_rata_share, max_additional)

                preferred_payouts[holder] = preferred_payouts.get(holder, 0) + pro_rata_share
                for t in tranches:
                    if t.holder == holder:
                        t.payout += pro_rata_share
                        t.payout_percent = round((t.payout / exit_value) * 100, 2) if exit_value > 0 else 0
                        t.method = "participating"
                        break

            total_participation = sum(
                (h.get("shares", 0) / shares_for_participation) * remaining
                for h in participating_holders
            )
            remaining -= min(total_participation, remaining)

    common_payout_per_share = (remaining / total_common_shares) if total_common_shares > 0 else 0

    for h in common_holdings:
        holder = h.get("holder", "Unknown")
        shares = h.get("shares", 0)
        payout = shares * common_payout_per_share

        tranches.append(WaterfallTranche(
            holder=holder,
            share_class="common",
            series="common",
            shares=shares,
            payout=round(payout, 2),
            payout_percent=round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
            method="pro_rata"
        ))

    common_total_payout = common_payout_per_share * total_common_shares
    remaining_after = remaining - common_total_payout

    preferred_total = sum(preferred_payouts.values())

    return WaterfallResult(
        exit_value=exit_value,
        total_distributed=round(exit_value - max(0, remaining_after), 2),
        tranches=tranches,
        common_payout_per_share=round(common_payout_per_share, 4),
        preferred_total=round(preferred_total, 2),
        common_total=round(common_total_payout, 2),
        remaining=round(max(0, remaining_after), 2)
    )


def calculate_as_converted(cap_table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate as-converted ownership by converting all preferred shares to common equivalent.

    This treats all preferred shares as if they had been converted to common stock,
    showing what ownership would look like on an as-converted basis.

    Args:
        cap_table: Cap table with holdings data

    Returns:
        Dictionary with as-converted breakdown and totals
    """
    holdings = cap_table.get("holdings", [])
    common_holdings = [h for h in holdings if h.get("share_class") == "common"]
    preferred_holdings = [h for h in holdings if h.get("share_class") == "preferred"]

    converted = []

    for h in common_holdings:
        converted.append({
            "holder": h.get("holder", "Unknown"),
            "original_class": "common",
            "shares": h.get("shares", 0),
            "conversion_ratio": 1.0,
            "converted_shares": h.get("shares", 0),
        })

    for h in preferred_holdings:
        conversion_ratio = h.get("conversion_ratio", 1.0)
        shares = h.get("shares", 0)
        converted_shares = shares * conversion_ratio
        converted.append({
            "holder": h.get("holder", "Unknown"),
            "original_class": "preferred",
            "series": h.get("series", ""),
            "shares": shares,
            "conversion_ratio": conversion_ratio,
            "converted_shares": converted_shares,
        })

    total_converted = sum(c["converted_shares"] for c in converted)

    for c in converted:
        c["percent"] = round((c["converted_shares"] / total_converted) * 100, 2) if total_converted > 0 else 0

    return {
        "total_as_converted_shares": total_converted,
        "breakdown": converted,
    }


def calculate_as_exercised(cap_table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate as-exercised ownership including all vested options as shares.

    This shows what ownership would look like if all vested (but unexercised) options
    were exercised and converted to common shares.

    Args:
        cap_table: Cap table with holdings and option grants data

    Returns:
        Dictionary with as-exercised breakdown and totals
    """
    holdings = cap_table.get("holdings", [])
    options = cap_table.get("option_grants", [])

    exercised = []

    for h in holdings:
        exercised.append({
            "holder": h.get("holder", "Unknown"),
            "type": h.get("share_class", "common"),
            "series": h.get("series", ""),
            "shares": h.get("shares", 0),
            "source": "equity",
        })

    for og in options:
        status = og.get("status", "active")
        if status not in ("active", "draft"):
            continue
        vested = og.get("shares_vested", 0)
        exercised_already = og.get("shares_exercised", 0)
        exercisable = max(0, vested - exercised_already)

        if exercisable > 0:
            exercised.append({
                "holder": og.get("holder", og.get("shareholder_name", "Unknown")),
                "type": "common (from options)",
                "series": "",
                "shares": exercisable,
                "source": "option_exercise",
                "exercise_price": og.get("exercise_price", 0),
                "grant_type": og.get("grant_type", ""),
            })

    total_shares = sum(e["shares"] for e in exercised)

    for e in exercised:
        e["percent"] = round((e["shares"] / total_shares) * 100, 2) if total_shares > 0 else 0

    return {
        "total_as_exercised_shares": total_shares,
        "breakdown": exercised,
    }
