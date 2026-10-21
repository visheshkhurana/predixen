"""Cohort gate for cross-company peer data.

Peer revenue bands, stage, and other attributes are published only as
aggregates. Individual peers are never returned. A missing sharing flag is
not opt-in.

MIN_DISTINCT_PEERS is a code constant. It is not read from the environment.
"""
from typing import Any, Dict, Iterable, List, Optional

MIN_DISTINCT_PEERS = 5
INSUFFICIENT_PEERS = "insufficient_peers"


def opted_in(company: Any) -> bool:
    """True only when the company has an explicit sharing flag set."""
    return bool(getattr(company, "data_sharing_enabled", False))


def empty_peer_view() -> Dict[str, Any]:
    return {
        "similar_companies": [],
        "aggregates": None,
        "peer_count": 0,
        "reason": INSUFFICIENT_PEERS,
    }


def band_counts(label_to_ids: Dict[str, Iterable[int]]) -> List[Dict[str, Any]]:
    """Publish a band only when at least MIN_DISTINCT_PEERS companies share it."""
    bands = []
    for label, ids in label_to_ids.items():
        distinct = {company_id for company_id in ids if company_id is not None}
        if len(distinct) >= MIN_DISTINCT_PEERS:
            bands.append({"band": label, "companies": len(distinct)})
    bands.sort(key=lambda row: (-row["companies"], str(row["band"])))
    return bands


def publishable_company_count(company_ids: Iterable[int]) -> Optional[int]:
    distinct = {company_id for company_id in company_ids if company_id is not None}
    if len(distinct) < MIN_DISTINCT_PEERS:
        return None
    return len(distinct)
