"""
Capability Discovery Service
Discovers available entities and fields from connected data sources.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from server.models import RawDataEvent
from server.models.connector_capability import ConnectorCapability

logger = logging.getLogger(__name__)


STRIPE_CAPABILITIES = {
    "entities": ["invoices", "subscriptions", "customers", "charges", "refunds", "products"],
    "fields": {
        "invoice.amount": "present",
        "invoice.amount_paid": "present",
        "invoice.status": "present",
        "invoice.currency": "present",
        "subscription.plan_amount": "present",
        "subscription.status": "present",
        "subscription.items": "present",
        "customer.id": "present",
        "customer.email": "present",
        "charge.amount": "present",
        "refund.amount": "present",
    },
    "time_field": "created",
    "supports_webhooks": True,
    "supports_incremental": True,
}

GA4_CAPABILITIES = {
    "entities": ["sessions", "users", "events", "conversions"],
    "metrics": ["sessions", "activeUsers", "conversions", "screenPageViews", "bounceRate"],
    "dimensions": ["date", "country", "deviceCategory", "sessionSource"],
    "fields": {
        "session.session_count": "present",
        "user.user_count": "present",
        "conversion.conversion_count": "present",
    },
    "time_field": "date",
    "supports_webhooks": False,
    "supports_incremental": True,
}

QUICKBOOKS_CAPABILITIES = {
    "entities": ["accounts", "transactions", "expenses", "invoices", "vendors", "customers"],
    "account_types": ["Expense", "OtherExpense", "CostOfGoodsSold", "Income", "Bank"],
    "fields": {
        "transaction.amount": "present",
        "transaction.account_type": "present",
        "expense.amount": "present",
        "invoice.total": "present",
    },
    "time_field": "txn_date",
    "supports_webhooks": True,
    "supports_incremental": True,
}


class CapabilityDiscovery:
    """
    Discovers and stores capabilities from connected data sources.
    """
    
    @staticmethod
    def discover_for_adapter(
        adapter_key: str,
        config: Dict[str, Any],
        db: Session,
        company_id: int,
        data_source_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Discover capabilities for a specific adapter.
        Uses known schemas for common connectors, infers from data for others.
        """
        if adapter_key == "stripe":
            capabilities = STRIPE_CAPABILITIES.copy()
        elif adapter_key == "ga4":
            capabilities = GA4_CAPABILITIES.copy()
        elif adapter_key == "quickbooks":
            capabilities = QUICKBOOKS_CAPABILITIES.copy()
        elif adapter_key == "google_sheets":
            capabilities = CapabilityDiscovery._infer_from_events(db, company_id, "google_sheets")
        else:
            capabilities = CapabilityDiscovery._infer_from_events(db, company_id, adapter_key)
        
        CapabilityDiscovery._store_capabilities(
            db, company_id, adapter_key, data_source_id, capabilities
        )
        
        return capabilities
    
    @staticmethod
    def _infer_from_events(
        db: Session,
        company_id: int,
        source_connector: str,
        sample_size: int = 200
    ) -> Dict[str, Any]:
        """
        Infer capabilities from RawDataEvents samples.
        """
        events = db.query(RawDataEvent).filter(
            RawDataEvent.company_id == company_id,
            RawDataEvent.source_connector == source_connector
        ).limit(sample_size).all()
        
        if not events:
            return {
                "entities": [],
                "fields": {},
                "columns": [],
                "time_field": None,
                "inferred": True,
            }
        
        event_types = set()
        all_fields = {}
        columns = set()
        time_column = None
        
        TIME_COLUMN_NAMES = ["date", "timestamp", "created_at", "time", "period", "month", "day"]
        
        for event in events:
            if event.event_type:
                event_types.add(event.event_type)
            
            if event.data and isinstance(event.data, dict):
                for key, value in event.data.items():
                    columns.add(key)
                    field_key = f"{event.event_type or 'row'}.{key}"
                    all_fields[field_key] = "present"
                    
                    if key.lower() in TIME_COLUMN_NAMES and not time_column:
                        time_column = key
        
        return {
            "entities": list(event_types) if event_types else ["row"],
            "fields": all_fields,
            "columns": sorted(list(columns)),
            "time_field": time_column,
            "time_column": time_column,
            "inferred": True,
            "sample_count": len(events),
        }
    
    @staticmethod
    def _store_capabilities(
        db: Session,
        company_id: int,
        adapter_key: str,
        data_source_id: Optional[int],
        capabilities: Dict[str, Any]
    ) -> ConnectorCapability:
        """
        Store or update capabilities in the database.
        """
        existing = db.query(ConnectorCapability).filter(
            ConnectorCapability.company_id == company_id,
            ConnectorCapability.adapter_key == adapter_key
        ).first()
        
        if existing:
            existing.capabilities = capabilities
            existing.discovered_at = datetime.utcnow()
            existing.data_source_id = data_source_id
            db.commit()
            return existing
        else:
            capability = ConnectorCapability(
                company_id=company_id,
                adapter_key=adapter_key,
                data_source_id=data_source_id,
                capabilities=capabilities,
            )
            db.add(capability)
            db.commit()
            db.refresh(capability)
            return capability
    
    @staticmethod
    def get_all_capabilities(db: Session, company_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get all stored capabilities for a company.
        
        Returns:
            Dict mapping adapter_key to capabilities
        """
        capabilities = db.query(ConnectorCapability).filter(
            ConnectorCapability.company_id == company_id
        ).all()
        
        return {
            cap.adapter_key: cap.capabilities
            for cap in capabilities
        }
    
    @staticmethod
    def get_capability(
        db: Session,
        company_id: int,
        adapter_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get capabilities for a specific adapter."""
        cap = db.query(ConnectorCapability).filter(
            ConnectorCapability.company_id == company_id,
            ConnectorCapability.adapter_key == adapter_key
        ).first()
        
        return cap.capabilities if cap else None
