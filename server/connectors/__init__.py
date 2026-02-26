"""
Payroll and ERP Connector Framework

This module provides a unified interface for connecting to various payroll 
and ERP providers to sync financial data into the FounderConsole platform.

Connectors are lazy-loaded on first access to speed up server startup.
"""

from .base import BaseConnector, ConnectorConfig, SyncResult
from .registry import ConnectorRegistry

_CONNECTOR_MODULES = [
    "stripe", "quickbooks", "razorpayx", "tally", "zoho_books",
    "keka", "greythr", "google_sheets", "rest_api", "plaid",
    "hubspot", "gusto", "xero", "salesforce", "google_analytics",
    "pipedrive", "close_crm", "mixpanel", "mercury", "brex",
    "ramp", "shopify", "mysql_connector", "freshbooks", "wave",
    "bench", "chargebee", "recurly", "rippling", "deel",
    "netsuite", "profitwell", "amplitude",
]

_connectors_loaded = False

def load_all_connectors():
    global _connectors_loaded
    if _connectors_loaded:
        return
    import importlib
    import logging
    logger = logging.getLogger(__name__)
    for name in _CONNECTOR_MODULES:
        try:
            importlib.import_module(f".{name}", package=__name__)
            logger.info(f"Registered connector: {name}")
        except Exception as e:
            logger.warning(f"Failed to load connector {name}: {e}")
    _connectors_loaded = True

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "SyncResult",
    "ConnectorRegistry",
    "load_all_connectors",
]
