"""
RazorpayX Payroll Connector

Integrates with RazorpayX Payroll (Opfin) API to fetch:
- Employee data
- Payroll runs and salary disbursements
- Statutory payments (PF, ESI, TDS)

API Documentation: https://documenter.getpostman.com/ (RazorpayX Payroll collection)
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import (
    BaseConnector, 
    ConnectorConfig, 
    AuthType, 
    ProviderCategory,
    EmployeeRecord,
    PayrollRunRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.razorpay.com/v1"  # RazorpayX API base


@ConnectorRegistry.register
class RazorpayXConnector(BaseConnector):
    """
    RazorpayX Payroll connector for syncing payroll and employee data.
    
    Authentication uses API key/secret (Basic Auth).
    """
    
    PROVIDER_ID = "razorpayx_payroll"
    PROVIDER_NAME = "RazorpayX Payroll"
    PROVIDER_DESCRIPTION = "Sync payroll data, employee salaries, and statutory payments from RazorpayX"
    PROVIDER_CATEGORY = ProviderCategory.PAYROLL
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://razorpay.com/docs/payroll/"
    
    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.credentials.get("api_key", "")
        self._api_secret = config.credentials.get("api_secret", "")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                auth=(self._api_key, self._api_secret),
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client
    
    async def authenticate(self) -> bool:
        """Verify API credentials by fetching account info."""
        try:
            client = await self._get_client()
            response = await client.get("/accounts")
            
            if response.status_code == 200:
                self._authenticated = True
                logger.info("RazorpayX authentication successful")
                return True
            else:
                logger.warning(f"RazorpayX auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"RazorpayX authentication error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Quick connectivity test."""
        try:
            client = await self._get_client()
            response = await client.get("/")
            return response.status_code in [200, 401, 403]  # API is reachable
        except Exception:
            return False
    
    async def fetch_employees(self) -> List[EmployeeRecord]:
        """
        Fetch employee list from RazorpayX Payroll.
        
        Note: This is a simplified implementation. The actual RazorpayX Payroll
        API may require different endpoints based on their Opfin integration.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        employees = []
        try:
            client = await self._get_client()
            
            # RazorpayX Payroll uses Opfin - endpoint structure may vary
            # This is a placeholder for the actual implementation
            response = await client.post("/payroll/employees", json={
                "auth": {
                    "api_key": self._api_key,
                },
                "request": {
                    "action": "list",
                },
            })
            
            if response.status_code == 200:
                data = response.json()
                employee_list = data.get("data", {}).get("employees", [])
                
                for emp in employee_list:
                    employees.append(EmployeeRecord(
                        external_id=emp.get("id", ""),
                        name=emp.get("name", ""),
                        email=emp.get("email"),
                        department=emp.get("department"),
                        designation=emp.get("designation"),
                        salary=emp.get("ctc"),
                        join_date=datetime.fromisoformat(emp["join_date"]) if emp.get("join_date") else None,
                        status=emp.get("status", "active"),
                        metadata={
                            "pan": emp.get("pan"),
                            "bank_account": emp.get("bank_account"),
                        },
                    ))
            
        except Exception as e:
            logger.error(f"Error fetching RazorpayX employees: {e}")
        
        return employees
    
    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """
        Fetch payroll run history from RazorpayX.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        payroll_runs = []
        try:
            client = await self._get_client()
            
            request_data: Dict[str, Any] = {
                "auth": {"api_key": self._api_key},
                "request": {"action": "list_payroll_runs"},
            }
            
            if start_date:
                request_data["request"]["from_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                request_data["request"]["to_date"] = end_date.strftime("%Y-%m-%d")
            
            response = await client.post("/payroll/runs", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                runs = data.get("data", {}).get("payroll_runs", [])
                
                for run in runs:
                    payroll_runs.append(PayrollRunRecord(
                        external_id=run.get("id", ""),
                        period_start=datetime.fromisoformat(run.get("period_start", "")),
                        period_end=datetime.fromisoformat(run.get("period_end", "")),
                        total_gross=run.get("total_gross", 0),
                        total_deductions=run.get("total_deductions", 0),
                        total_net=run.get("total_net", 0),
                        employee_count=run.get("employee_count", 0),
                        currency="INR",
                        status=run.get("status", "completed"),
                        breakdown={
                            "pf": run.get("pf_contribution", 0),
                            "esi": run.get("esi_contribution", 0),
                            "tds": run.get("tds_deducted", 0),
                            "professional_tax": run.get("professional_tax", 0),
                        },
                    ))
            
        except Exception as e:
            logger.error(f"Error fetching RazorpayX payroll runs: {e}")
        
        return payroll_runs
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
