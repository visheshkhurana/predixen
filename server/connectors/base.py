"""
Base connector interface for payroll and ERP integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


class ProviderCategory(str, Enum):
    PAYROLL = "payroll"
    ERP = "erp"
    ACCOUNTING = "accounting"
    CRM = "crm"
    HRIS = "hris"


@dataclass
class ConnectorConfig:
    """Configuration for a connector instance."""
    provider_id: str
    company_id: int
    credentials: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    

@dataclass
class EmployeeRecord:
    """Normalized employee record from payroll systems."""
    external_id: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    salary: Optional[float] = None
    join_date: Optional[datetime] = None
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PayrollRunRecord:
    """Normalized payroll run record."""
    external_id: str
    period_start: datetime
    period_end: datetime
    total_gross: float
    total_deductions: float
    total_net: float
    employee_count: int
    currency: str = "INR"
    status: str = "completed"
    breakdown: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerEntry:
    """Normalized ledger/accounting entry."""
    external_id: str
    date: datetime
    account_code: str
    account_name: str
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvoiceRecord:
    """Normalized invoice record from ERP/accounting systems."""
    external_id: str
    date: datetime
    due_date: Optional[datetime] = None
    customer_name: Optional[str] = None
    amount: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "INR"
    status: str = "pending"
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a data sync operation."""
    success: bool
    provider_id: str
    sync_type: str  # employees, payroll, ledger, invoices
    records_synced: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sync_started: datetime = field(default_factory=datetime.utcnow)
    sync_completed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider_id": self.provider_id,
            "sync_type": self.sync_type,
            "records_synced": self.records_synced,
            "records_failed": self.records_failed,
            "errors": self.errors,
            "warnings": self.warnings,
            "sync_started": self.sync_started.isoformat() if self.sync_started else None,
            "sync_completed": self.sync_completed.isoformat() if self.sync_completed else None,
            "metadata": self.metadata,
        }


class BaseConnector(ABC):
    """
    Abstract base class for all payroll/ERP connectors.
    
    Each connector must implement:
    - authenticate(): Validate credentials and establish connection
    - test_connection(): Quick test to verify connectivity
    - fetch_employees(): Get employee list (for payroll connectors)
    - fetch_payroll_runs(): Get payroll run history
    - fetch_ledger(): Get ledger/journal entries (for ERP/accounting)
    - fetch_invoices(): Get invoice data
    - map_to_financials(): Convert fetched data to internal financial schema
    """
    
    # Provider metadata - override in subclasses
    PROVIDER_ID: str = "base"
    PROVIDER_NAME: str = "Base Connector"
    PROVIDER_DESCRIPTION: str = ""
    PROVIDER_CATEGORY: ProviderCategory = ProviderCategory.PAYROLL
    AUTH_TYPE: AuthType = AuthType.API_KEY
    DOCS_URL: str = ""
    
    # Capabilities - override to indicate supported operations
    SUPPORTS_EMPLOYEES: bool = False
    SUPPORTS_PAYROLL: bool = False
    SUPPORTS_LEDGER: bool = False
    SUPPORTS_INVOICES: bool = False
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._authenticated = False
        self._last_sync: Optional[datetime] = None
    
    @property
    def is_authenticated(self) -> bool:
        return self._authenticated
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the provider using configured credentials.
        Returns True if authentication successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Quick connectivity test without full authentication.
        Useful for validating API keys or OAuth tokens.
        """
        pass
    
    async def fetch_employees(self) -> List[EmployeeRecord]:
        """Fetch employee list from payroll system."""
        if not self.SUPPORTS_EMPLOYEES:
            logger.warning(f"{self.PROVIDER_ID} does not support employee fetching")
            return []
        raise NotImplementedError("Subclass must implement fetch_employees")
    
    async def fetch_payroll_runs(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """Fetch payroll run history."""
        if not self.SUPPORTS_PAYROLL:
            logger.warning(f"{self.PROVIDER_ID} does not support payroll fetching")
            return []
        raise NotImplementedError("Subclass must implement fetch_payroll_runs")
    
    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        """Fetch ledger/journal entries from ERP/accounting system."""
        if not self.SUPPORTS_LEDGER:
            logger.warning(f"{self.PROVIDER_ID} does not support ledger fetching")
            return []
        raise NotImplementedError("Subclass must implement fetch_ledger")
    
    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        """Fetch invoice data."""
        if not self.SUPPORTS_INVOICES:
            logger.warning(f"{self.PROVIDER_ID} does not support invoice fetching")
            return []
        raise NotImplementedError("Subclass must implement fetch_invoices")
    
    def map_to_financials(
        self,
        employees: List[EmployeeRecord] = None,
        payroll_runs: List[PayrollRunRecord] = None,
        ledger_entries: List[LedgerEntry] = None,
        invoices: List[InvoiceRecord] = None
    ) -> Dict[str, Any]:
        """
        Map fetched data to internal financial schema.
        
        Returns a dict compatible with FinancialRecord model:
        - revenue, cogs, opex, payroll, cash_balance, etc.
        """
        result = {
            "source_type": f"connector_{self.PROVIDER_ID}",
            "extraction_summary": f"Synced from {self.PROVIDER_NAME}",
        }
        
        # Calculate payroll totals
        if payroll_runs:
            total_payroll = sum(run.total_net for run in payroll_runs)
            avg_monthly_payroll = total_payroll / max(len(payroll_runs), 1)
            result["payroll"] = avg_monthly_payroll
            result["headcount"] = payroll_runs[-1].employee_count if payroll_runs else None
        
        # Calculate revenue from invoices
        if invoices:
            total_revenue = sum(inv.total for inv in invoices if inv.status in ["paid", "completed"])
            result["revenue"] = total_revenue
        
        # Process ledger entries for expense categories
        if ledger_entries:
            expense_categories = {}
            for entry in ledger_entries:
                if entry.category:
                    expense_categories[entry.category] = (
                        expense_categories.get(entry.category, 0) + entry.debit
                    )
            result["expense_breakdown"] = expense_categories
        
        return result
    
    async def sync_all(self) -> SyncResult:
        """
        Perform a full sync of all supported data types.
        """
        sync_started = datetime.utcnow()
        errors = []
        warnings = []
        total_records = 0
        
        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed"],
                    sync_started=sync_started,
                )
            
            employees = []
            payroll_runs = []
            ledger_entries = []
            invoices = []
            
            if self.SUPPORTS_EMPLOYEES:
                try:
                    employees = await self.fetch_employees()
                    total_records += len(employees)
                except Exception as e:
                    errors.append(f"Employee fetch failed: {str(e)}")
            
            if self.SUPPORTS_PAYROLL:
                try:
                    payroll_runs = await self.fetch_payroll_runs()
                    total_records += len(payroll_runs)
                except Exception as e:
                    errors.append(f"Payroll fetch failed: {str(e)}")
            
            if self.SUPPORTS_LEDGER:
                try:
                    ledger_entries = await self.fetch_ledger()
                    total_records += len(ledger_entries)
                except Exception as e:
                    errors.append(f"Ledger fetch failed: {str(e)}")
            
            if self.SUPPORTS_INVOICES:
                try:
                    invoices = await self.fetch_invoices()
                    total_records += len(invoices)
                except Exception as e:
                    errors.append(f"Invoice fetch failed: {str(e)}")
            
            # Map to internal schema
            financials = self.map_to_financials(
                employees=employees,
                payroll_runs=payroll_runs,
                ledger_entries=ledger_entries,
                invoices=invoices,
            )
            
            self._last_sync = datetime.utcnow()
            
            return SyncResult(
                success=len(errors) == 0,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=total_records,
                errors=errors,
                warnings=warnings,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={"financials": financials},
            )
            
        except Exception as e:
            logger.error(f"Sync failed for {self.PROVIDER_ID}: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider metadata for UI display."""
        return {
            "id": self.PROVIDER_ID,
            "name": self.PROVIDER_NAME,
            "description": self.PROVIDER_DESCRIPTION,
            "category": self.PROVIDER_CATEGORY.value,
            "auth_type": self.AUTH_TYPE.value,
            "docs_url": self.DOCS_URL,
            "capabilities": {
                "employees": self.SUPPORTS_EMPLOYEES,
                "payroll": self.SUPPORTS_PAYROLL,
                "ledger": self.SUPPORTS_LEDGER,
                "invoices": self.SUPPORTS_INVOICES,
            },
        }
