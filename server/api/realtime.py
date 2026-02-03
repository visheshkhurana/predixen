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
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan

router = APIRouter(prefix="/realtime", tags=["realtime"])


def get_company_kpi_metrics(company_id: int, db: Session) -> dict:
    """
    Get KPI metrics from financial records and truth scan data.
    """
    # Try to get latest financial record
    latest_financial = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    # Try to get latest truth scan
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    # Get company metadata as fallback
    company = db.query(Company).filter(Company.id == company_id).first()
    metadata = company.metadata_json if company else {}
    
    # Initialize with zeros
    metrics = {
        "monthly_revenue": 0,
        "mrr": 0,
        "arr": 0,
        "cash_balance": 0,
        "net_burn": 0,
        "runway_months": 0,
        "gross_margin": 0,
        "churn_rate": 0,
        "cac": 0,
        "ltv": 0,
        "ltv_cac_ratio": 0,
        "headcount": 0,
        "revenue_per_employee": 0
    }
    
    # Populate from financial records
    if latest_financial:
        revenue = latest_financial.revenue or 0
        cogs = latest_financial.cogs or 0
        opex = latest_financial.opex or 0
        payroll = latest_financial.payroll or 0
        other_costs = latest_financial.other_costs or 0
        cash = latest_financial.cash_balance or 0
        headcount = latest_financial.headcount or 0
        
        total_costs = cogs + opex + payroll + other_costs
        net_burn = total_costs - revenue
        gross_margin = ((revenue - cogs) / revenue) if revenue > 0 else 0
        runway = (cash / net_burn) if net_burn > 0 else 24  # Default 24 months if profitable
        
        metrics["monthly_revenue"] = revenue
        metrics["mrr"] = revenue
        metrics["arr"] = revenue * 12
        metrics["cash_balance"] = cash
        metrics["net_burn"] = net_burn if net_burn > 0 else 0
        metrics["runway_months"] = runway if runway > 0 else 0
        metrics["gross_margin"] = gross_margin
        metrics["headcount"] = headcount
        metrics["revenue_per_employee"] = (revenue / headcount) if headcount > 0 else 0
    
    # Enrich with truth scan data if available
    if truth_scan and truth_scan.outputs_json:
        outputs = truth_scan.outputs_json
        ts_metrics = outputs.get("metrics", {})
        
        # Override with truth scan values if present
        for key in ["churn_rate", "cac", "ltv", "ltv_cac_ratio"]:
            val = ts_metrics.get(key)
            if isinstance(val, (int, float)):
                metrics[key] = val
            elif isinstance(val, dict) and "value" in val:
                metrics[key] = val["value"]
    
    # Final fallback to metadata
    for key in metrics:
        if metrics[key] == 0 and key in metadata:
            metrics[key] = metadata.get(key, 0)
    
    return metrics


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
            
            metrics = get_company_kpi_metrics(company_id, db)
            
            kpi_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "company_id": company_id,
                "metrics": metrics
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


@router.get("/kpi/{company_id}/snapshot")
def get_kpi_snapshot(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a one-time snapshot of KPI metrics for a company.
    Use this for polling when SSE is not available.
    """
    from datetime import datetime
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metrics = get_company_kpi_metrics(company_id, db)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "company_id": company_id,
        "metrics": metrics
    }


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
