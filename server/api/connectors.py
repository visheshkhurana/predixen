"""
API endpoints for payroll and ERP connectors.

Provides endpoints for:
- Listing available connectors
- Managing connector configurations
- Triggering data syncs
- Viewing sync history
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord

from server.connectors import ConnectorRegistry, ConnectorConfig
from server.connectors.base import ProviderCategory

# Import connectors to register them
from server.connectors import razorpayx, greythr, zoho_books, keka, tally, stripe, quickbooks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConnectorCredentials(BaseModel):
    """Credentials for connecting to a provider."""
    provider_id: str
    credentials: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None


class ConnectorStatusResponse(BaseModel):
    """Response for connector status."""
    provider_id: str
    connected: bool
    last_sync: Optional[str] = None
    records_synced: int = 0
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Response for sync operation."""
    success: bool
    provider_id: str
    records_synced: int
    errors: List[str]
    warnings: List[str]


@router.get("/providers")
async def list_providers(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all available connector providers.
    
    Optionally filter by category: payroll, erp, accounting, hris
    """
    cat = None
    if category:
        try:
            cat = ProviderCategory(category)
        except ValueError:
            pass
    
    providers = ConnectorRegistry.list_connectors(category=cat)
    
    # Add India-specific payroll/ERP providers that may not be implemented yet
    additional_providers = [
        {
            "id": "peoplestrong",
            "name": "PeopleStrong",
            "description": "Enterprise HR and talent management platform",
            "category": "hris",
            "coming_soon": True,
        },
        {
            "id": "quikchex",
            "name": "QuikChex",
            "description": "Cloud-based payroll for Indian SMEs",
            "category": "payroll",
            "coming_soon": True,
        },
        {
            "id": "hrblizz",
            "name": "HR Blizz",
            "description": "HRMS and payroll automation",
            "category": "hris",
            "coming_soon": True,
        },
        {
            "id": "deskera",
            "name": "Deskera",
            "description": "All-in-one business management software",
            "category": "erp",
            "coming_soon": True,
        },
        {
            "id": "sap_b1",
            "name": "SAP Business One",
            "description": "Enterprise resource planning for SMBs",
            "category": "erp",
            "coming_soon": True,
        },
        {
            "id": "netsuite",
            "name": "Oracle NetSuite",
            "description": "Cloud ERP and financial management",
            "category": "erp",
            "coming_soon": True,
        },
        {
            "id": "odoo",
            "name": "Odoo",
            "description": "Open-source business applications",
            "category": "erp",
            "coming_soon": True,
        },
        {
            "id": "marg",
            "name": "Marg ERP",
            "description": "GST-ready business software for India",
            "category": "erp",
            "coming_soon": True,
        },
    ]
    
    # Add coming_soon flag to implemented providers
    for provider in providers:
        provider["coming_soon"] = False
    
    # Merge and deduplicate
    provider_ids = {p["id"] for p in providers}
    for ap in additional_providers:
        if ap["id"] not in provider_ids:
            providers.append(ap)
    
    return providers


@router.get("/catalog")
async def list_catalog(
    category: Optional[str] = None,
    native_only: Optional[bool] = False,
    implemented_only: Optional[bool] = False,
    company_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    List connector catalog in format expected by marketplace UI.
    """
    providers = await list_providers(category, current_user)
    
    company_connectors = {}
    if company_id:
        from server.models.company import Company
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company and company.metadata_json:
                company_connectors = company.metadata_json.get("connectors", {})
        except Exception:
            pass
    
    catalog = []
    for p in providers:
        is_implemented = not p.get("coming_soon", False)
        
        if implemented_only and not is_implemented:
            continue
        if native_only and not p.get("native", False):
            continue
        
        install_status = None
        conn_meta = company_connectors.get(p["id"])
        if conn_meta and conn_meta.get("connected"):
            install_status = {
                "connector_id": p["id"],
                "status": "active",
                "last_sync": conn_meta.get("last_sync"),
                "record_count": conn_meta.get("records_synced", 0),
                "error_summary": conn_meta.get("last_error"),
            }
        
        catalog.append({
            "id": p["id"],
            "name": p["name"],
            "category": p.get("category", "other"),
            "logo_url": p.get("logo_url"),
            "description": p.get("description", ""),
            "long_description": p.get("long_description"),
            "auth_type": p.get("auth_type", "api_key"),
            "supports_webhooks": p.get("supports_webhooks", False),
            "supports_polling": p.get("supports_polling", True),
            "supports_incremental": p.get("supports_incremental", False),
            "typical_refresh": p.get("typical_refresh", "daily"),
            "native": p.get("native", False),
            "beta": p.get("coming_soon", False),
            "popularity_rank": p.get("popularity_rank", 99),
            "setup_complexity": p.get("setup_complexity", "medium"),
            "documentation_url": p.get("documentation_url"),
            "implemented": is_implemented,
            "adapter_key": p.get("adapter_key"),
            "metrics_unlocked": p.get("metrics_unlocked", []),
            "required_permissions": p.get("required_permissions", []),
            "data_collected": p.get("data_collected", []),
            "installStatus": install_status,
        })
    
    return catalog


@router.get("/catalog/{connector_id}")
async def get_catalog_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get single connector from catalog.
    """
    catalog = await list_catalog(None, False, False, current_user)
    for c in catalog:
        if c["id"] == connector_id:
            return c
    raise HTTPException(status_code=404, detail="Connector not found")


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List connector categories with counts.
    """
    catalog = await list_catalog(None, False, False, current_user)
    category_counts: Dict[str, int] = {}
    for c in catalog:
        cat = c.get("category", "other")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    return [{"name": name, "count": count} for name, count in category_counts.items()]


@router.get("/companies/{company_id}/status")
async def get_connector_status(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of all connectors for a company.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get connector config from company metadata
    metadata = company.metadata_json or {}
    connectors_config = metadata.get("connectors", {})
    
    statuses = []
    seen_ids = set()
    for provider_id in ConnectorRegistry.get_available_providers():
        config = connectors_config.get(provider_id, {})
        statuses.append({
            "provider_id": provider_id,
            "connected": config.get("connected", False),
            "last_sync": config.get("last_sync"),
            "records_synced": config.get("records_synced", 0),
            "error": config.get("last_error"),
        })
        seen_ids.add(provider_id)
    
    for provider_id, config in connectors_config.items():
        if provider_id not in seen_ids and isinstance(config, dict):
            statuses.append({
                "provider_id": provider_id,
                "connected": config.get("connected", False),
                "last_sync": config.get("last_sync"),
                "records_synced": config.get("records_synced", 0),
                "error": config.get("last_error"),
            })
    
    return {
        "company_id": company_id,
        "connectors": statuses,
    }


@router.post("/companies/{company_id}/connect")
async def connect_provider(
    company_id: int,
    credentials: ConnectorCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Connect a provider to a company using provided credentials.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    provider_id = credentials.provider_id
    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    
    if not connector_class:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    # Create connector and test authentication
    config = ConnectorConfig(
        provider_id=provider_id,
        company_id=company_id,
        credentials=credentials.credentials,
        settings=credentials.settings or {},
    )
    
    connector = connector_class(config)
    
    try:
        auth_success = await connector.authenticate()
        
        if not auth_success:
            raise HTTPException(status_code=401, detail="Authentication failed. Check your credentials.")
        
        # Store credentials securely (encrypted in production)
        metadata = company.metadata_json or {}
        if "connectors" not in metadata:
            metadata["connectors"] = {}
        
        metadata["connectors"][provider_id] = {
            "connected": True,
            "credentials": credentials.credentials,  # Should be encrypted
            "settings": credentials.settings,
            "connected_at": datetime.utcnow().isoformat(),
        }
        
        company.metadata_json = metadata
        db.commit()
        
        return {
            "success": True,
            "provider_id": provider_id,
            "message": f"Successfully connected to {connector.PROVIDER_NAME}",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection error for {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await connector.close()


@router.post("/companies/{company_id}/disconnect/{provider_id}")
async def disconnect_provider(
    company_id: int,
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Disconnect a provider from a company.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metadata = company.metadata_json or {}
    connectors = metadata.get("connectors", {})
    
    if provider_id in connectors:
        del connectors[provider_id]
        metadata["connectors"] = connectors
        company.metadata_json = metadata
        db.commit()
    
    return {
        "success": True,
        "provider_id": provider_id,
        "message": "Provider disconnected",
    }


@router.post("/companies/{company_id}/sync/{provider_id}")
async def sync_provider(
    company_id: int,
    provider_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger a data sync from a connected provider.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    metadata = company.metadata_json or {}
    connectors = metadata.get("connectors", {})
    
    if provider_id not in connectors or not connectors[provider_id].get("connected"):
        raise HTTPException(status_code=400, detail=f"Provider {provider_id} is not connected")
    
    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    if not connector_class:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")
    
    # Get stored credentials
    stored_config = connectors[provider_id]
    config = ConnectorConfig(
        provider_id=provider_id,
        company_id=company_id,
        credentials=stored_config.get("credentials", {}),
        settings=stored_config.get("settings", {}),
    )
    
    connector = connector_class(config)
    
    try:
        result = await connector.sync_all()
        
        # Update sync status in metadata
        connectors[provider_id]["last_sync"] = datetime.utcnow().isoformat()
        connectors[provider_id]["records_synced"] = result.records_synced
        connectors[provider_id]["last_error"] = result.errors[0] if result.errors else None
        
        metadata["connectors"] = connectors
        company.metadata_json = metadata
        
        # Save financial data if sync was successful
        if result.success and result.metadata.get("financials"):
            financials = result.metadata["financials"]
            
            today = datetime.utcnow().date()
            record = FinancialRecord(
                company_id=company_id,
                period_start=today.replace(day=1),
                period_end=today,
                source_type=f"connector_{provider_id}",
                extraction_summary=f"Synced from {connector.PROVIDER_NAME}",
                revenue=financials.get("revenue"),
                payroll=financials.get("payroll"),
                headcount=financials.get("headcount"),
            )
            db.add(record)
        
        db.commit()
        
        return {
            "success": result.success,
            "provider_id": provider_id,
            "records_synced": result.records_synced,
            "errors": result.errors,
            "warnings": result.warnings,
            "sync_completed": result.sync_completed.isoformat() if result.sync_completed else None,
        }
        
    except Exception as e:
        logger.error(f"Sync error for {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await connector.close()


@router.get("/companies/{company_id}/sync-history")
async def get_sync_history(
    company_id: int,
    provider_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get sync history for a company.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Query financial records created by connectors
    query = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id,
        FinancialRecord.source_type.like("connector_%")
    )
    
    if provider_id:
        query = query.filter(FinancialRecord.source_type == f"connector_{provider_id}")
    
    records = query.order_by(FinancialRecord.created_at.desc()).limit(limit).all()
    
    history = []
    for record in records:
        history.append({
            "id": record.id,
            "provider_id": record.source_type.replace("connector_", ""),
            "synced_at": record.created_at.isoformat() if record.created_at else None,
            "period_start": record.period_start.isoformat() if record.period_start else None,
            "period_end": record.period_end.isoformat() if record.period_end else None,
            "summary": record.extraction_summary,
        })
    
    return {
        "company_id": company_id,
        "history": history,
    }
