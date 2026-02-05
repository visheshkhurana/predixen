"""
Generic REST API connector for importing data from any HTTP endpoint.
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


class RestAPIConnector(BaseConnector):
    """
    Generic REST API connector.
    
    Auth: API key (header or query param)
    Data flow: Polls endpoint → stores full JSON payload as RawDataEvent
    """
    
    PROVIDER_ID = "rest_api"
    PROVIDER_NAME = "REST API"
    CATEGORY = ProviderCategory.CRM
    AUTH_TYPE = AuthType.API_KEY
    
    REQUIRED_CREDENTIALS = ["api_key"]
    OPTIONAL_CREDENTIALS = ["endpoint_url", "auth_header", "auth_param"]
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.endpoint_url = config.settings.get("endpoint_url")
        self.auth_header = config.settings.get("auth_header", "Authorization")
        self.auth_param = config.settings.get("auth_param")
        self.response_path = config.settings.get("response_path")
        self.date_field = config.settings.get("date_field")
        self.method = config.settings.get("method", "GET")
        self.headers = config.settings.get("headers", {})
    
    async def test_connection(self) -> bool:
        """Test the connection to the REST API."""
        try:
            if not self.endpoint_url:
                return False
            
            import httpx
            async with httpx.AsyncClient() as client:
                headers = self._build_headers()
                response = await client.request(
                    self.method,
                    self.endpoint_url,
                    headers=headers,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"REST API connection test failed: {e}")
            return False
    
    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {**self.headers}
        
        api_key = self.config.credentials.get("api_key")
        if api_key and self.auth_header:
            if self.auth_header.lower() == "authorization":
                headers["Authorization"] = f"Bearer {api_key}"
            else:
                headers[self.auth_header] = api_key
        
        return headers
    
    def _build_params(self) -> Dict[str, str]:
        """Build query parameters with authentication."""
        params = {}
        
        api_key = self.config.credentials.get("api_key")
        if api_key and self.auth_param:
            params[self.auth_param] = api_key
        
        return params
    
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetch data from the REST API endpoint.
        
        Returns a list of raw data payloads.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    self.method,
                    self.endpoint_url,
                    headers=self._build_headers(),
                    params=self._build_params(),
                    timeout=30.0
                )
                
                if response.status_code >= 400:
                    raise Exception(f"API error: {response.status_code} - {response.text}")
                
                json_data = response.json()
                
                if self.response_path:
                    for key in self.response_path.split("."):
                        if isinstance(json_data, dict):
                            json_data = json_data.get(key, [])
                        elif isinstance(json_data, list) and key.isdigit():
                            json_data = json_data[int(key)]
                
                if not isinstance(json_data, list):
                    json_data = [json_data]
                
                data = []
                for item in json_data:
                    occurred_at = datetime.utcnow()
                    if self.date_field and isinstance(item, dict):
                        try:
                            date_value = item.get(self.date_field)
                            if date_value:
                                occurred_at = self._parse_date(date_value)
                        except:
                            pass
                    
                    data.append({
                        "payload": item if isinstance(item, dict) else {"value": item},
                        "occurred_at": occurred_at,
                    })
                
                return data
                
        except Exception as e:
            logger.error(f"Error fetching REST API data: {e}")
            raise
    
    def _parse_date(self, value: Any) -> datetime:
        """Parse a date value from the response."""
        if isinstance(value, datetime):
            return value
        
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]:
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
        """
        events = []
        for item in data:
            event = RawDataEvent(
                company_id=company_id,
                connector_id=self.PROVIDER_ID,
                source=f"api:{self.endpoint_url}",
                payload=item["payload"],
                occurred_at=item["occurred_at"],
            )
            events.append(event)
        return events


ConnectorRegistry.register(RestAPIConnector)
