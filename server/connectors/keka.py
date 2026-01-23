"""
Keka Connector

Integrates with Keka HR API to fetch:
- Employee data
- Payroll information
- Time and attendance

API Documentation: https://developers.keka.com/ and https://apidocs.keka.com/
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


@ConnectorRegistry.register
class KekaConnector(BaseConnector):
    """
    Keka HR connector for syncing employee and payroll data.
    
    Authentication uses API key generated from admin account.
    Requires API/Webhook add-on to be enabled.
    """
    
    PROVIDER_ID = "keka"
    PROVIDER_NAME = "Keka HR"
    PROVIDER_DESCRIPTION = "Sync employee data, payroll, and time tracking from Keka"
    PROVIDER_CATEGORY = ProviderCategory.HRIS
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://developers.keka.com/"
    
    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._base_url = config.credentials.get("base_url", "https://api.keka.com")
        self._api_key = config.credentials.get("api_key", "")
        self._tenant_id = config.credentials.get("tenant_id", "")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create authenticated HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                    "X-Tenant-Id": self._tenant_id,
                },
                timeout=30.0,
            )
        return self._client
    
    async def authenticate(self) -> bool:
        """Verify API credentials."""
        try:
            client = await self._get_client()
            response = await client.get("/v1/employees", params={"limit": 1})
            
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Keka authentication successful")
                return True
            else:
                logger.warning(f"Keka auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Keka authentication error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Quick connectivity test."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code in [200, 401, 403]
        except Exception:
            return False
    
    async def fetch_employees(self) -> List[EmployeeRecord]:
        """Fetch employee list from Keka."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        employees = []
        offset = 0
        limit = 100
        
        try:
            client = await self._get_client()
            
            while True:
                response = await client.get(
                    "/v1/employees",
                    params={"offset": offset, "limit": limit}
                )
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                employee_list = data.get("data", [])
                
                if not employee_list:
                    break
                
                for emp in employee_list:
                    employees.append(EmployeeRecord(
                        external_id=emp.get("employeeId", ""),
                        name=emp.get("displayName", ""),
                        email=emp.get("email"),
                        department=emp.get("department", {}).get("name"),
                        designation=emp.get("designation", {}).get("name"),
                        salary=emp.get("compensation", {}).get("ctc"),
                        join_date=datetime.fromisoformat(emp["dateOfJoining"]) if emp.get("dateOfJoining") else None,
                        status=emp.get("status", "active").lower(),
                        metadata={
                            "employee_number": emp.get("employeeNumber"),
                            "manager": emp.get("manager", {}).get("displayName"),
                            "location": emp.get("location", {}).get("name"),
                        },
                    ))
                
                if len(employee_list) < limit:
                    break
                offset += limit
            
            logger.info(f"Fetched {len(employees)} employees from Keka")
            
        except Exception as e:
            logger.error(f"Error fetching Keka employees: {e}")
        
        return employees
    
    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """Fetch payroll run history from Keka."""
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        payroll_runs = []
        
        try:
            client = await self._get_client()
            
            params: Dict[str, Any] = {}
            if start_date:
                params["fromDate"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["toDate"] = end_date.strftime("%Y-%m-%d")
            
            response = await client.get("/v1/payroll/runs", params=params)
            
            if response.status_code == 200:
                data = response.json()
                runs = data.get("data", [])
                
                for run in runs:
                    payroll_runs.append(PayrollRunRecord(
                        external_id=run.get("id", ""),
                        period_start=datetime.fromisoformat(run["periodStart"]) if run.get("periodStart") else datetime.now(),
                        period_end=datetime.fromisoformat(run["periodEnd"]) if run.get("periodEnd") else datetime.now(),
                        total_gross=run.get("summary", {}).get("totalGross", 0),
                        total_deductions=run.get("summary", {}).get("totalDeductions", 0),
                        total_net=run.get("summary", {}).get("totalNet", 0),
                        employee_count=run.get("summary", {}).get("employeeCount", 0),
                        currency="INR",
                        status=run.get("status", "completed").lower(),
                        breakdown={
                            "pf": run.get("summary", {}).get("pfContribution", 0),
                            "esi": run.get("summary", {}).get("esiContribution", 0),
                            "tds": run.get("summary", {}).get("tds", 0),
                        },
                    ))
            
        except Exception as e:
            logger.error(f"Error fetching Keka payroll runs: {e}")
        
        return payroll_runs
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
