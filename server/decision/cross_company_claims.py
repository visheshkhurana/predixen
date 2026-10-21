"""Wording for cross-company pattern rows.

Research rows are published studies seeded into cross_company_patterns.
Peer-cohort rows are decision_outcome aggregates. The distinct-company gate
that decides whether a decision_outcome row is publishable lives in
get_relevant_patterns and is not re-decided here.
"""

from typing import Any, Dict, Optional

RESEARCH = "research"
PEER_COHORT = "peer_cohort"

# Longer prefixes first so "subscription economy" wins over a shorter token.
_PUBLISHER_PREFIXES = (
    ("andreessen horowitz", "a16z"),
    ("subscription economy", "Subscription Economy Index"),
    ("startup genome", "Startup Genome"),
    ("lenny's newsletter", "Lenny's Newsletter"),
    ("lenny", "Lenny's Newsletter"),
    ("first round", "First Round"),
    ("cb insights", "CB Insights"),
    ("rock health", "Rock Health"),
    ("y combinator", "YC"),
    ("chartmogul", "ChartMogul"),
    ("openview", "OpenView"),
    ("bessemer", "Bessemer"),
    ("keybanc", "KeyBanc"),
    ("mckinsey", "McKinsey"),
    ("reforge", "Reforge"),
    ("shopify", "Shopify"),
    ("stripe", "Stripe"),
    ("toptal", "Toptal"),
    ("plaid", "Plaid"),
    ("zuora", "Zuora"),
    ("bolt", "Bolt"),
    ("a16z", "a16z"),
    ("hax", "HAX"),
    ("yc", "YC"),
)


def research_citation(source: Optional[str]) -> str:
    """Short publisher name for a stored research source title."""
    raw = " ".join((source or "").split())
    if not raw:
        return "published research"
    lower = raw.lower()
    for prefix, label in _PUBLISHER_PREFIXES:
        if lower.startswith(prefix):
            return label
    parts = raw.split()
    if parts and parts[-1].isdigit() and len(parts[-1]) == 4:
        parts = parts[:-1]
    return " ".join(parts) or raw


def format_research_insight(source: Optional[str], success_rate: Any, sample_size: Any) -> str:
    """Attribute a research row to its publisher. Never calls it a peer cohort."""
    citation = research_citation(source)
    rate = float(success_rate or 0)
    n = int(sample_size or 0)
    return f"Industry research ({citation}, n={n}): {rate:.0f}% positive outcomes"


def source_kind(pattern_type: Optional[str]) -> str:
    if pattern_type == RESEARCH:
        return RESEARCH
    return PEER_COHORT


def rate_fields(pattern: Dict[str, Any]) -> Dict[str, Any]:
    """Fields both engines copy onto a recommendation."""
    pattern_type = pattern.get("pattern_type")
    kind = source_kind(pattern_type)
    return {
        "success_rate": pattern.get("success_rate"),
        "sample_size": pattern.get("sample_size"),
        "pattern_type": pattern_type,
        "source": pattern.get("source"),
        "cross_company_source": kind,
    }


def peer_insight_text(success_rate: Any, sample_size: Any, decision_type: Optional[str] = None) -> str:
    """Existing peer-cohort sentence. decision_type set → pattern engine voice."""
    if decision_type:
        label = decision_type.replace("_", " ")
        return (
            f"{success_rate:.0f}% of similar companies saw positive outcomes "
            f"from {label} decisions (based on {sample_size} decisions)."
        )
    return (
        f"{success_rate:.0f}% of similar companies saw positive outcomes from this type of action "
        f"(based on {sample_size} decisions)."
    )


def peer_rationale_suffix(success_rate: Any) -> str:
    return f" {success_rate:.0f}% of similar companies that took this action saw positive outcomes."


def insight_text(rate: Dict[str, Any], decision_type: Optional[str] = None) -> str:
    if rate.get("cross_company_source") == RESEARCH or rate.get("pattern_type") == RESEARCH:
        return format_research_insight(rate.get("source"), rate.get("success_rate"), rate.get("sample_size"))
    return peer_insight_text(rate.get("success_rate"), rate.get("sample_size"), decision_type)
