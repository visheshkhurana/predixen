"""
API endpoints for external integrations (CRM, Accounting).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from server.core.db import get_db
from server.models.company import Company
from server.integrations.accounting import get_accounting_integration
from server.integrations.crm import get_crm_integration

router = APIRouter(prefix="/integrations", tags=["integrations"])


class ConnectRequest(BaseModel):
    provider: str
    credentials: Dict[str, str]


class IntegrationStatus(BaseModel):
    provider: str
    type: str  # "accounting" or "crm"
    connected: bool
    last_sync: Optional[str] = None
    error: Optional[str] = None


@router.get("/companies/{company_id}/status")
def get_integration_status(
    company_id: int,
    db: Session = Depends(get_db),
):
    """
    Get status of all integrations for a company.
    """
    from server.models.user import User
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    demo_user = db.query(User).filter(User.id == company.user_id, User.email == "demo@predixen.ai").first()
    if demo_user:
        from datetime import datetime, timedelta
        last_sync_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        return {
            "company_id": company_id,
            "integrations": {
                "accounting": {
                    "available": ["quickbooks", "xero"],
                    "connected": "quickbooks",
                    "last_sync": last_sync_time,
                    "sync_details": {
                        "records_synced": 847,
                        "last_error": None
                    }
                },
                "crm": {
                    "available": ["salesforce", "hubspot"],
                    "connected": "hubspot",
                    "last_sync": last_sync_time,
                    "sync_details": {
                        "records_synced": 234,
                        "last_error": None
                    }
                },
                "payments": {
                    "available": ["stripe"],
                    "connected": "stripe",
                    "last_sync": last_sync_time,
                    "sync_details": {
                        "records_synced": 1256,
                        "last_error": None
                    }
                },
            },
        }
    
    return {
        "company_id": company_id,
        "integrations": {
            "accounting": {
                "available": ["quickbooks", "xero"],
                "connected": None,
                "last_sync": None,
            },
            "crm": {
                "available": ["salesforce", "hubspot"],
                "connected": None,
                "last_sync": None,
            },
            "payments": {
                "available": ["stripe"],
                "connected": None,
                "last_sync": None,
            },
        },
    }


@router.get("/available")
def get_available_integrations():
    """
    List all available integrations.
    """
    return {
        "accounting": [
            {
                "id": "quickbooks",
                "name": "QuickBooks Online",
                "description": "Sync P&L, Balance Sheet, and transactions",
                "features": ["revenue", "expenses", "cash_flow", "ar_ap"],
            },
            {
                "id": "xero",
                "name": "Xero",
                "description": "Sync financial reports and bank transactions",
                "features": ["revenue", "expenses", "cash_flow", "ar_ap"],
            },
        ],
        "crm": [
            {
                "id": "salesforce",
                "name": "Salesforce",
                "description": "Sync opportunities, contacts, and pipeline data",
                "features": ["pipeline", "deals", "contacts", "forecasts"],
            },
            {
                "id": "hubspot",
                "name": "HubSpot",
                "description": "Sync deals, contacts, and marketing data",
                "features": ["pipeline", "deals", "contacts", "marketing"],
            },
        ],
    }


@router.post("/companies/{company_id}/accounting/connect")
async def connect_accounting(
    company_id: int,
    request: ConnectRequest,
    db: Session = Depends(get_db),
):
    """
    Connect an accounting integration.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    integration = get_accounting_integration(request.provider)
    if not integration:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown accounting provider: {request.provider}"
        )
    
    success = await integration.connect(request.credentials)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect")
    
    return {
        "status": "connected",
        "provider": request.provider,
        "message": f"Successfully connected to {request.provider}",
    }


@router.post("/companies/{company_id}/crm/connect")
async def connect_crm(
    company_id: int,
    request: ConnectRequest,
    db: Session = Depends(get_db),
):
    """
    Connect a CRM integration.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    integration = get_crm_integration(request.provider)
    if not integration:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown CRM provider: {request.provider}"
        )
    
    success = await integration.connect(request.credentials)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect")
    
    return {
        "status": "connected",
        "provider": request.provider,
        "message": f"Successfully connected to {request.provider}",
    }


@router.post("/companies/{company_id}/accounting/sync")
async def sync_accounting(
    company_id: int,
    provider: str = "quickbooks",
    db: Session = Depends(get_db),
):
    """
    Sync data from accounting integration.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    integration = get_accounting_integration(provider)
    if not integration:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    result = await integration.sync()
    
    return {
        "success": result.success,
        "records_synced": result.records_synced,
        "errors": result.errors,
        "sync_time": result.sync_time.isoformat(),
    }


@router.post("/companies/{company_id}/crm/sync")
async def sync_crm(
    company_id: int,
    provider: str = "hubspot",
    db: Session = Depends(get_db),
):
    """
    Sync data from CRM integration.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    integration = get_crm_integration(provider)
    if not integration:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    result = await integration.sync()
    
    return {
        "success": result.success,
        "records_synced": result.records_synced,
        "errors": result.errors,
        "sync_time": result.sync_time.isoformat(),
    }


@router.get("/companies/{company_id}/crm/pipeline")
async def get_pipeline_metrics(
    company_id: int,
    provider: str = "hubspot",
    db: Session = Depends(get_db),
):
    """
    Get pipeline metrics from CRM.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    integration = get_crm_integration(provider)
    if not integration:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    # Check connection and get metrics
    from server.integrations.crm import HubSpotIntegration, SalesforceIntegration
    
    if isinstance(integration, (HubSpotIntegration, SalesforceIntegration)):
        metrics = await integration.get_pipeline_metrics()
        if metrics:
            return metrics.to_dict()
    
    return {
        "total_pipeline_value": 0,
        "weighted_pipeline": 0,
        "deal_count": 0,
        "message": "No data available. Please connect and sync your CRM first.",
    }


@router.post("/companies/{company_id}/payments/connect")
async def connect_payments(
    company_id: int,
    request: ConnectRequest,
    db: Session = Depends(get_db),
):
    """
    Connect a payments integration (e.g., Stripe).
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if request.provider not in ["stripe"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payments provider: {request.provider}"
        )
    
    # In production, this would validate credentials and store them
    return {
        "status": "connected",
        "provider": request.provider,
        "message": f"Successfully connected to {request.provider}",
    }


@router.post("/companies/{company_id}/payments/sync")
async def sync_payments(
    company_id: int,
    provider: str = "stripe",
    db: Session = Depends(get_db),
):
    """
    Sync data from payments integration.
    """
    from datetime import datetime
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if provider not in ["stripe"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    # In production, this would call the Stripe API and sync data
    # For now, return mock success response
    return {
        "success": True,
        "records_synced": 0,
        "errors": [],
        "sync_time": datetime.utcnow().isoformat(),
    }
