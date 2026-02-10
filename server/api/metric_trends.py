from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Optional

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.metric_snapshot import MetricSnapshot

router = APIRouter(tags=["metric-trends"])


@router.get("/companies/{company_id}/trends")
def get_metric_trends(
    company_id: int,
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    cutoff = datetime.utcnow() - timedelta(days=days)
    snapshots = db.query(MetricSnapshot).filter(
        and_(
            MetricSnapshot.company_id == company_id,
            MetricSnapshot.created_at >= cutoff,
        )
    ).order_by(MetricSnapshot.created_at.asc()).all()

    grouped = {}
    for s in snapshots:
        date_key = s.created_at.strftime("%Y-%m-%d") if s.created_at else "unknown"
        if date_key not in grouped:
            grouped[date_key] = {"date": date_key}
        grouped[date_key][s.metric_name] = s.value

    return {
        "days": days,
        "data": list(grouped.values()),
    }


def save_simulation_snapshot(db: Session, company_id: int, simulation_data: dict):
    metrics_to_save = {}
    
    runway = simulation_data.get("runway", {})
    if runway.get("p50") is not None:
        metrics_to_save["runway_p50"] = runway["p50"]
    if runway.get("p10") is not None:
        metrics_to_save["runway_p10"] = runway["p10"]
    if runway.get("p90") is not None:
        metrics_to_save["runway_p90"] = runway["p90"]

    bands = simulation_data.get("bands", {})
    cash_band = bands.get("cash", {})
    if cash_band.get("p50"):
        last_cash = cash_band["p50"][-1] if isinstance(cash_band["p50"], list) else None
        if last_cash is not None:
            metrics_to_save["cash_p50_final"] = last_cash

    survival = simulation_data.get("survival", {})
    if survival.get("12_month") is not None:
        metrics_to_save["survival_12m"] = survival["12_month"]

    for metric_name, value in metrics_to_save.items():
        snapshot = MetricSnapshot(
            company_id=company_id,
            metric_name=metric_name,
            value=float(value),
        )
        db.add(snapshot)

    if metrics_to_save:
        db.commit()
