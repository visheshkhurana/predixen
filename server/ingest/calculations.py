"""
Centralized financial calculations module.
All burn/runway formulas and metric computations should use these functions.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class BurnStatus(str, Enum):
    BURNING = "burning"
    PROFITABLE = "profitable"
    SUSTAINABLE = "sustainable"
    BREAKEVEN = "breakeven"


@dataclass
class BaselineMetrics:
    """Computed baseline metrics from financial data."""
    revenue: float
    total_expenses: float
    net_burn: float
    burn_status: BurnStatus
    runway_months: Optional[float]
    cash_on_hand: Optional[float]
    growth_rate_mom: Optional[float]
    
    expense_breakdown: Optional[Dict[str, float]] = None
    warnings: Optional[List[str]] = None


def calculate_net_burn(total_expenses: float, revenue: float) -> float:
    """
    Calculate net burn.
    
    Formula: net_burn = total_expenses - revenue
    
    - Positive net_burn = burning cash
    - Negative net_burn = profitable/surplus
    - Zero = breakeven
    
    IMPORTANT: total_expenses should already be positive (normalized).
    """
    return total_expenses - revenue


def calculate_runway_months(net_burn: float, cash_on_hand: Optional[float]) -> Optional[float]:
    """
    Calculate runway in months.
    
    - If net_burn <= 0: "Sustainable" (return None to indicate infinite)
    - If net_burn > 0 and cash_on_hand is known: runway = cash_on_hand / net_burn
    - If net_burn > 0 and cash_on_hand is None: return None (unknown)
    """
    if net_burn <= 0:
        return None
    
    if cash_on_hand is None:
        return None
    
    if cash_on_hand <= 0:
        return 0.0
    
    return cash_on_hand / net_burn


def determine_burn_status(net_burn: float) -> BurnStatus:
    """Determine the burn status based on net burn value."""
    if net_burn < -0.01:
        return BurnStatus.PROFITABLE
    elif net_burn > 0.01:
        return BurnStatus.BURNING
    else:
        return BurnStatus.BREAKEVEN


DEFAULT_RUNWAY_ASSUMPTION_MONTHS = 12
DEFAULT_PROFITABLE_CASH_BALANCE = 2_000_000  # $2 million USD


def estimate_cash_on_hand(
    net_burn: float, 
    cash_on_hand: Optional[float] = None
) -> tuple[Optional[float], bool]:
    """
    Estimate cash on hand when not provided.
    
    Rules:
    - If cash_on_hand is already provided, use it as-is
    - If company is burning cash (net_burn > 0), assume 12 months runway: cash = burn * 12
    - If company is profitable/breakeven (net_burn <= 0), assume $2 million USD balance
    
    Returns:
        Tuple of (estimated_cash, is_estimated) where is_estimated is True if we made an assumption
    """
    if cash_on_hand is not None:
        return cash_on_hand, False
    
    if net_burn > 0:
        estimated = net_burn * DEFAULT_RUNWAY_ASSUMPTION_MONTHS
        return estimated, True
    else:
        return DEFAULT_PROFITABLE_CASH_BALANCE, True


def format_runway_display(runway_months: Optional[float], burn_status: BurnStatus) -> str:
    """Format runway for display in the UI."""
    if burn_status == BurnStatus.PROFITABLE:
        return "Sustainable"
    
    if burn_status == BurnStatus.BREAKEVEN:
        return "Sustainable"
    
    if runway_months is None:
        return "Unknown (missing cash data)"
    
    if runway_months <= 0:
        return "0 months"
    
    if runway_months >= 36:
        return "36+ months"
    
    return f"{runway_months:.1f} months"


def format_burn_display(net_burn: float) -> Dict[str, Any]:
    """
    Format burn for display. Never show negative expenses.
    
    Returns dict with:
    - label: "Monthly Burn" or "Monthly Surplus"
    - value: absolute value (always positive)
    - is_surplus: boolean
    """
    if net_burn < 0:
        return {
            'label': 'Monthly Surplus',
            'value': abs(net_burn),
            'is_surplus': True
        }
    elif net_burn > 0:
        return {
            'label': 'Monthly Burn',
            'value': net_burn,
            'is_surplus': False
        }
    else:
        return {
            'label': 'Breakeven',
            'value': 0,
            'is_surplus': False
        }


def compute_baseline_metrics(
    revenue: float,
    total_expenses: float,
    cash_on_hand: Optional[float] = None,
    growth_rate_mom: Optional[float] = None,
    expense_breakdown: Optional[Dict[str, float]] = None,
    auto_estimate_cash: bool = True
) -> BaselineMetrics:
    """
    Compute all baseline metrics from raw financial data.
    
    Args:
        revenue: Total revenue (should be positive)
        total_expenses: Total expenses (should be positive, normalized)
        cash_on_hand: Current cash balance (optional)
        growth_rate_mom: Month-over-month growth rate (optional)
        expense_breakdown: Dict with keys like 'cogs', 'marketing', 'payroll', 'operating'
        auto_estimate_cash: If True, estimate cash when not provided (default True)
    
    Returns:
        BaselineMetrics object with all computed values
    """
    revenue = abs(revenue)
    total_expenses = abs(total_expenses)
    
    net_burn = calculate_net_burn(total_expenses, revenue)
    burn_status = determine_burn_status(net_burn)
    
    warnings = []
    
    # Estimate cash on hand if not provided
    effective_cash = cash_on_hand
    cash_was_estimated = False
    
    if auto_estimate_cash:
        effective_cash, cash_was_estimated = estimate_cash_on_hand(net_burn, cash_on_hand)
        
        if cash_was_estimated:
            if net_burn > 0:
                warnings.append(f"Cash on hand estimated assuming 12-month runway (${effective_cash:,.0f})")
            else:
                warnings.append(f"Cash on hand defaulted to $2 million (profitable company)")
    elif cash_on_hand is None and net_burn > 0:
        warnings.append("Cash on hand is missing; runway cannot be calculated")
    
    runway_months = calculate_runway_months(net_burn, effective_cash)
    
    if revenue == 0 and total_expenses > 0:
        warnings.append("No revenue recorded; all expenses contribute to burn")
    
    return BaselineMetrics(
        revenue=revenue,
        total_expenses=total_expenses,
        net_burn=net_burn,
        burn_status=burn_status,
        runway_months=runway_months,
        cash_on_hand=effective_cash,
        growth_rate_mom=growth_rate_mom,
        expense_breakdown=expense_breakdown,
        warnings=warnings if warnings else None
    )


def aggregate_expense_breakdown(rows: List[Dict[str, Any]], period: str) -> Dict[str, float]:
    """
    Aggregate expense rows by bucket for a specific period.
    
    Args:
        rows: List of classified row dicts
        period: The period key to aggregate
    
    Returns:
        Dict with expense bucket totals
    """
    breakdown = {
        'cogs': 0.0,
        'marketing': 0.0,
        'payroll': 0.0,
        'operating': 0.0
    }
    
    for row in rows:
        if row.get('classification') != 'expense':
            continue
        if not row.get('include_in_totals', True):
            continue
        
        values = row.get('values', {})
        period_data = values.get(period, {})
        
        value = period_data.get('normalized', 0) if isinstance(period_data, dict) else period_data
        if not isinstance(value, (int, float)):
            continue
        
        bucket = row.get('expense_bucket', 'operating') or 'operating'
        breakdown[bucket] = breakdown.get(bucket, 0) + abs(value)
    
    return breakdown


def calculate_total_revenue(rows: List[Dict[str, Any]], period: str) -> float:
    """Calculate total revenue for a period from classified rows."""
    total = 0.0
    
    for row in rows:
        if row.get('classification') != 'revenue':
            continue
        if not row.get('include_in_totals', True):
            continue
        
        values = row.get('values', {})
        period_data = values.get(period, {})
        
        value = period_data.get('normalized', 0) if isinstance(period_data, dict) else period_data
        if isinstance(value, (int, float)):
            total += abs(value)
    
    return total


def calculate_total_expenses(rows: List[Dict[str, Any]], period: str) -> float:
    """Calculate total expenses for a period from classified rows."""
    total = 0.0
    
    for row in rows:
        if row.get('classification') != 'expense':
            continue
        if not row.get('include_in_totals', True):
            continue
        
        values = row.get('values', {})
        period_data = values.get(period, {})
        
        value = period_data.get('normalized', 0) if isinstance(period_data, dict) else period_data
        if isinstance(value, (int, float)):
            total += abs(value)
    
    return total


def calculate_growth_rate(current_revenue: float, previous_revenue: float) -> Optional[float]:
    """Calculate month-over-month growth rate.
    
    Returns rate as a decimal (e.g., 0.10 for 10% growth).
    Capped at +/- 2.0 (200%) to prevent nonsensical projections.
    """
    if previous_revenue == 0:
        if current_revenue > 0:
            return 1.0
        return 0.0
    
    rate = (current_revenue - previous_revenue) / previous_revenue
    return max(-2.0, min(2.0, rate))


MAX_MONTHLY_GROWTH_RATE_PCT = 50.0


def safe_growth_rate_from_series(
    revenue_values: list,
) -> Optional[float]:
    """Compute growth rate from a list of revenue values.
    
    Returns None if fewer than 2 data points (cannot compute growth).
    Returns the average MoM growth rate as a percentage (e.g., 10.0 for 10%).
    Capped at MAX_MONTHLY_GROWTH_RATE_PCT to prevent projection overflow.
    """
    if len(revenue_values) < 2:
        return None
    
    rates = []
    for i in range(1, len(revenue_values)):
        prev = revenue_values[i - 1]
        curr = revenue_values[i]
        if prev and prev > 0:
            rate = (curr - prev) / prev
            rates.append(rate)
    
    if not rates:
        return None
    
    avg_rate = sum(rates) / len(rates)
    avg_pct = avg_rate * 100
    return max(-MAX_MONTHLY_GROWTH_RATE_PCT, min(MAX_MONTHLY_GROWTH_RATE_PCT, avg_pct))


def compute_3_month_average(rows: List[Dict[str, Any]], periods: List[str]) -> Dict[str, float]:
    """
    Compute 3-month rolling average for baseline metrics.
    
    Args:
        rows: Classified rows
        periods: List of period keys (last 3 months)
    
    Returns:
        Dict with averaged values
    """
    if len(periods) == 0:
        return {'revenue': 0, 'expenses': 0}
    
    total_revenue = sum(calculate_total_revenue(rows, p) for p in periods)
    total_expenses = sum(calculate_total_expenses(rows, p) for p in periods)
    
    n = len(periods)
    return {
        'revenue': total_revenue / n,
        'expenses': total_expenses / n
    }
