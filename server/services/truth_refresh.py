"""Keep the truth scan from going stale on its own.

Every derived number a founder sees — data confidence, ARPU, customer count,
concentration, quality-of-growth — is read from the most recent stored TruthScan
row, not computed on request. Until now that row was only ever written by two
things: a manual "Refresh Scan" click, or an import.

The consequence showed up during verification on 8 Aug. The fix that stopped
churn being fabricated as 0% had been live for hours, and the dashboard still
served the old fabricated value, because the stored scan predated the deploy and
nothing had triggered a recompute. A founder who uploads once in January and
comes back in March is looking at January's derived metrics with a confident
"High Confidence" badge over the top.

This loop closes that gap: once a day, any company whose scan has gone stale
gets recomputed in the background.

Deliberately conservative:

  * Only companies that have financial data are touched. Recomputing an empty
    company produces nothing and wastes a transaction.
  * A per-cycle cap, so a large account list degrades into "catches up over a
    few cycles" rather than a thundering herd on boot.
  * One failure never stops the loop or poisons the next company's session.
  * Nothing is deleted and no existing row is mutated — a scan is appended, the
    same as pressing the button.

Known limitation: this is in-process. Two API replicas mean two loops, and the
same company could be recomputed twice in a cycle. That is wasteful but not
harmful (compute_truth_scan is a pure read plus an append), and it matches how
the onboarding-email and competitor-scan loops in this codebase already work. If
this ever runs multi-replica, move it behind an advisory lock.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# How old a scan has to be before we refresh it.
STALE_AFTER = timedelta(hours=24)

# Ceiling on companies recomputed per cycle.
MAX_PER_CYCLE = 25

# Pause between companies so a backlog doesn't monopolise the DB pool.
PAUSE_BETWEEN_SECONDS = 2


def refresh_stale_truth_scans(db, now: datetime | None = None) -> dict:
    """Recompute truth scans that have gone stale. Returns a small summary.

    Split out from the loop so it can be called directly — from a management
    command, a test, or a one-off backfill — without waiting on a timer.
    """
    from server.models.company import Company
    from server.models.financial import FinancialRecord
    from server.models.truth_scan import TruthScan
    from server.truth.truth_scan import compute_truth_scan

    now = now or datetime.utcnow()
    cutoff = now - STALE_AFTER

    # Companies that have financial data at all. Without it compute_truth_scan
    # produces the "No Financial Data" shape, which is not worth a write.
    company_ids_with_data = {
        row[0]
        for row in db.query(FinancialRecord.company_id).distinct().all()
    }
    if not company_ids_with_data:
        return {"checked": 0, "refreshed": 0, "failed": 0}

    checked = refreshed = failed = 0

    for company_id in sorted(company_ids_with_data):
        if refreshed >= MAX_PER_CYCLE:
            break

        latest = (
            db.query(TruthScan)
            .filter(TruthScan.company_id == company_id)
            .order_by(TruthScan.created_at.desc())
            .first()
        )
        # A company with no scan at all is stale by definition.
        if latest is not None and latest.created_at and latest.created_at > cutoff:
            continue

        checked += 1
        company = db.query(Company).filter(Company.id == company_id).first()
        if company is None:
            continue

        try:
            outputs = compute_truth_scan(company, db)
            db.add(TruthScan(company_id=company_id, outputs_json=outputs))
            db.commit()
            refreshed += 1
        except Exception as e:
            # One bad company must not take the rest down with it.
            failed += 1
            db.rollback()
            logger.warning(f"Truth scan refresh failed for company {company_id}: {e}")

    return {"checked": checked, "refreshed": refreshed, "failed": failed}


async def run_truth_scan_refresh_loop(interval_seconds: int = 21600) -> None:
    """Background loop: refresh stale truth scans every `interval_seconds` (6h).

    The tick is more frequent than STALE_AFTER on purpose — a 6h tick against a
    24h staleness window means a company is never more than ~30h out of date,
    without recomputing anything four times a day.
    """
    from server.core.db import SessionLocal

    logger.info(
        f"Truth scan refresh loop started (tick every {interval_seconds}s, "
        f"stale after {STALE_AFTER})"
    )
    while True:
        # Sleep first: startup is already busy, and nothing is stale at boot
        # that was not stale a moment earlier.
        await asyncio.sleep(interval_seconds)

        db = SessionLocal()
        try:
            result = refresh_stale_truth_scans(db)
            if result["refreshed"] or result["failed"]:
                logger.info(
                    f"Truth scan refresh: {result['refreshed']} recomputed, "
                    f"{result['failed']} failed, {result['checked']} stale"
                )
        except Exception as e:
            logger.warning(f"Truth scan refresh cycle failed: {e}")
        finally:
            db.close()

        await asyncio.sleep(PAUSE_BETWEEN_SECONDS)
