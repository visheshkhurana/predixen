from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import uuid as uuid_lib

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.shared_scenario import SharedScenario

router = APIRouter(tags=["shared-scenarios"])

# Share metadata rides inside simulation_data (no schema change); it is
# stripped before the payload is returned to a viewer.
SHARE_META_KEY = "__share"
MAX_SHARE_DAYS = 365


class ShareScenarioRequest(BaseModel):
    scenario_name: str
    scenario_description: Optional[str] = None
    simulation_data: dict
    # Optional: the link stops working after this many days. None = until revoked.
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=MAX_SHARE_DAYS)


def _expires_at(shared: SharedScenario) -> Optional[str]:
    data = shared.simulation_data if isinstance(shared.simulation_data, dict) else {}
    meta = data.get(SHARE_META_KEY) or {}
    return meta.get("expiresAt") if isinstance(meta, dict) else None


def is_share_expired(shared: SharedScenario, now: Optional[datetime] = None) -> bool:
    raw = _expires_at(shared)
    if not raw:
        return False
    try:
        expires_at = datetime.fromisoformat(str(raw))
    except ValueError:
        return True
    return (now or datetime.utcnow()) >= expires_at


@router.post("/companies/{company_id}/scenarios/share")
def create_shared_scenario(
    company_id: int,
    data: ShareScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    expires_at = (
        (datetime.utcnow() + timedelta(days=data.expires_in_days)).isoformat()
        if data.expires_in_days else None
    )
    simulation_data = {k: v for k, v in (data.simulation_data or {}).items() if k != SHARE_META_KEY}
    if expires_at:
        simulation_data[SHARE_META_KEY] = {"expiresAt": expires_at}

    share_uuid = str(uuid_lib.uuid4())
    shared = SharedScenario(
        uuid=share_uuid,
        company_id=company_id,
        scenario_name=data.scenario_name,
        scenario_description=data.scenario_description,
        simulation_data=simulation_data,
        created_by=current_user.id,
    )
    db.add(shared)
    db.commit()
    db.refresh(shared)

    return {
        "uuid": share_uuid,
        "url": f"/scenarios/shared/{share_uuid}",
        "expires_at": expires_at,
    }


@router.delete("/companies/{company_id}/scenarios/shared/{share_uuid}")
def revoke_shared_scenario(
    company_id: int,
    share_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a shared scenario link. Only the company owner or the link's creator."""
    shared = db.query(SharedScenario).filter(
        SharedScenario.uuid == share_uuid,
        SharedScenario.company_id == company_id,
    ).first()
    if not shared:
        raise HTTPException(status_code=404, detail="Shared scenario not found")
    company = db.query(Company).filter(Company.id == company_id).first()
    is_owner = company is not None and company.user_id == current_user.id
    if not is_owner and shared.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Shared scenario not found")

    db.delete(shared)
    db.commit()
    return {"revoked": True}


@router.get("/scenarios/shared/{share_uuid}")
def get_shared_scenario(
    share_uuid: str,
    db: Session = Depends(get_db),
):
    shared = db.query(SharedScenario).filter(
        SharedScenario.uuid == share_uuid
    ).first()
    if not shared or is_share_expired(shared):
        raise HTTPException(status_code=404, detail="Shared scenario not found")

    data = shared.simulation_data
    if isinstance(data, dict):
        data = {k: v for k, v in data.items() if k != SHARE_META_KEY}

    return {
        "uuid": shared.uuid,
        "scenario_name": shared.scenario_name,
        "scenario_description": shared.scenario_description,
        "simulation_data": data,
        "created_at": shared.created_at.isoformat() if shared.created_at else None,
        "expires_at": _expires_at(shared),
    }
