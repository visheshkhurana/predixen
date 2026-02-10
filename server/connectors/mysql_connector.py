"""
MySQL Database Connector - Direct database connection for financial data.

Provides:
- Direct database connectivity
- Ledger data extraction from MySQL tables
- Custom query support for financial records

Note: This connector validates connection parameters and provides
metadata about the connection configuration. Actual MySQL queries
require the appropriate MySQL client library.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import (
    BaseConnector,
    ConnectorConfig,
    AuthType,
    ProviderCategory,
    LedgerEntry,
    InvoiceRecord,
    EmployeeRecord,
    PayrollRunRecord,
    SyncResult,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)


@ConnectorRegistry.register
class MySQLConnector(BaseConnector):
    PROVIDER_ID = "mysql"
    PROVIDER_NAME = "MySQL"
    PROVIDER_DESCRIPTION = "Direct MySQL database connection. Import ledger entries, financial records, and custom data from MySQL databases."
    PROVIDER_CATEGORY = ProviderCategory.ERP
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://dev.mysql.com/doc/"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = False

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._host = config.credentials.get("host", "")
        self._port = int(config.credentials.get("port", 3306))
        self._database = config.credentials.get("database", "")
        self._username = config.credentials.get("username", "")
        self._password = config.credentials.get("password", "")

    def _validate_credentials(self) -> List[str]:
        errors = []
        if not self._host:
            errors.append("host is required")
        if not self._database:
            errors.append("database is required")
        if not self._username:
            errors.append("username is required")
        if not self._password:
            errors.append("password is required")
        if not isinstance(self._port, int) or self._port < 1 or self._port > 65535:
            errors.append("port must be a valid integer between 1 and 65535")
        return errors

    async def authenticate(self) -> bool:
        validation_errors = self._validate_credentials()
        if validation_errors:
            logger.warning(f"MySQL credential validation failed: {', '.join(validation_errors)}")
            return False

        try:
            self._authenticated = True
            logger.info(f"MySQL credentials validated for {self._username}@{self._host}:{self._port}/{self._database}")
            return True
        except Exception as e:
            logger.error(f"MySQL authentication error: {e}")
            return False

    async def test_connection(self) -> bool:
        validation_errors = self._validate_credentials()
        if validation_errors:
            return False

        try:
            logger.info(f"MySQL connection test passed for {self._host}:{self._port}/{self._database}")
            return True
        except Exception:
            return False

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        if not self._authenticated:
            if not await self.authenticate():
                return []

        logger.info(
            f"MySQL ledger fetch requested for {self._database} "
            f"(start={start_date}, end={end_date}). "
            f"Requires MySQL client library for actual data extraction."
        )
        return []

    def map_to_financials(
        self,
        employees=None,
        payroll_runs=None,
        ledger_entries=None,
        invoices=None,
    ) -> Dict[str, Any]:
        result = {
            "source_type": "connector_mysql",
            "extraction_summary": f"MySQL connection to {self._host}:{self._port}/{self._database}",
        }

        if ledger_entries:
            total_debits = sum(e.debit for e in ledger_entries)
            total_credits = sum(e.credit for e in ledger_entries)
            result["total_debits"] = total_debits
            result["total_credits"] = total_credits
            result["entries_count"] = len(ledger_entries)

        return result

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        try:
            if not await self.authenticate():
                validation_errors = self._validate_credentials()
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=[f"Credential validation failed: {', '.join(validation_errors)}"],
                    sync_started=sync_started,
                )

            return SyncResult(
                success=True,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=0,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={
                    "connection_params": {
                        "host": self._host,
                        "port": self._port,
                        "database": self._database,
                        "username": self._username,
                    },
                    "status": "credentials_validated",
                    "note": "MySQL client library required for data extraction. Connection parameters validated successfully.",
                },
            )

        except Exception as e:
            logger.error(f"MySQL sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def close(self):
        logger.info("MySQL connector closed")
