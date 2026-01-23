"""
Payroll and ERP Connector Framework

This module provides a unified interface for connecting to various payroll 
and ERP providers to sync financial data into the Predixen platform.
"""

from .base import BaseConnector, ConnectorConfig, SyncResult
from .registry import ConnectorRegistry

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "SyncResult",
    "ConnectorRegistry",
]
