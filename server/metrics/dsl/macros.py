"""
Metric DSL Macros - safe SQL macro expansions.
"""

from typing import Dict, Callable, Tuple, List
from enum import Enum


class MacroError(Exception):
    """Error in macro expansion."""
    pass


class GrainInterval(Enum):
    """SQL interval mappings for grain types."""
    DAILY = "1 day"
    WEEKLY = "1 week"
    MONTHLY = "1 month"


def time_bucket_macro(grain: str, timestamp_col: str) -> str:
    """
    Generate time bucket expression.
    
    Args:
        grain: Time grain (daily, weekly, monthly)
        timestamp_col: Column name for timestamp
        
    Returns:
        SQL expression for time bucketing
    """
    grain_lower = grain.lower()
    if grain_lower == "daily":
        return f"date_trunc('day', {timestamp_col})"
    elif grain_lower == "weekly":
        return f"date_trunc('week', {timestamp_col})"
    elif grain_lower == "monthly":
        return f"date_trunc('month', {timestamp_col})"
    else:
        raise MacroError(f"Unknown grain: {grain}")


def coalesce_macro(*args: str) -> str:
    """
    Generate COALESCE expression.
    
    Args:
        *args: Column names or values to coalesce
        
    Returns:
        SQL COALESCE expression
    """
    if not args:
        raise MacroError("coalesce requires at least one argument")
    return f"COALESCE({', '.join(args)})"


def to_number_macro(json_field: str) -> str:
    """
    Generate expression to extract number from JSON field.
    
    Args:
        json_field: JSON path expression
        
    Returns:
        SQL expression to extract as numeric
    """
    return f"CAST({json_field} AS NUMERIC)"


def lower_macro(text_col: str) -> str:
    """
    Generate LOWER expression.
    
    Args:
        text_col: Column or expression to lowercase
        
    Returns:
        SQL LOWER expression
    """
    return f"LOWER({text_col})"


def date_trunc_macro(part: str, timestamp_col: str) -> str:
    """
    Generate DATE_TRUNC expression.
    
    Args:
        part: Date part (day, week, month, year)
        timestamp_col: Timestamp column
        
    Returns:
        SQL DATE_TRUNC expression
    """
    valid_parts = {"day", "week", "month", "quarter", "year"}
    part_lower = part.lower().strip("'\"")
    if part_lower not in valid_parts:
        raise MacroError(f"Invalid date_trunc part: {part}. Valid: {valid_parts}")
    return f"date_trunc('{part_lower}', {timestamp_col})"


MACRO_REGISTRY: Dict[str, Callable] = {
    "time_bucket": time_bucket_macro,
    "coalesce": coalesce_macro,
    "to_number": to_number_macro,
    "lower": lower_macro,
    "date_trunc": date_trunc_macro,
}


def expand_macro(name: str, args: List[str]) -> str:
    """
    Expand a macro with given arguments.
    
    Args:
        name: Macro name
        args: List of arguments
        
    Returns:
        Expanded SQL expression
        
    Raises:
        MacroError: If macro is unknown or args invalid
    """
    name_lower = name.lower()
    if name_lower not in MACRO_REGISTRY:
        raise MacroError(f"Unknown macro: {name}")
    
    try:
        return MACRO_REGISTRY[name_lower](*args)
    except TypeError as e:
        raise MacroError(f"Macro {name} argument error: {e}")


def parse_macro_call(expr: str) -> Tuple[str, List[str]]:
    """
    Parse a macro call expression.
    
    Args:
        expr: Expression like "time_bucket(monthly, occurred_at)"
        
    Returns:
        Tuple of (macro_name, [args])
    """
    import re
    match = re.match(r'(\w+)\s*\(([^)]*)\)', expr.strip())
    if not match:
        raise MacroError(f"Invalid macro syntax: {expr}")
    
    name = match.group(1)
    args_str = match.group(2).strip()
    
    if not args_str:
        return name, []
    
    args = [a.strip() for a in args_str.split(',')]
    return name, args


def expand_expression(expr: str) -> str:
    """
    Expand all macros in an expression.
    
    Args:
        expr: Expression potentially containing macro calls
        
    Returns:
        Expression with macros expanded to SQL
    """
    import re
    
    pattern = r'\b(\w+)\s*\(([^)]*)\)'
    
    def replace_macro(match):
        name = match.group(1).lower()
        args_str = match.group(2).strip()
        
        if name not in MACRO_REGISTRY:
            return match.group(0)
        
        args = [a.strip() for a in args_str.split(',')] if args_str else []
        try:
            return expand_macro(name, args)
        except MacroError:
            return match.group(0)
    
    return re.sub(pattern, replace_macro, expr)
