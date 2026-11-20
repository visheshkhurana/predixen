"""
Google Sheets connector for importing data as RawDataEvents.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import urllib.parse

import httpx
from .http import http_client

from server.connectors.base import (
    BaseConnector, 
    ConnectorConfig,
    AuthType,
    ProviderCategory,
)
from server.connectors.registry import ConnectorRegistry
from server.connectors.google_analytics import refresh_google_access_token
from server.models.raw_data_event import RawDataEvent

logger = logging.getLogger(__name__)

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def a1_range(sheet_name: str, cells: str = "A:ZZ") -> str:
    """URL-path-safe A1 range: 'Sheet Name'!A:ZZ with ' escaped as ''.

    https://developers.google.com/sheets/api/guides/concepts#cell -- sheet names
    with spaces or special characters must be single-quoted.
    """
    quoted = "'" + str(sheet_name).replace("'", "''") + "'"
    return urllib.parse.quote(f"{quoted}!{cells}", safe="")


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
    OPTIONAL_CREDENTIALS = ["spreadsheet_id", "sheet_name", "header_row", "client_id", "client_secret"]
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.spreadsheet_id = config.settings.get("spreadsheet_id")
        self.sheet_name = config.settings.get("sheet_name", "Sheet1")
        self.header_row = config.settings.get("header_row", 1)
        self.date_column = config.settings.get("date_column")
        creds = config.credentials or {}
        self._access_token = creds.get("access_token", "")
        self._refresh_token = creds.get("refresh_token", "")
        self._client_id = creds.get("client_id", "")
        self._client_secret = creds.get("client_secret", "")

    def _can_refresh(self) -> bool:
        return bool(self._refresh_token and self._client_id and self._client_secret)

    async def _refresh_access_token(self) -> bool:
        token = await refresh_google_access_token(self._client_id, self._client_secret, self._refresh_token)
        if not token:
            return False
        # BaseConnector.rotated_credentials() persists these after the sync.
        self._access_token = token["access_token"]
        if token.get("refresh_token"):
            self._refresh_token = token["refresh_token"]
        return True

    async def _get(self, url: str, timeout: float) -> httpx.Response:
        """GET with the bearer token; on 401 refresh once (when possible) and retry."""
        async with http_client() as client:
            response = await client.get(
                url, headers={"Authorization": f"Bearer {self._access_token}"}, timeout=timeout
            )
            if response.status_code == 401 and self._can_refresh() and await self._refresh_access_token():
                response = await client.get(
                    url, headers={"Authorization": f"Bearer {self._access_token}"}, timeout=timeout
                )
        return response
    
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
        if not self._access_token and not self._can_refresh():
            logger.warning("Google Sheets access token not provided")
            return False

        if not self.spreadsheet_id:
            logger.warning("Google Sheets spreadsheet_id not provided")
            return False

        try:
            if not self._access_token and not await self._refresh_access_token():
                logger.warning("Google Sheets token refresh failed")
                return False
            url = f"{SHEETS_API}/{urllib.parse.quote(str(self.spreadsheet_id), safe='')}"
            response = await self._get(url, timeout=10.0)

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
            return bool(self._access_token or self._can_refresh())
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
        spreadsheet_id = self.spreadsheet_id

        if not (self._access_token or self._can_refresh()) or not spreadsheet_id:
            raise ValueError("Missing access_token or spreadsheet_id")
        if not self._access_token and not await self._refresh_access_token():
            raise ValueError("Google Sheets token refresh failed")

        url = (
            f"{SHEETS_API}/{urllib.parse.quote(str(spreadsheet_id), safe='')}"
            f"/values/{a1_range(self.sheet_name)}"
        )
        response = await self._get(url, timeout=30.0)

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
