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
from server.core.company_metadata import delete_metadata_value, save_metadata_value
from server.core.encryption import (
    encrypt_credentials,
    decrypt_credentials,
    mask_account_number,
)
from server.models.user import User
from server.models.company import Company
from server.models.financial import FinancialRecord

from server.connectors import ConnectorRegistry, ConnectorConfig, load_all_connectors
from server.connectors.base import ProviderCategory

load_all_connectors()

from server.connectors.razorpayx import redact_account_number

logger = logging.getLogger(__name__)

_ACCOUNT_NUMBER_KEY = "account_number"


def _is_razorpay_family(provider_id: str) -> bool:
    return ConnectorRegistry.canonical_provider_id(provider_id) == "razorpayx"


def _pop_account_number(settings: Dict[str, Any]) -> str:
    """Remove account_number from settings and return the value."""
    found = ""
    for key in list(settings):
        if key.lower().replace("-", "_") != _ACCOUNT_NUMBER_KEY:
            continue
        value = str(settings.pop(key) or "").strip()
        if value and not found:
            found = value
    return found


def _account_from_stored(config: Dict[str, Any]) -> str:
    """Read a RazorpayX account number from memory. Never log the return value."""
    stored = config.get("credentials")
    creds: Dict[str, Any] = {}
    if isinstance(stored, dict):
        creds = stored
    elif isinstance(stored, str) and stored:
        try:
            decrypted = decrypt_credentials(stored)
        except Exception:
            decrypted = None
        if isinstance(decrypted, dict):
            creds = decrypted
    settings = config.get("settings") if isinstance(config.get("settings"), dict) else {}
    return str(creds.get(_ACCOUNT_NUMBER_KEY) or settings.get(_ACCOUNT_NUMBER_KEY) or "").strip()


def _seal_razorpay_config(config: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
    """Keep the RazorpayX account number inside the encrypted credentials blob.

    Other connector secrets are encrypted on connect. A number left in settings
    (or in a legacy plaintext credential dict) is merged into that blob and
    removed from settings. Sample-data configs with no account are left alone.
    """
    updated = dict(config)
    if not _is_razorpay_family(provider_id):
        return updated

    settings = dict(updated["settings"]) if isinstance(updated.get("settings"), dict) else {}
    stored = updated.get("credentials")
    was_encrypted = isinstance(stored, str)
    creds: Dict[str, Any] = {}
    if was_encrypted and stored:
        try:
            decrypted = decrypt_credentials(stored)
        except Exception:
            decrypted = None
        if not isinstance(decrypted, dict):
            if _pop_account_number(settings):
                updated["settings"] = settings
            return updated
        creds = dict(decrypted)
    elif isinstance(stored, dict):
        creds = dict(stored)

    settings_account = _pop_account_number(settings)
    account = str(creds.get(_ACCOUNT_NUMBER_KEY) or settings_account or "").strip()
    if account:
        creds[_ACCOUNT_NUMBER_KEY] = account
    if account and creds and (not was_encrypted or settings_account):
        updated["credentials"] = encrypt_credentials(creds)
    if settings_account:
        updated["settings"] = settings
    return updated


def _safe_account_text(message: Any, account_number: str = "") -> str:
    return redact_account_number(message, account_number)


def _status_row(provider_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    account = _account_from_stored(config) if _is_razorpay_family(provider_id) else ""
    error = config.get("last_error")
    if error:
        error = _safe_account_text(error, account)
    row = {
        "provider_id": provider_id,
        "connected": config.get("connected", False),
        "last_sync": config.get("last_sync"),
        "records_synced": config.get("records_synced", 0),
        "error": error,
    }
    if account:
        row["account_hint"] = mask_account_number(account)
    return row


def _family_ids(provider_id: str) -> List[str]:
    return ConnectorRegistry.provider_ids_for(provider_id)


def _connected_storage_id(connectors: Dict[str, Any], provider_id: str) -> Optional[str]:
    """Storage key that holds a live connection for this provider or an alias."""
    requested = connectors.get(provider_id)
    if isinstance(requested, dict) and requested.get("connected"):
        return provider_id
    for candidate in _family_ids(provider_id):
        config = connectors.get(candidate)
        if isinstance(config, dict) and config.get("connected"):
            return candidate
    return None


def _status_config(connectors: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
    storage_id = _connected_storage_id(connectors, provider_id)
    if storage_id:
        config = connectors.get(storage_id)
        if isinstance(config, dict):
            return config
    config = connectors.get(provider_id)
    return config if isinstance(config, dict) else {}


def _record_provider_id(provider_id: str) -> str:
    """Id written on FinancialRecord.source_type. Aliases share the canonical id."""
    return ConnectorRegistry.canonical_provider_id(provider_id)


def _sample_for(provider_id: str) -> Optional[Dict[str, Any]]:
    if provider_id in SAMPLE_DATA:
        return SAMPLE_DATA[provider_id]
    return SAMPLE_DATA.get(ConnectorRegistry.canonical_provider_id(provider_id))


def _record_sync_failure(db: Session, company_id: int, storage_id: str, message: str) -> None:
    """Persist last_error after a failed sync. The connection stays connected."""
    try:
        db.rollback()
    except Exception:
        logger.exception("rollback before recording sync error failed")
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if company is None:
            return
        connectors = (company.metadata_json or {}).get("connectors") or {}
        current = connectors.get(storage_id)
        if not isinstance(current, dict):
            return
        updated = _seal_razorpay_config(dict(current), storage_id)
        account = _account_from_stored(current)
        updated["last_error"] = _safe_account_text(message, account)[:500]
        save_metadata_value(
            db,
            company,
            ("connectors", storage_id),
            updated,
            commit=True,
        )
    except Exception:
        logger.exception("failed to record connector sync error")
        try:
            db.rollback()
        except Exception:
            pass

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
            company = db.query(Company).filter(
                Company.id == company_id,
                Company.user_id == current_user.id,
            ).first()
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
        conn_meta = _status_config(company_connectors, p["id"])
        if conn_meta and conn_meta.get("connected"):
            public = _status_row(p["id"], conn_meta)
            install_status = {
                "connector_id": p["id"],
                "status": "active",
                "last_sync": public.get("last_sync"),
                "record_count": public.get("records_synced", 0),
                "error_summary": public.get("error"),
            }
            if public.get("account_hint"):
                install_status["account_hint"] = public["account_hint"]
        
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get single connector from catalog.
    """
    catalog = await list_catalog(None, False, False, None, current_user, db)
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
        config = _status_config(connectors_config, provider_id)
        statuses.append(_status_row(provider_id, config))
        seen_ids.add(provider_id)
    
    for provider_id, config in connectors_config.items():
        if provider_id not in seen_ids and isinstance(config, dict):
            statuses.append(_status_row(provider_id, config))
    
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
    
    # RazorpayX account numbers are financial PII. They belong in the encrypted
    # credential blob with the key and secret, not in plaintext settings.
    creds_to_store = dict(credentials.credentials or {})
    settings_to_store = credentials.settings
    account_number = ""
    if _is_razorpay_family(provider_id):
        settings_to_store = dict(credentials.settings or {})
        settings_account = _pop_account_number(settings_to_store)
        account_number = str(creds_to_store.get(_ACCOUNT_NUMBER_KEY) or settings_account or "").strip()
        if account_number:
            creds_to_store[_ACCOUNT_NUMBER_KEY] = account_number

    # Create connector and test authentication
    config = ConnectorConfig(
        provider_id=provider_id,
        company_id=company_id,
        credentials=creds_to_store,
        settings=settings_to_store,
    )
    
    connector = connector_class(config)
    
    try:
        auth_success = await connector.authenticate()

        if not auth_success:
            raise HTTPException(status_code=401, detail="Authentication failed. Check your credentials.")

        # Encrypt sensitive credentials before storing in database
        encrypted_creds = encrypt_credentials(creds_to_store)

        # Write just this provider's entry. A full-blob write here would drop a
        # provider connected by a concurrent request, along with any other
        # feature's metadata key.
        save_metadata_value(
            db,
            company,
            ("connectors", provider_id),
            {
                "connected": True,
                "credentials": encrypted_creds,  # Encrypted string
                "settings": settings_to_store,
                "connected_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Successfully connected provider {provider_id} for company {company_id}")

        payload = {
            "success": True,
            "provider_id": provider_id,
            "message": f"Successfully connected to {connector.PROVIDER_NAME}",
        }
        if account_number:
            payload["account_hint"] = mask_account_number(account_number)
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        safe_error = _safe_account_text(e, account_number)
        logger.error("Connection error for %s: %s", provider_id, safe_error)
        raise HTTPException(status_code=500, detail=safe_error)
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
    
    connectors = (company.metadata_json or {}).get("connectors", {})
    for candidate in _family_ids(provider_id):
        if candidate in connectors:
            delete_metadata_value(db, company, ("connectors", candidate))

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
    storage_id = _connected_storage_id(connectors, provider_id)

    if not storage_id:
        raise HTTPException(status_code=400, detail=f"Provider {provider_id} is not connected")

    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    if not connector_class:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_id}")

    stored_config = connectors[storage_id]
    stored_credentials = stored_config.get("credentials", {})
    connector = None
    account_number = _account_from_stored(stored_config) if _is_razorpay_family(provider_id) else ""

    try:
        if isinstance(stored_credentials, str):
            try:
                credentials_dict = decrypt_credentials(stored_credentials)
            except Exception as e:
                logger.error(
                    "Failed to decrypt credentials for %s: %s",
                    provider_id,
                    _safe_account_text(e, account_number),
                )
                raise RuntimeError(
                    "Failed to decrypt stored credentials. Configuration may be corrupted."
                )
        else:
            credentials_dict = stored_credentials or {}

        if not account_number and isinstance(credentials_dict, dict):
            account_number = str(credentials_dict.get(_ACCOUNT_NUMBER_KEY) or "").strip()

        config = ConnectorConfig(
            provider_id=connector_class.PROVIDER_ID,
            company_id=company_id,
            credentials=credentials_dict,
            settings=stored_config.get("settings") or {},
        )
        connector = connector_class(config)

        result = await connector.sync_all()

        if not result.success:
            error_msg = _safe_account_text(
                result.errors[0] if result.errors else "Connector sync failed",
                account_number,
            )
            logger.warning("Sync validation error for %s: %s", provider_id, error_msg)
            raise ValueError(f"Connector sync validation failed: {error_msg}")

        financial_record = None
        if result.metadata.get("financials"):
            financials = result.metadata["financials"]
            today = datetime.utcnow().date()
            # Canonical id keeps source_type stable when the caller used an alias.
            record_provider_id = _record_provider_id(provider_id)
            financial_record = _build_financial_record(
                company_id, record_provider_id, connector.PROVIDER_NAME, financials, today
            )

            if (financial_record.revenue is None and
                financial_record.cash_balance is None and
                financial_record.payroll is None and
                financial_record.opex is None):
                raise ValueError("Financial record must contain at least one financial metric (revenue, cash_balance, payroll, or opex)")

        updated = _seal_razorpay_config(dict(connectors[storage_id]), storage_id)
        updated["last_sync"] = datetime.utcnow().isoformat()
        updated["records_synced"] = result.records_synced
        updated["last_error"] = None

        logger.info(
            f"Sync completed for provider {provider_id}, company {company_id}: "
            f"{result.records_synced} records synced"
        )

        # commit=False: the sync status must land in the same transaction as
        # the FinancialRecord below, so the caller's commit owns both.
        save_metadata_value(
            db,
            company,
            ("connectors", storage_id),
            updated,
            commit=False,
        )

        if financial_record:
            db.add(financial_record)
            from server.services.sample_data import on_real_financials_written
            on_real_financials_written(db, company_id, commit=False)

        db.commit()

        try:
            from server.services.digital_twin import emit_twin_event
            emit_twin_event(db, company_id, "connector_sync", f"connector:{provider_id}", {
                "provider": provider_id,
                "records_synced": result.records_synced,
                "has_financial_record": financial_record is not None,
            })
        except Exception:
            db.rollback()

        safe_errors = [_safe_account_text(error, account_number) for error in result.errors]
        safe_warnings = [_safe_account_text(warning, account_number) for warning in result.warnings]
        return {
            "success": result.success,
            "provider_id": provider_id,
            "records_synced": result.records_synced,
            "errors": safe_errors,
            "warnings": safe_warnings,
            "sync_completed": result.sync_completed.isoformat() if result.sync_completed else None,
        }

    except ValueError as validation_error:
        safe_error = _safe_account_text(validation_error, account_number)
        logger.error("Sync validation error for %s: %s", provider_id, safe_error)
        _record_sync_failure(db, company_id, storage_id, safe_error)
        raise HTTPException(status_code=400, detail=safe_error)
    except Exception as e:
        safe_error = _safe_account_text(e, account_number)
        logger.error("Sync error for %s: %s", provider_id, safe_error)
        _record_sync_failure(db, company_id, storage_id, safe_error)
        raise HTTPException(status_code=500, detail=safe_error)
    finally:
        if connector is not None:
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
        source_types = [f"connector_{pid}" for pid in _family_ids(provider_id)]
        query = query.filter(FinancialRecord.source_type.in_(source_types))
    
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

    sample = _sample_for(provider_id)
    if not sample:
        raise HTTPException(status_code=400, detail=f"No sample data available for {provider_id}")

    today = datetime.utcnow().date()
    connector_class = ConnectorRegistry.get_connector_class(provider_id)
    provider_name = connector_class.PROVIDER_NAME if connector_class else provider_id
    record_provider_id = _record_provider_id(provider_id)

    record = _build_financial_record(company_id, record_provider_id, provider_name, sample, today)
    db.add(record)

    save_metadata_value(
        db,
        company,
        ("connectors", provider_id),
        {
            "connected": True,
            "credentials": {"mode": "sample_data"},
            "connected_at": datetime.utcnow().isoformat(),
            "last_sync": datetime.utcnow().isoformat(),
            "records_synced": sum(1 for v in sample.values() if v is not None and isinstance(v, (int, float))),
            "sample_mode": True,
        },
    )

    stored = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id,
        FinancialRecord.source_type == f"connector_{record_provider_id}",
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
