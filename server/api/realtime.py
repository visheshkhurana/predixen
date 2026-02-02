"""
Real-time API endpoints using Server-Sent Events (SSE) for live KPI updates.
"""
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.models import User, Company

router = APIRouter(prefix="/realtime", tags=["realtime"])


async def generate_kpi_events(
    company_id: int,
    db: Session,
    request: Request
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for real-time KPI updates.
    Sends updates every 5 seconds with latest metrics.
    """
    try:
        while True:
            if await request.is_disconnected():
                break
            
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                yield f"event: error\ndata: {json.dumps({'error': 'Company not found'})}\n\n"
                break
            
            metrics_data = company.metadata_json or {}
            
            kpi_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "company_id": company_id,
                "metrics": {
                    "monthly_revenue": metrics_data.get("monthly_revenue", 0),
                    "mrr": metrics_data.get("mrr", 0),
                    "arr": metrics_data.get("arr", 0),
                    "cash_balance": metrics_data.get("cash_balance", 0),
                    "net_burn": metrics_data.get("net_burn", 0),
                    "runway_months": metrics_data.get("runway_months", 0),
                    "gross_margin": metrics_data.get("gross_margin", 0),
                    "churn_rate": metrics_data.get("churn_rate", 0),
                    "cac": metrics_data.get("cac", 0),
                    "ltv": metrics_data.get("ltv", 0),
                    "ltv_cac_ratio": metrics_data.get("ltv_cac_ratio", 0),
                    "headcount": metrics_data.get("headcount", 0),
                    "revenue_per_employee": metrics_data.get("revenue_per_employee", 0),
                }
            }
            
            yield f"event: kpi_update\ndata: {json.dumps(kpi_data)}\n\n"
            
            await asyncio.sleep(5)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.get("/kpi/{company_id}")
async def stream_kpi_updates(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Stream real-time KPI updates for a company via Server-Sent Events.
    
    Connect to this endpoint to receive live metric updates every 5 seconds.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return StreamingResponse(
        generate_kpi_events(company_id, db, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/kpi/{company_id}/push")
async def push_kpi_update(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger a KPI update notification.
    This can be called after data imports or manual updates.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "success": True,
        "message": "KPI update triggered",
        "company_id": company_id,
        "timestamp": datetime.utcnow().isoformat()
    }
