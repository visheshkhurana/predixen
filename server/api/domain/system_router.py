"""
Domain Router: /system
Aggregates system-level endpoints — events, flags, autopilot, admin tools.
All endpoints require platform admin authentication.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.api.admin import require_platform_admin

router = APIRouter(prefix="/system", tags=["System Domain"])


@router.get("/events")
def get_events(
    company_id: Optional[int] = None,
    event_type: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    limit: int = Query(50, le=500),
    user=Depends(require_platform_admin),
):
    from server.events.event_store import get_events as _get_events
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"events": []}
    return {"events": _get_events(cid, event_type=event_type, aggregate_type=aggregate_type, limit=limit)}


@router.get("/events/stats")
def get_event_stats(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.events.event_store import get_event_stats
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"total_events": 0, "by_type": {}}
    return get_event_stats(cid)


@router.get("/flags")
def get_all_flags(user=Depends(require_platform_admin)):
    from server.core.feature_flags import get_all_flags
    return {"flags": get_all_flags()}


@router.post("/flags/{flag_key}")
def toggle_flag(flag_key: str, enabled: bool = True, user=Depends(require_platform_admin)):
    from server.core.feature_flags import set_feature_flag
    set_feature_flag(flag_key, enabled)
    return {"key": flag_key, "enabled": enabled}


@router.get("/agents")
def get_agents(user=Depends(require_platform_admin)):
    from server.copilot.ai_governance import get_all_permissions
    return {"agents": get_all_permissions()}


@router.get("/agents/stats")
def agent_usage_stats(days: int = 7, user=Depends(require_platform_admin)):
    from server.copilot.ai_governance import get_agent_stats
    return get_agent_stats(days=days)


@router.get("/autopilot/briefing")
def get_briefing(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import get_latest_briefing
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"message": "No company found for this user."}
    briefing = get_latest_briefing(cid)
    if not briefing:
        return {"message": "No briefing available yet. Run autopilot first."}
    return briefing


@router.post("/autopilot/run")
def run_autopilot_endpoint(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import run_autopilot
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"error": "No company found"}
    return run_autopilot(cid)


@router.get("/autopilot/history")
def autopilot_history(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import get_briefing_history
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"history": []}
    return {"history": get_briefing_history(cid)}


@router.get("/autopilot/risks")
def detect_risks(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import detect_risks
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"risks": []}
    return {"risks": detect_risks(cid)}


@router.get("/confidence")
def get_confidence(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.data_confidence import compute_all_confidence
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"overall_confidence": 0, "metrics": {}}
    return compute_all_confidence(cid)


def _get_primary_company(user) -> Optional[int]:
    try:
        from server.core.db import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT c.id FROM companies c
                    LEFT JOIN workspace_members wm ON wm.company_id = c.id AND wm.user_id = :uid
                    WHERE c.user_id = :uid OR wm.user_id = :uid
                    ORDER BY c.id LIMIT 1
                """),
                {"uid": user.id},
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None
