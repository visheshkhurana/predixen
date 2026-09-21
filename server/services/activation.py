"""First-success product-bet events: signup_completed and founder_activated.

signup_completed fires once when a user row is created (email register or
first Google OAuth). founder_activated fires once when that founder completes
a Truth Scan or a simulation on their own company data.

Sample companies (companies.metadata_json.is_sample / Company.is_sample) never
count as activation — the #21 sample-data first run must stay labelled and
out of the north-star metric.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from server.services.posthog import capture as posthog_capture

logger = logging.getLogger(__name__)


def company_is_sample(company: Any) -> bool:
    """True when the company is labelled sample data.

    Accepts either Company.is_sample or metadata_json.is_sample so a stale
    object without the property still gates correctly.
    """
    if company is None:
        return True
    if bool(getattr(company, "is_sample", False)):
        return True
    meta = getattr(company, "metadata_json", None) or {}
    return isinstance(meta, dict) and bool(meta.get("is_sample"))


def emit_signup_completed(*, user_id: int, method: str) -> bool:
    """Server first-success signup. Never raises."""
    try:
        if not user_id or not method:
            return False
        return bool(
            posthog_capture(
                "signup_completed",
                f"user:{user_id}",
                {"method": method, "user_id": user_id},
            )
        )
    except Exception:
        logger.exception("[activation] could not emit signup_completed")
        return False


def real_company_ids(companies: list[Any]) -> list[int]:
    """Company ids whose sample flag is not set. Used by first-success checks."""
    return [c.id for c in companies if not company_is_sample(c)]


def _real_company_ids_for_user(db: Any, user_id: int) -> list[int]:
    from server.models.company import Company

    companies = db.query(Company).filter(Company.user_id == user_id).all()
    return real_company_ids(companies)


def _has_prior_truth_scan(
    db: Any,
    company_ids: list[int],
    exclude_id: Optional[int] = None,
) -> bool:
    if not company_ids:
        return False
    from server.models.truth_scan import TruthScan

    q = db.query(TruthScan.id).filter(TruthScan.company_id.in_(company_ids))
    if exclude_id is not None:
        q = q.filter(TruthScan.id != exclude_id)
    return q.first() is not None


def _has_prior_simulation(
    db: Any,
    company_ids: list[int],
    exclude_id: Optional[int] = None,
) -> bool:
    if not company_ids:
        return False
    from server.models.scenario import Scenario
    from server.models.simulation_run import SimulationRun

    q = (
        db.query(SimulationRun.id)
        .join(Scenario, SimulationRun.scenario_id == Scenario.id)
        .filter(Scenario.company_id.in_(company_ids))
    )
    if exclude_id is not None:
        q = q.filter(SimulationRun.id != exclude_id)
    return q.first() is not None


def has_prior_real_activation(
    db: Any,
    user_id: int,
    *,
    exclude_truth_scan_id: Optional[int] = None,
    exclude_simulation_run_id: Optional[int] = None,
) -> bool:
    """True if this founder already completed a real Truth Scan or simulation."""
    real_ids = _real_company_ids_for_user(db, user_id)
    if not real_ids:
        return False
    if _has_prior_truth_scan(db, real_ids, exclude_truth_scan_id):
        return True
    return _has_prior_simulation(db, real_ids, exclude_simulation_run_id)


def maybe_emit_founder_activated(
    db: Any,
    *,
    user_id: int,
    company: Any,
    source: str,
    exclude_truth_scan_id: Optional[int] = None,
    exclude_simulation_run_id: Optional[int] = None,
) -> bool:
    """Emit founder_activated once on first real Truth Scan or simulation.

    Call after the successful row is committed. Pass the just-created scan/run
    id as exclude_* so this success is not treated as a prior one.

    Returns True if the event was handed to capture. Sample companies, retries
    after a prior real success, and missing user/company never emit. Never raises.
    """
    try:
        if not user_id or company_is_sample(company):
            return False
        if has_prior_real_activation(
            db,
            user_id,
            exclude_truth_scan_id=exclude_truth_scan_id,
            exclude_simulation_run_id=exclude_simulation_run_id,
        ):
            return False
        posthog_capture(
            "founder_activated",
            f"user:{user_id}",
            {
                "source": source,
                "company_id": getattr(company, "id", None),
                "is_sample": False,
                "user_id": user_id,
            },
        )
        return True
    except Exception:
        logger.exception("[activation] could not emit founder_activated")
        return False
