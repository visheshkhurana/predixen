"""
Payroll and ERP Connector Framework

This module provides a unified interface for connecting to various payroll 
and ERP providers to sync financial data into the FounderConsole platform.
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
from . import salesforce
from . import google_analytics
from . import pipedrive
from . import close_crm
from . import mixpanel
from . import mercury
from . import brex
from . import ramp
from . import shopify
from . import mysql_connector
from . import freshbooks
from . import wave
from . import bench
from . import chargebee
from . import recurly
from . import rippling
from . import deel
from . import netsuite
from . import profitwell
from . import amplitude

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "SyncResult",
    "ConnectorRegistry",
]
