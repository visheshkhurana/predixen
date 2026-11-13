"""
Google Sheets connector for importing data as RawDataEvents.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from server.connectors.base import (
    BaseConnector, 
    ConnectorConfig,
    AuthType,
    ProviderCategory,
)
from server.connectors.registry import ConnectorRegistry
from server.models.raw_data_event import RawDataEvent

logger = logging.getLogger(__name__)


class GoogleSheetsConnector(BaseConnector):
    """
    Google Sheets connector for importing spreadsheet data.
    
    Auth: OAuth 2.0
    Data flow: Fetches rows → normalizes headers → emits RawDataEvents
    """
    
    PROVIDER_ID = "google_sheets"
    PROVIDER_NAME = "Google Sheets"
    # The base class declares PROVIDER_CATEGORY, not CATEGORY, and the registry
    # filters on PROVIDER_CATEGORY -- so the old `CATEGORY` spelling was dead
    # code and this provider silently inherited the base default (PAYROLL).
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.OAUTH2
    
    REQUIRED_CREDENTIALS = ["access_token", "refresh_token"]
    OPTIONAL_CREDENTIALS = ["spreadsheet_id", "sheet_name", "header_row"]
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.spreadsheet_id = config.settings.get("spreadsheet_id")
        self.sheet_name = config.settings.get("sheet_name", "Sheet1")
        self.header_row = config.settings.get("header_row", 1)
        self.date_column = config.settings.get("date_column")
    
    async def authenticate(self) -> bool:
        """
        Validate the OAuth token against the Sheets API.

        This was the one abstract member the class never implemented, which made
        it un-instantiable and took the whole provider catalogue down with it.
        It probes the spreadsheet's metadata endpoint -- the cheapest call that
        proves the token is live and the spreadsheet is reachable by this user.

        Returns False rather than raising, matching the other connectors: every
        caller treats authentication failure as a state, not an exception.
        """
        access_token = self.config.credentials.get("access_token")
        if not access_token:
            logger.warning("Google Sheets access token not provided")
            return False

        if not self.spreadsheet_id:
            logger.warning("Google Sheets spreadsheet_id not provided")
            return False

        try:
            import httpx

            url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )

            if response.status_code == 200:
                self._authenticated = True
                logger.info("Google Sheets authentication successful")
                return True

            logger.warning(
                f"Google Sheets authentication failed: HTTP {response.status_code}"
            )
            return False
        except Exception as e:
            logger.error(f"Google Sheets authentication failed: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test the connection to Google Sheets API."""
        try:
            access_token = self.config.credentials.get("access_token")
            if not access_token:
                return False
            return True
        except Exception as e:
            logger.error(f"Google Sheets connection test failed: {e}")
            return False
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch data from Google Sheets.
        
        Returns a list of raw data payloads, one per row.
        """
        try:
            rows = await self._fetch_sheet_data()
            
            if not rows or len(rows) < 2:
                return []
            
            headers = [str(h).strip().lower().replace(" ", "_") for h in rows[0]]
            
            data = []
            for row in rows[1:]:
                payload = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        payload[headers[i]] = value
                
                occurred_at = datetime.utcnow()
                if self.date_column and self.date_column in payload:
                    try:
                        occurred_at = self._parse_date(payload[self.date_column])
                    except:
                        pass
                
                data.append({
                    "payload": payload,
                    "occurred_at": occurred_at,
                })
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching Google Sheets data: {e}")
            raise
    
    async def _fetch_sheet_data(self) -> List[List[Any]]:
        """Fetch raw sheet data from Google Sheets API."""
        import httpx
        
        access_token = self.config.credentials.get("access_token")
        spreadsheet_id = self.spreadsheet_id
        
        if not access_token or not spreadsheet_id:
            raise ValueError("Missing access_token or spreadsheet_id")
        
        range_name = f"{self.sheet_name}!A:ZZ"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Google Sheets API error: {response.text}")
            
            data = response.json()
            return data.get("values", [])
    
    def _parse_date(self, value: Any) -> datetime:
        """Parse a date value from the sheet."""
        if isinstance(value, datetime):
            return value
        
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(str(value), fmt)
            except:
                continue
        
        return datetime.utcnow()
    
    def emit_raw_events(
        self, 
        data: List[Dict[str, Any]], 
        company_id: int
    ) -> List[RawDataEvent]:
        """
        Convert fetched data to RawDataEvent records.
        
        Args:
            data: List of fetched data with payload and occurred_at
            company_id: The company ID
            
        Returns:
            List of RawDataEvent records (not persisted)
        """
        events = []
        for item in data:
            event = RawDataEvent(
                company_id=company_id,
                connector_id=self.PROVIDER_ID,
                source=f"sheets:{self.spreadsheet_id}",
                payload=item["payload"],
                occurred_at=item["occurred_at"],
            )
            events.append(event)
        return events


ConnectorRegistry.register(GoogleSheetsConnector)
