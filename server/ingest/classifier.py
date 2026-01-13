"""
Row classification engine for financial data ingestion.
Classifies row labels as revenue, expense, derived, header, or other.
Handles sign convention detection and expense bucket mapping.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re


class Classification(str, Enum):
    REVENUE = "revenue"
    EXPENSE = "expense"
    DERIVED = "derived"
    HEADER = "header"
    OTHER = "other"


class ExpenseBucket(str, Enum):
    COGS = "cogs"
    MARKETING = "marketing"
    PAYROLL = "payroll"
    OPERATING = "operating"


class SignConvention(str, Enum):
    ACCOUNTING = "accounting"
    ALL_POSITIVE = "all_positive"
    MIXED = "mixed"


REVENUE_KEYWORDS = [
    "revenue", "revenues", "sales", "gmv", "bookings", "collections",
    "total revenue", "net revenue", "gross revenue", "subscription revenue",
    "recurring revenue", "mrr", "arr"
]

EXPENSE_KEYWORDS = [
    "expense", "expenses", "cost", "costs", "cogs", "opex", "payroll",
    "salary", "salaries", "wages", "marketing", "ads", "advertising",
    "rent", "hosting", "cloud", "logistics", "packaging", "commission",
    "payout", "contractor", "support", "payment processing", "fulfillment",
    "operating expenses", "total expenses", "other expenses"
]

DERIVED_KEYWORDS = [
    "gross profit", "operating income", "ebit", "ebitda", "margin",
    "rule of", "magic number", "ltv", "cac", "payback", "net income",
    "profit", "loss", "burn", "runway", "growth rate"
]

HEADER_EXACT_MATCHES = [
    "revenue", "cogs", "sales and marketing", "other opex",
    "gross profit", "operating income", "expenses", "operating expenses",
    "cost of goods sold", "cost of revenue"
]

MARKETING_BUCKET_KEYWORDS = [
    "marketing", "ads", "advertising", "acquisition", "growth", "brand",
    "performance", "ua", "user acquisition", "sales and marketing", "s&m"
]

PAYROLL_BUCKET_KEYWORDS = [
    "salary", "salaries", "payroll", "wages", "people", "contractor",
    "contractors", "benefits", "personnel", "staff", "employee", "employees",
    "compensation", "team"
]

COGS_BUCKET_KEYWORDS = [
    "cogs", "cost of goods", "cost of revenue", "payout", "commission",
    "payment processing", "fulfillment", "logistics", "packaging",
    "astrologer", "provider", "supplier", "vendor", "delivery"
]


@dataclass
class ClassifiedRow:
    """Result of classifying a row label."""
    label: str
    classification: Classification
    expense_bucket: Optional[ExpenseBucket]
    confidence: str
    is_header: bool
    has_children: bool
    parent_label: Optional[str]
    notes: List[str]


@dataclass
class ParsedRow:
    """A parsed row with hierarchy information."""
    index: int
    label: str
    indent_level: int
    values: Dict[str, float]
    parent_index: Optional[int]
    children_indices: List[int]


def normalize_label(label: str) -> str:
    """Normalize a label for matching."""
    if not label:
        return ""
    label = label.lower().strip()
    label = re.sub(r'\s+', ' ', label)
    label = re.sub(r'[^\w\s]', '', label)
    return label


def detect_indent_level(label: str) -> int:
    """Detect indentation level from leading whitespace or bullets."""
    if not label:
        return 0
    leading_spaces = len(label) - len(label.lstrip())
    indent = leading_spaces // 2
    if label.lstrip().startswith(('-', '•', '*', '·')):
        indent += 1
    return indent


def parse_rows_with_hierarchy(rows: List[Dict[str, Any]]) -> List[ParsedRow]:
    """Parse rows and detect parent-child relationships based on indentation."""
    parsed = []
    parent_stack: List[int] = []
    
    for idx, row in enumerate(rows):
        label = row.get('label', '') or ''
        values = row.get('values', {})
        
        indent = detect_indent_level(label)
        clean_label = label.strip().lstrip('-•*·').strip()
        
        while parent_stack and parsed[parent_stack[-1]].indent_level >= indent:
            parent_stack.pop()
        
        parent_idx = parent_stack[-1] if parent_stack else None
        
        parsed_row = ParsedRow(
            index=idx,
            label=clean_label,
            indent_level=indent,
            values=values if isinstance(values, dict) else {},
            parent_index=parent_idx,
            children_indices=[]
        )
        
        if parent_idx is not None:
            parsed[parent_idx].children_indices.append(idx)
        
        parsed.append(parsed_row)
        parent_stack.append(idx)
    
    return parsed


def detect_sign_convention(rows: List[ParsedRow]) -> SignConvention:
    """
    Detect the sign convention used in the file.
    - accounting: expenses negative, revenue positive
    - all_positive: all values positive
    - mixed: inconsistent signs
    """
    expense_like_values = []
    revenue_like_values = []
    
    for row in rows:
        norm_label = normalize_label(row.label)
        
        is_expense_like = any(kw in norm_label for kw in EXPENSE_KEYWORDS)
        is_revenue_like = any(kw in norm_label for kw in REVENUE_KEYWORDS)
        
        all_values = [v for v in row.values.values() if isinstance(v, (int, float)) and v != 0]
        
        if is_expense_like:
            expense_like_values.extend(all_values)
        elif is_revenue_like:
            revenue_like_values.extend(all_values)
    
    if not expense_like_values:
        return SignConvention.ALL_POSITIVE
    
    negative_expense_count = sum(1 for v in expense_like_values if v < 0)
    positive_revenue_count = sum(1 for v in revenue_like_values if v > 0)
    
    expense_negative_ratio = negative_expense_count / len(expense_like_values) if expense_like_values else 0
    revenue_positive_ratio = positive_revenue_count / len(revenue_like_values) if revenue_like_values else 1
    
    if expense_negative_ratio > 0.6 and revenue_positive_ratio > 0.6:
        return SignConvention.ACCOUNTING
    elif expense_negative_ratio < 0.2:
        return SignConvention.ALL_POSITIVE
    else:
        return SignConvention.MIXED


def calculate_classification_scores(label: str, values: List[float], has_children: bool) -> Dict[str, float]:
    """Calculate scores for each classification type."""
    norm_label = normalize_label(label)
    scores = {
        'revenue': 0.0,
        'expense': 0.0,
        'derived': 0.0,
        'header': 0.0,
        'other': 0.1
    }
    
    for kw in REVENUE_KEYWORDS:
        if kw in norm_label:
            scores['revenue'] += 1.0
            if norm_label == kw:
                scores['revenue'] += 0.5
    
    for kw in EXPENSE_KEYWORDS:
        if kw in norm_label:
            scores['expense'] += 1.0
            if norm_label == kw:
                scores['expense'] += 0.5
    
    for kw in DERIVED_KEYWORDS:
        if kw in norm_label:
            scores['derived'] += 2.0
    
    for exact in HEADER_EXACT_MATCHES:
        if norm_label == exact:
            scores['header'] += 1.5
    
    if has_children:
        scores['header'] += 1.0
    
    if values:
        negative_count = sum(1 for v in values if v < 0)
        if negative_count > len(values) * 0.6:
            scores['expense'] += 0.5
    
    return scores


def classify_row(
    row: ParsedRow,
    has_children: bool = False,
    sign_convention: SignConvention = SignConvention.ALL_POSITIVE
) -> ClassifiedRow:
    """Classify a single row based on its label and values."""
    values = [v for v in row.values.values() if isinstance(v, (int, float))]
    scores = calculate_classification_scores(row.label, values, has_children)
    
    max_score = max(scores.values())
    classification = Classification.OTHER
    
    if max_score > 0.5:
        if scores['derived'] >= max_score:
            classification = Classification.DERIVED
        elif scores['header'] >= max_score:
            classification = Classification.HEADER
        elif scores['expense'] > scores['revenue']:
            classification = Classification.EXPENSE
        elif scores['revenue'] > 0.5:
            classification = Classification.REVENUE
    
    expense_bucket = None
    if classification == Classification.EXPENSE:
        expense_bucket = map_expense_bucket(row.label)
    
    confidence = "high" if max_score > 1.5 else ("medium" if max_score > 0.8 else "low")
    
    notes = []
    if has_children:
        notes.append("Has child rows")
    if sign_convention == SignConvention.ACCOUNTING and classification == Classification.EXPENSE:
        notes.append("Values normalized from negative to positive")
    
    parent_label = None
    
    return ClassifiedRow(
        label=row.label,
        classification=classification,
        expense_bucket=expense_bucket,
        confidence=confidence,
        is_header=classification == Classification.HEADER,
        has_children=has_children,
        parent_label=parent_label,
        notes=notes
    )


def map_expense_bucket(label: str) -> ExpenseBucket:
    """Map an expense row to a specific bucket."""
    norm_label = normalize_label(label)
    
    for kw in MARKETING_BUCKET_KEYWORDS:
        if kw in norm_label:
            return ExpenseBucket.MARKETING
    
    for kw in PAYROLL_BUCKET_KEYWORDS:
        if kw in norm_label:
            return ExpenseBucket.PAYROLL
    
    for kw in COGS_BUCKET_KEYWORDS:
        if kw in norm_label:
            return ExpenseBucket.COGS
    
    return ExpenseBucket.OPERATING


def normalize_value(
    raw_value: float,
    classification: Classification,
    sign_convention: SignConvention
) -> Tuple[float, List[str]]:
    """
    Normalize a value based on its classification and the file's sign convention.
    Returns (normalized_value, warnings).
    
    Rules:
    - Expenses: always stored as positive (abs)
    - Revenue: should be positive (warn if negative)
    - Derived/Header/Other: keep as-is
    """
    warnings = []
    
    if classification == Classification.EXPENSE:
        return abs(raw_value), warnings
    
    if classification == Classification.REVENUE:
        if raw_value < 0:
            warnings.append(f"Revenue value is negative ({raw_value}), normalized to positive")
            return abs(raw_value), warnings
        return raw_value, warnings
    
    return raw_value, warnings


def classify_all_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point: classify all rows in a financial data import.
    Returns structured result with sign convention, classified rows, and warnings.
    """
    parsed = parse_rows_with_hierarchy(rows)
    
    sign_convention = detect_sign_convention(parsed)
    
    classified_rows = []
    all_warnings = []
    
    for parsed_row in parsed:
        has_children = len(parsed_row.children_indices) > 0
        classified = classify_row(parsed_row, has_children, sign_convention)
        
        normalized_values = {}
        for period, raw_val in parsed_row.values.items():
            if isinstance(raw_val, (int, float)):
                norm_val, warnings = normalize_value(raw_val, classified.classification, sign_convention)
                normalized_values[period] = {
                    'raw': raw_val,
                    'normalized': norm_val,
                    'warnings': warnings
                }
                all_warnings.extend(warnings)
        
        classified_rows.append({
            'index': parsed_row.index,
            'label': parsed_row.label,
            'classification': classified.classification.value,
            'expense_bucket': classified.expense_bucket.value if classified.expense_bucket else None,
            'confidence': classified.confidence,
            'is_header': classified.is_header,
            'has_children': classified.has_children,
            'parent_index': parsed_row.parent_index,
            'values': normalized_values,
            'include_in_totals': classified.classification in [Classification.REVENUE, Classification.EXPENSE] and not classified.is_header,
            'notes': classified.notes
        })
    
    return {
        'sign_convention': sign_convention.value,
        'rows': classified_rows,
        'warnings': all_warnings,
        'summary': {
            'revenue_rows': sum(1 for r in classified_rows if r['classification'] == 'revenue'),
            'expense_rows': sum(1 for r in classified_rows if r['classification'] == 'expense'),
            'derived_rows': sum(1 for r in classified_rows if r['classification'] == 'derived'),
            'header_rows': sum(1 for r in classified_rows if r['classification'] == 'header'),
            'other_rows': sum(1 for r in classified_rows if r['classification'] == 'other'),
        }
    }
