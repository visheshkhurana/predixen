"""
GreytHR Connector

Integrates with GreytHR API to fetch:
- Employee data
- Leave and attendance records
- Salary structures and payroll

API Documentation: https://api-docs.greythr.com/
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

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
class GreytHRConnector(BaseConnector):
    """
    GreytHR connector for syncing HR and payroll data.
    
    Authentication uses API Access ID and Secret generated from Admin portal.
    API Version: V2
    """
    
    PROVIDER_ID = "greythr"
    PROVIDER_NAME = "GreytHR"
    PROVIDER_DESCRIPTION = "Sync employee data, attendance, leave, and payroll from GreytHR"
    PROVIDER_CATEGORY = ProviderCategory.HRIS
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://api-docs.greythr.com/"
    
    SUPPORTS_EMPLOYEES = True
    SUPPORTS_PAYROLL = True
    SUPPORTS_LEDGER = False
    SUPPORTS_INVOICES = False
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._base_url = config.credentials.get("base_url", "https://api.greythr.com")
        self._api_access_id = config.credentials.get("api_access_id", "")
        self._api_secret = config.credentials.get("api_secret", "")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create authenticated HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Content-Type": "application/json",
                    "X-API-ACCESS-ID": self._api_access_id,
                    "X-API-SECRET": self._api_secret,
                },
                timeout=30.0,
            )
        return self._client
    
    async def authenticate(self) -> bool:
        """Verify API credentials."""
        try:
            client = await self._get_client()
            # Test auth by fetching a small employee list
            response = await client.get("/employee/v2/employees", params={"page": 1, "size": 1})
            
            if response.status_code == 200:
                self._authenticated = True
                logger.info("GreytHR authentication successful")
                return True
            else:
                logger.warning(f"GreytHR auth failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"GreytHR authentication error: {e}")
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
        """
        Fetch employee list from GreytHR.
        
        Uses GET /employee/v2/employees endpoint with pagination.
        """
        if not self._authenticated:
            if not await self.authenticate():
                return []
        
        employees = []
        page = 1
        page_size = 25
        
        try:
            client = await self._get_client()
            
            while True:
                response = await client.get(
                    "/employee/v2/employees",
                    params={"page": page, "size": page_size}
                )
                
                if response.status_code != 200:
                    logger.warning(f"GreytHR employees fetch failed: {response.status_code}")
                    break
                
                data = response.json()
                employee_list = data.get("employees", [])
                
                if not employee_list:
                    break
                
                for emp in employee_list:
                    employees.append(EmployeeRecord(
                        external_id=str(emp.get("employeeId", "")),
                        name=f"{emp.get('firstName', '')} {emp.get('lastName', '')}".strip(),
                        email=emp.get("email"),
                        department=emp.get("department", {}).get("name"),
                        designation=emp.get("designation", {}).get("name"),
                        salary=emp.get("ctc"),  # May need separate salary API call
                        join_date=datetime.fromisoformat(emp["dateOfJoining"]) if emp.get("dateOfJoining") else None,
                        status="active" if emp.get("isActive") else "inactive",
                        metadata={
                            "employee_code": emp.get("employeeCode"),
                            "reporting_manager": emp.get("reportingManager", {}).get("name"),
                            "location": emp.get("location", {}).get("name"),
                        },
                    ))
                
                # Check if more pages
                total_pages = data.get("totalPages", 1)
                if page >= total_pages:
                    break
                page += 1
            
            logger.info(f"Fetched {len(employees)} employees from GreytHR")
            
        except Exception as e:
            logger.error(f"Error fetching GreytHR employees: {e}")
        
        return employees
    
    async def fetch_payroll_runs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PayrollRunRecord]:
        """
        Fetch payroll run summary from GreytHR.
        
        Note: GreytHR salary module may have different endpoint structure.
        """
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
            
            # Salary module endpoint - structure may vary
            response = await client.get("/salary/v2/payroll-runs", params=params)
            
            if response.status_code == 200:
                data = response.json()
                runs = data.get("payrollRuns", [])
                
                for run in runs:
                    period_start_str = run.get("periodStart", run.get("month", ""))
                    period_end_str = run.get("periodEnd", run.get("month", ""))
                    
                    payroll_runs.append(PayrollRunRecord(
                        external_id=str(run.get("id", "")),
                        period_start=datetime.fromisoformat(period_start_str) if period_start_str else datetime.now(),
                        period_end=datetime.fromisoformat(period_end_str) if period_end_str else datetime.now(),
                        total_gross=run.get("totalGross", 0),
                        total_deductions=run.get("totalDeductions", 0),
                        total_net=run.get("totalNet", 0),
                        employee_count=run.get("employeeCount", 0),
                        currency="INR",
                        status=run.get("status", "completed"),
                        breakdown={
                            "pf": run.get("pfAmount", 0),
                            "esi": run.get("esiAmount", 0),
                            "tds": run.get("tdsAmount", 0),
                        },
                    ))
                
                logger.info(f"Fetched {len(payroll_runs)} payroll runs from GreytHR")
            
        except Exception as e:
            logger.error(f"Error fetching GreytHR payroll runs: {e}")
        
        return payroll_runs
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
