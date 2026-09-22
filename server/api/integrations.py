"""
API endpoints for external integrations (CRM, Accounting).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from server.core.company_access import get_user_company
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.integrations.accounting import get_accounting_integration
from server.integrations.crm import get_crm_integration

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(get_current_user)],
)


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
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all integrations for a company.
    """
    company = get_user_company(db, company_id, current_user)
    
    demo_user = db.query(User).filter(User.id == company.user_id, User.email == "demo@founderconsole.ai").first()
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
        "payments": [
            {
                "id": "stripe",
                "name": "Stripe",
                "description": "Sync subscription metrics, MRR, churn, and payment data",
                "features": ["mrr", "arr", "churn", "ltv", "subscriptions", "invoices"],
            },
        ],
    }


@router.post("/companies/{company_id}/accounting/connect")
async def connect_accounting(
    company_id: int,
    request: ConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Connect an accounting integration.
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Connect a CRM integration.
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Sync data from accounting integration.
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Sync data from CRM integration.
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Get pipeline metrics from CRM.
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Connect a payments integration (e.g., Stripe).
    """
    company = get_user_company(db, company_id, current_user)
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Sync data from payments integration.
    """
    from datetime import datetime
    
    company = get_user_company(db, company_id, current_user)
    
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
