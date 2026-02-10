"""
Payroll and ERP Connector Framework

This module provides a unified interface for connecting to various payroll 
and ERP providers to sync financial data into the Predixen platform.
"""

from .base import BaseConnector, ConnectorConfig, SyncResult
from .registry import ConnectorRegistry

from . import stripe
from . import quickbooks
from . import razorpayx
from . import tally
from . import zoho_books
from . import keka
from . import greythr
from . import google_sheets
from . import rest_api
from . import plaid
from . import hubspot
from . import gusto
from . import xero

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "SyncResult",
    "ConnectorRegistry",
]
