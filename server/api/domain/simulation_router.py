"""
Domain Router: /api/simulation
Aggregates simulation, scenario, and stress test endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company

router = APIRouter(prefix="/simulation", tags=["Simulation Domain"])


@router.get("/scenarios")
def list_scenarios(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, name, description, status, created_at FROM scenarios WHERE company_id = :cid ORDER BY created_at DESC"),
        {"cid": company_id},
    ).fetchall()
    return [{"id": r[0], "name": r[1], "description": r[2], "status": r[3], "created_at": r[4].isoformat() if r[4] else None} for r in rows]


@router.get("/runs")
def list_runs(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("SELECT id, scenario_id, status, created_at FROM simulation_runs WHERE company_id = :cid ORDER BY created_at DESC LIMIT 20"),
        {"cid": company_id},
    ).fetchall()
    return [{"id": r[0], "scenario_id": r[1], "status": r[2], "created_at": r[3].isoformat() if r[3] else None} for r in rows]


@router.get("/history")
def simulation_history(company_id: int = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    get_user_company(db, company_id, user)
    from sqlalchemy import text
    rows = db.execute(
        text("""
            SELECT s.id, s.name, sr.id as run_id, sr.status, sr.created_at
            FROM scenarios s
            LEFT JOIN simulation_runs sr ON sr.scenario_id = s.id
            WHERE s.company_id = :cid
            ORDER BY sr.created_at DESC NULLS LAST LIMIT 50
        """),
        {"cid": company_id},
    ).fetchall()
    return [
        {"scenario_id": r[0], "scenario_name": r[1], "run_id": r[2], "status": r[3], "created_at": r[4].isoformat() if r[4] else None}
        for r in rows
    ]
