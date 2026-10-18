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
from server.core.burn import burn_summary

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
        "runway_months": None,
        "gross_margin": 0,
        "churn_rate": None,
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
        headcount = latest_financial.headcount or 0
        
        # Shared rule (server/core/burn.py): signed net burn incl. marketing;
        # runway is null when profitable (see is_profitable) or cash unknown --
        # never a fabricated 12 / 36 / 60 months.
        burn = burn_summary(latest_financial)
        gross_margin = ((revenue - cogs) / revenue) if revenue > 0 else 0
        
        metrics["monthly_revenue"] = revenue
        metrics["mrr"] = revenue
        metrics["arr"] = revenue * 12
        metrics["cash_balance"] = burn["cash_balance"]
        metrics["net_burn"] = burn["net_burn"] if burn["net_burn"] is not None else 0
        metrics["runway_months"] = burn["runway_months"]
        metrics["runway_status"] = burn["runway_status"]
        metrics["is_profitable"] = burn["is_profitable"]
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
        
        if (metrics.get("churn_rate") or 0) > 1:
            metrics["churn_rate"] = metrics["churn_rate"] / 100
        
        # CAC / LTV / LTV:CAC are reported as computed. The old clamps (CAC
        # floor $100, LTV floor $500, ratio 0.5x-20x) replaced real values with
        # invented ones.
    
    # Final fallback to metadata (runway is never back-filled: null means
    # profitable or cash unknown, and a stored number would contradict that).
    for key in metrics:
        if key in ("runway_months", "runway_status", "is_profitable"):
            continue
        if metrics[key] in (0, None) and key in metadata:
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


@router.get("/kpi/{company_id}/history")
def get_kpi_history(
    company_id: int,
    months: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical KPI data from financial records for trend charts.
    Returns up to `months` periods of data, ordered oldest to newest.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    financials = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_end.desc())
        .limit(months)
        .all()
    )

    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()

    ts_metrics = {}
    if truth_scan and truth_scan.outputs_json:
        ts_metrics = truth_scan.outputs_json.get("metrics", {})

    history = []
    for record in reversed(financials):
        revenue = record.revenue or 0
        cogs = record.cogs or 0
        cash = record.cash_balance
        headcount = record.headcount or 0

        burn = burn_summary(record)
        net_burn = burn["net_burn"] if burn["net_burn"] is not None else 0
        gross_margin = ((revenue - cogs) / revenue) if revenue > 0 else 0
        runway = burn["runway_months"]

        period_label = record.period_end.strftime("%b %y") if record.period_end else ""

        churn_val = ts_metrics.get("churn_rate")
        if isinstance(churn_val, dict):
            churn_val = churn_val.get("value", 0)
        # No churn data -> null ("not available"), not an invented 2%.
        churn_rate = churn_val if isinstance(churn_val, (int, float)) else None
        if churn_rate is not None and churn_rate > 1:
            churn_rate = churn_rate / 100

        cac_val = ts_metrics.get("cac")
        if isinstance(cac_val, dict):
            cac_val = cac_val.get("value", 0)
        cac = cac_val if isinstance(cac_val, (int, float)) else 0

        ltv_val = ts_metrics.get("ltv")
        if isinstance(ltv_val, dict):
            ltv_val = ltv_val.get("value", 0)
        ltv = ltv_val if isinstance(ltv_val, (int, float)) else 0

        ltv_cac_val = ts_metrics.get("ltv_cac_ratio")
        if isinstance(ltv_cac_val, dict):
            ltv_cac_val = ltv_cac_val.get("value", 0)
        ltv_cac_ratio = ltv_cac_val if isinstance(ltv_cac_val, (int, float)) else 0

        history.append({
            "time": period_label,
            "monthly_revenue": revenue,
            "mrr": revenue,
            "arr": revenue * 12,
            "cash_balance": cash,
            "net_burn": net_burn,
            "runway_months": runway,
            "is_profitable": burn["is_profitable"],
            "gross_margin": gross_margin,
            "churn_rate": churn_rate,
            "cac": cac,
            "ltv": ltv,
            "ltv_cac_ratio": ltv_cac_ratio,
            "headcount": headcount,
            "revenue_per_employee": (revenue / headcount) if headcount > 0 else 0,
        })

    return {
        "company_id": company_id,
        "months": len(history),
        "data": history
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
