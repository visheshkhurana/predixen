"""
Accounting integrations: QuickBooks, Xero, etc.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import IntegrationBase, IntegrationConfig, IntegrationStatus, SyncResult

logger = logging.getLogger(__name__)


@dataclass
class AccountingData:
    """Normalized accounting data structure."""
    period_start: datetime
    period_end: datetime
    revenue: float
    cogs: float
    gross_profit: float
    operating_expenses: float
    payroll: float
    net_income: float
    cash_balance: float
    accounts_receivable: float
    accounts_payable: float
    inventory: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "revenue": self.revenue,
            "cogs": self.cogs,
            "gross_profit": self.gross_profit,
            "operating_expenses": self.operating_expenses,
            "payroll": self.payroll,
            "net_income": self.net_income,
            "cash_balance": self.cash_balance,
            "accounts_receivable": self.accounts_receivable,
            "accounts_payable": self.accounts_payable,
            "inventory": self.inventory,
        }


class QuickBooksIntegration(IntegrationBase):
    """QuickBooks Online integration."""
    
    PROVIDER_NAME = "quickbooks"
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        if config is None:
            config = IntegrationConfig(provider=self.PROVIDER_NAME)
        super().__init__(config)
    
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to QuickBooks using OAuth2.
        
        Credentials should contain:
        - client_id: OAuth client ID
        - client_secret: OAuth client secret
        - refresh_token: OAuth refresh token
        - realm_id: QuickBooks company ID
        """
        try:
            # In production, this would exchange tokens with QuickBooks API
            self.config.api_key = credentials.get("access_token")
            self.config.refresh_token = credentials.get("refresh_token")
            self.config.company_id = credentials.get("realm_id")
            self._status = IntegrationStatus.CONNECTED
            logger.info(f"Connected to QuickBooks: {self.config.company_id}")
            return True
        except Exception as e:
            logger.error(f"QuickBooks connection failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from QuickBooks."""
        self.config.api_key = None
        self.config.refresh_token = None
        self._status = IntegrationStatus.NOT_CONNECTED
        return True
    
    async def sync(self) -> SyncResult:
        """
        Sync financial data from QuickBooks.
        Fetches P&L and Balance Sheet data.
        """
        if self._status != IntegrationStatus.CONNECTED:
            return SyncResult(
                success=False,
                records_synced=0,
                errors=["Not connected to QuickBooks"],
            )
        
        try:
            self._status = IntegrationStatus.SYNCING
            
            # In production, call QuickBooks API:
            # - GET /v3/company/{realmId}/reports/ProfitAndLoss
            # - GET /v3/company/{realmId}/reports/BalanceSheet
            
            # Placeholder for actual API calls
            data = await self._fetch_reports()
            
            self.config.last_sync = datetime.utcnow()
            self._status = IntegrationStatus.CONNECTED
            
            return SyncResult(
                success=True,
                records_synced=len(data),
                errors=[],
                data={"accounting": data},
            )
        except Exception as e:
            logger.error(f"QuickBooks sync failed: {e}")
            self._status = IntegrationStatus.ERROR
            return SyncResult(
                success=False,
                records_synced=0,
                errors=[str(e)],
            )
    
    async def test_connection(self) -> bool:
        """Test QuickBooks connection by fetching company info."""
        if not self.config.api_key:
            return False
        
        try:
            # In production: GET /v3/company/{realmId}/companyinfo/{realmId}
            return True
        except Exception:
            self._status = IntegrationStatus.EXPIRED
            return False
    
    async def _fetch_reports(self) -> List[AccountingData]:
        """Fetch and parse QuickBooks reports."""
        # Placeholder - in production, call actual QuickBooks API
        return []
    
    async def get_profit_loss(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[Dict[str, float]]:
        """Fetch P&L report for a period."""
        if self._status != IntegrationStatus.CONNECTED:
            return None
        
        # In production: call QuickBooks P&L API
        return None
    
    async def get_balance_sheet(self, as_of: datetime) -> Optional[Dict[str, float]]:
        """Fetch Balance Sheet as of a date."""
        if self._status != IntegrationStatus.CONNECTED:
            return None
        
        # In production: call QuickBooks Balance Sheet API
        return None


class XeroIntegration(IntegrationBase):
    """Xero accounting integration."""
    
    PROVIDER_NAME = "xero"
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        if config is None:
            config = IntegrationConfig(provider=self.PROVIDER_NAME)
        super().__init__(config)
    
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """Connect to Xero using OAuth2."""
        try:
            self.config.api_key = credentials.get("access_token")
            self.config.refresh_token = credentials.get("refresh_token")
            self.config.company_id = credentials.get("tenant_id")
            self._status = IntegrationStatus.CONNECTED
            logger.info(f"Connected to Xero: {self.config.company_id}")
            return True
        except Exception as e:
            logger.error(f"Xero connection failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Xero."""
        self.config.api_key = None
        self.config.refresh_token = None
        self._status = IntegrationStatus.NOT_CONNECTED
        return True
    
    async def sync(self) -> SyncResult:
        """Sync financial data from Xero."""
        if self._status != IntegrationStatus.CONNECTED:
            return SyncResult(
                success=False,
                records_synced=0,
                errors=["Not connected to Xero"],
            )
        
        try:
            self._status = IntegrationStatus.SYNCING
            
            # In production, call Xero API
            data = []
            
            self.config.last_sync = datetime.utcnow()
            self._status = IntegrationStatus.CONNECTED
            
            return SyncResult(
                success=True,
                records_synced=len(data),
                errors=[],
                data={"accounting": data},
            )
        except Exception as e:
            logger.error(f"Xero sync failed: {e}")
            self._status = IntegrationStatus.ERROR
            return SyncResult(
                success=False,
                records_synced=0,
                errors=[str(e)],
            )
    
    async def test_connection(self) -> bool:
        """Test Xero connection."""
        return self._status == IntegrationStatus.CONNECTED


def get_accounting_integration(provider: str) -> Optional[IntegrationBase]:
    """Factory to get accounting integration by provider name."""
    providers = {
        "quickbooks": QuickBooksIntegration,
        "xero": XeroIntegration,
    }
    
    integration_class = providers.get(provider.lower())
    if integration_class:
        return integration_class()
    return None
