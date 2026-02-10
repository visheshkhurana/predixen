from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid as uuid_lib

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.shared_scenario import SharedScenario

router = APIRouter(tags=["shared-scenarios"])


class ShareScenarioRequest(BaseModel):
    scenario_name: str
    scenario_description: Optional[str] = None
    simulation_data: dict


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

    share_uuid = str(uuid_lib.uuid4())
    shared = SharedScenario(
        uuid=share_uuid,
        company_id=company_id,
        scenario_name=data.scenario_name,
        scenario_description=data.scenario_description,
        simulation_data=data.simulation_data,
        created_by=current_user.id,
    )
    db.add(shared)
    db.commit()
    db.refresh(shared)

    return {
        "uuid": share_uuid,
        "url": f"/scenarios/shared/{share_uuid}",
    }


@router.get("/scenarios/shared/{share_uuid}")
def get_shared_scenario(
    share_uuid: str,
    db: Session = Depends(get_db),
):
    shared = db.query(SharedScenario).filter(
        SharedScenario.uuid == share_uuid
    ).first()
    if not shared:
        raise HTTPException(status_code=404, detail="Shared scenario not found")

    return {
        "uuid": shared.uuid,
        "scenario_name": shared.scenario_name,
        "scenario_description": shared.scenario_description,
        "simulation_data": shared.simulation_data,
        "created_at": shared.created_at.isoformat() if shared.created_at else None,
    }
