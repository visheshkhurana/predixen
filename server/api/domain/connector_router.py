"""
Domain Router: /connectors-domain
Aggregates data connector endpoints (prefixed differently to avoid
collisions with existing /connectors routes).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/connectors-domain", tags=["Connectors Domain"])


@router.get("/list")
def list_connectors(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, name, connector_type, status, last_synced_at FROM data_sources WHERE company_id = :cid ORDER BY name"),
        {"cid": company_id},
    ).fetchall()
    return [{"id": r[0], "name": r[1], "type": r[2], "status": r[3], "last_synced": r[4].isoformat() if r[4] else None} for r in rows]


@router.get("/catalog")
def get_connector_catalog(user=Depends(get_current_user)):
    try:
        from server.connectors.registry import CONNECTOR_REGISTRY
        return {"connectors": [
            {"key": k, "name": v.get("name", k), "category": v.get("category", "other")}
            for k, v in CONNECTOR_REGISTRY.items()
        ]}
    except Exception:
        return {"connectors": [], "note": "Registry unavailable"}
