# Integrations Module
# External service connectors for accounting and CRM

from .base import (
    IntegrationBase,
    IntegrationStatus,
    IntegrationConfig,
    SyncResult,
)

__all__ = [
    "IntegrationBase",
    "IntegrationStatus",
    "IntegrationConfig",
    "SyncResult",
]
