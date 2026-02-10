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

import server.connectors

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
        
        if result.success and result.metadata.get("financials"):
            financials = result.metadata["financials"]
            today = datetime.utcnow().date()
            record = _build_financial_record(company_id, provider_id, connector.PROVIDER_NAME, financials, today)
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


def _build_financial_record(company_id: int, provider_id: str, provider_name: str, financials: Dict[str, Any], today) -> FinancialRecord:
    revenue = financials.get("revenue")
    cogs = financials.get("cogs")
    opex = financials.get("opex")
    payroll = financials.get("payroll")
    other_costs = financials.get("other_costs")
    cash_balance = financials.get("cash_balance")

    gross_profit = None
    gross_margin = None
    if revenue is not None and cogs is not None:
        gross_profit = revenue - cogs
        gross_margin = (gross_profit / revenue * 100) if revenue else None

    operating_income = None
    operating_margin = None
    total_expenses = sum(v for v in [cogs, opex, payroll, other_costs] if v is not None)
    if revenue is not None and total_expenses:
        operating_income = revenue - total_expenses
        operating_margin = (operating_income / revenue * 100) if revenue else None

    net_burn = financials.get("net_burn")
    if net_burn is None and revenue is not None and total_expenses:
        net_burn = total_expenses - revenue

    runway_months = None
    if cash_balance and net_burn and net_burn > 0:
        runway_months = cash_balance / net_burn

    mrr = financials.get("mrr")
    arr = financials.get("arr")
    if mrr is not None and arr is None:
        arr = mrr * 12

    record = FinancialRecord(
        company_id=company_id,
        period_start=today.replace(day=1),
        period_end=today,
        source_type=f"connector_{provider_id}",
        extraction_summary=financials.get("extraction_summary", f"Synced from {provider_name}"),
        revenue=revenue,
        cogs=cogs,
        opex=opex,
        payroll=payroll,
        other_costs=other_costs,
        cash_balance=cash_balance,
        mrr=mrr,
        arr=arr,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        operating_income=operating_income,
        operating_margin=operating_margin,
        net_burn=net_burn,
        runway_months=runway_months,
        burn_multiple=financials.get("burn_multiple"),
        headcount=financials.get("headcount"),
        customers=financials.get("customers"),
        mom_growth=financials.get("mom_growth"),
        yoy_growth=financials.get("yoy_growth"),
        ndr=financials.get("ndr"),
        ltv=financials.get("ltv"),
        cac=financials.get("cac"),
        ltv_cac_ratio=financials.get("ltv_cac_ratio"),
        arpu=financials.get("arpu"),
        marketing_expense=financials.get("marketing_expense"),
    )
    return record


SAMPLE_DATA: Dict[str, Dict[str, Any]] = {
    "stripe": {
        "revenue": 185000, "mrr": 15400, "arr": 184800,
        "customers": 312, "cash_balance": 420000,
        "cogs": 18500, "opex": 45000, "payroll": 95000,
        "extraction_summary": "Sample: Stripe MRR/ARR from 312 customers, 847 invoices",
    },
    "quickbooks": {
        "revenue": 210000, "cogs": 42000, "opex": 63000, "payroll": 98000,
        "cash_balance": 380000, "other_costs": 12000,
        "extraction_summary": "Sample: QuickBooks P&L and balance sheet data",
    },
    "xero": {
        "revenue": 195000, "cogs": 39000, "opex": 58000, "payroll": 92000,
        "cash_balance": 345000,
        "extraction_summary": "Sample: Xero invoices, P&L, and bank transactions",
    },
    "zoho_books": {
        "revenue": 145000, "cogs": 29000, "opex": 43000,
        "cash_balance": 260000,
        "extraction_summary": "Sample: Zoho Books invoices and chart of accounts",
    },
    "freshbooks": {
        "revenue": 78000, "opex": 23000, "payroll": 45000,
        "cash_balance": 190000,
        "extraction_summary": "Sample: FreshBooks invoices, expenses, time entries",
    },
    "wave": {
        "revenue": 62000, "opex": 18000, "payroll": 38000,
        "cash_balance": 145000,
        "extraction_summary": "Sample: Wave invoices and transactions via GraphQL",
    },
    "bench": {
        "revenue": 130000, "cogs": 26000, "opex": 39000, "payroll": 72000,
        "cash_balance": 290000,
        "extraction_summary": "Sample: Bench categorized monthly financials",
    },
    "chargebee": {
        "revenue": 168000, "mrr": 14000, "customers": 280,
        "extraction_summary": "Sample: Chargebee subscriptions, MRR, 280 customers",
    },
    "recurly": {
        "revenue": 142000, "mrr": 11800, "customers": 195,
        "extraction_summary": "Sample: Recurly subscriptions and revenue recognition",
    },
    "shopify": {
        "revenue": 230000, "cogs": 92000, "customers": 1840,
        "extraction_summary": "Sample: Shopify orders, revenue, 1840 customers",
    },
    "hubspot": {
        "revenue": 320000, "customers": 48,
        "extraction_summary": "Sample: HubSpot 48 closed deals, pipeline $1.2M",
    },
    "salesforce": {
        "revenue": 450000, "customers": 67,
        "extraction_summary": "Sample: Salesforce 67 closed opportunities via SOQL",
    },
    "pipedrive": {
        "revenue": 175000, "customers": 34,
        "extraction_summary": "Sample: Pipedrive 34 won deals, pipeline $650K",
    },
    "close_crm": {
        "revenue": 98000, "customers": 22,
        "extraction_summary": "Sample: Close CRM 22 won opportunities",
    },
    "gusto": {
        "payroll": 112000, "headcount": 18,
        "extraction_summary": "Sample: Gusto payroll for 18 employees",
    },
    "rippling": {
        "payroll": 145000, "headcount": 24,
        "extraction_summary": "Sample: Rippling payroll for 24 workers",
    },
    "deel": {
        "payroll": 68000, "headcount": 12,
        "extraction_summary": "Sample: Deel contracts and payments for 12 contractors",
    },
    "razorpayx": {
        "payroll": 85000, "headcount": 15,
        "extraction_summary": "Sample: RazorpayX payouts for 15 employees",
    },
    "keka": {
        "payroll": 72000, "headcount": 14,
        "extraction_summary": "Sample: Keka payroll summaries for 14 employees",
    },
    "greythr": {
        "payroll": 55000, "headcount": 11,
        "extraction_summary": "Sample: greytHR payroll for 11 employees",
    },
    "plaid": {
        "cash_balance": 520000,
        "extraction_summary": "Sample: Plaid 3 bank accounts, 245 transactions",
    },
    "mercury": {
        "cash_balance": 380000,
        "extraction_summary": "Sample: Mercury 2 accounts, real-time cash position",
    },
    "brex": {
        "opex": 34000, "cash_balance": 290000,
        "extraction_summary": "Sample: Brex card transactions and expense categories",
    },
    "ramp": {
        "opex": 28000,
        "extraction_summary": "Sample: Ramp transactions across 4 departments",
    },
    "google_analytics": {
        "customers": 12500,
        "extraction_summary": "Sample: GA4 45K sessions, 12.5K users, 3.2% conversion",
    },
    "mixpanel": {
        "customers": 8400,
        "extraction_summary": "Sample: Mixpanel 8.4K active users, 67% retention",
    },
    "profitwell": {
        "mrr": 16200, "customers": 340,
        "extraction_summary": "Sample: ProfitWell MRR $16.2K, 2.1% churn, 340 subscribers",
    },
    "amplitude": {
        "customers": 15200,
        "extraction_summary": "Sample: Amplitude 15.2K users, cohort retention analysis",
    },
    "tally": {
        "revenue": 95000, "cogs": 38000, "opex": 28000,
        "extraction_summary": "Sample: Tally ledger entries via XML API",
    },
    "netsuite": {
        "revenue": 520000, "cogs": 156000, "opex": 130000, "payroll": 180000,
        "cash_balance": 890000,
        "extraction_summary": "Sample: NetSuite full financial suite via OAuth 1.0",
    },
    "mysql": {
        "revenue": 165000, "customers": 450,
        "extraction_summary": "Sample: MySQL direct query - revenue and customer data",
    },
    "rest_api": {
        "revenue": 88000,
        "extraction_summary": "Sample: REST API custom endpoint financial data",
    },
    "google_sheets": {
        "revenue": 72000, "cogs": 14400, "opex": 21600, "payroll": 36000,
        "extraction_summary": "Sample: Google Sheets imported financial data",
    },
}


@router.post("/companies/{company_id}/test-sample/{provider_id}")
async def test_with_sample_data(
    company_id: int,
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    sample = SAMPLE_DATA.get(provider_id)
    if not sample:
        raise HTTPException(status_code=400, detail=f"No sample data available for {provider_id}")

    today = datetime.utcnow().date()
    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    provider_name = connector_class.PROVIDER_NAME if connector_class else provider_id

    record = _build_financial_record(company_id, provider_id, provider_name, sample, today)
    db.add(record)

    metadata = company.metadata_json or {}
    if "connectors" not in metadata:
        metadata["connectors"] = {}

    metadata["connectors"][provider_id] = {
        "connected": True,
        "credentials": {"mode": "sample_data"},
        "connected_at": datetime.utcnow().isoformat(),
        "last_sync": datetime.utcnow().isoformat(),
        "records_synced": sum(1 for v in sample.values() if v is not None and isinstance(v, (int, float))),
        "sample_mode": True,
    }
    company.metadata_json = metadata
    db.commit()

    stored = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id,
        FinancialRecord.source_type == f"connector_{provider_id}",
    ).order_by(FinancialRecord.created_at.desc()).first()

    verification = {}
    if stored:
        for field_name in ["revenue", "cogs", "opex", "payroll", "cash_balance", "mrr", "arr",
                           "gross_profit", "gross_margin", "operating_income", "operating_margin",
                           "net_burn", "runway_months", "headcount", "customers"]:
            db_val = getattr(stored, field_name, None)
            sample_val = sample.get(field_name)
            if db_val is not None or sample_val is not None:
                verification[field_name] = {
                    "input": sample_val,
                    "stored": db_val,
                    "computed": sample_val is None and db_val is not None,
                }

    return {
        "success": True,
        "provider_id": provider_id,
        "provider_name": provider_name,
        "sample_data_used": {k: v for k, v in sample.items() if k != "extraction_summary"},
        "record_id": stored.id if stored else None,
        "extraction_summary": sample.get("extraction_summary", ""),
        "verification": verification,
        "message": f"Sample data synced for {provider_name}. Financial record created and verified.",
    }


@router.get("/sample-providers")
async def list_sample_providers(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    result = []
    for pid, data in SAMPLE_DATA.items():
        connector_class = ConnectorRegistry.get_connector_class(pid)
        name = connector_class.PROVIDER_NAME if connector_class else pid
        metrics = [k for k, v in data.items() if isinstance(v, (int, float))]
        result.append({
            "provider_id": pid,
            "provider_name": name,
            "available_metrics": metrics,
            "summary": data.get("extraction_summary", ""),
        })
    return result
