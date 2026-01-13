"""
CRM integrations: Salesforce, HubSpot, etc.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base import IntegrationBase, IntegrationConfig, IntegrationStatus, SyncResult

logger = logging.getLogger(__name__)


@dataclass
class CRMDeal:
    """Normalized CRM deal/opportunity structure."""
    id: str
    name: str
    stage: str
    amount: float
    probability: float
    close_date: Optional[datetime]
    owner_name: str
    company_name: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "stage": self.stage,
            "amount": self.amount,
            "probability": self.probability,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "owner_name": self.owner_name,
            "company_name": self.company_name,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CRMContact:
    """Normalized CRM contact structure."""
    id: str
    email: str
    first_name: str
    last_name: str
    company_name: str
    title: str
    lifecycle_stage: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "title": self.title,
            "lifecycle_stage": self.lifecycle_stage,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PipelineMetrics:
    """Aggregated pipeline metrics."""
    total_pipeline_value: float
    weighted_pipeline: float
    deal_count: int
    average_deal_size: float
    average_close_time_days: float
    win_rate: float
    deals_by_stage: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_pipeline_value": self.total_pipeline_value,
            "weighted_pipeline": self.weighted_pipeline,
            "deal_count": self.deal_count,
            "average_deal_size": self.average_deal_size,
            "average_close_time_days": self.average_close_time_days,
            "win_rate": self.win_rate,
            "deals_by_stage": self.deals_by_stage,
        }


class SalesforceIntegration(IntegrationBase):
    """Salesforce CRM integration."""
    
    PROVIDER_NAME = "salesforce"
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        if config is None:
            config = IntegrationConfig(provider=self.PROVIDER_NAME)
        super().__init__(config)
        self._instance_url: Optional[str] = None
    
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to Salesforce using OAuth2.
        
        Credentials should contain:
        - access_token: OAuth access token
        - refresh_token: OAuth refresh token
        - instance_url: Salesforce instance URL
        """
        try:
            self.config.api_key = credentials.get("access_token")
            self.config.refresh_token = credentials.get("refresh_token")
            self._instance_url = credentials.get("instance_url")
            self._status = IntegrationStatus.CONNECTED
            logger.info(f"Connected to Salesforce: {self._instance_url}")
            return True
        except Exception as e:
            logger.error(f"Salesforce connection failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Salesforce."""
        self.config.api_key = None
        self.config.refresh_token = None
        self._instance_url = None
        self._status = IntegrationStatus.NOT_CONNECTED
        return True
    
    async def sync(self) -> SyncResult:
        """Sync opportunities and contacts from Salesforce."""
        if self._status != IntegrationStatus.CONNECTED:
            return SyncResult(
                success=False,
                records_synced=0,
                errors=["Not connected to Salesforce"],
            )
        
        try:
            self._status = IntegrationStatus.SYNCING
            
            # In production, call Salesforce SOQL API:
            # - SELECT Id,Name,Amount,StageName,Probability,CloseDate FROM Opportunity
            # - SELECT Id,Email,FirstName,LastName FROM Contact
            
            deals = await self._fetch_opportunities()
            contacts = await self._fetch_contacts()
            
            self.config.last_sync = datetime.utcnow()
            self._status = IntegrationStatus.CONNECTED
            
            return SyncResult(
                success=True,
                records_synced=len(deals) + len(contacts),
                errors=[],
                data={
                    "deals": [d.to_dict() for d in deals],
                    "contacts": [c.to_dict() for c in contacts],
                },
            )
        except Exception as e:
            logger.error(f"Salesforce sync failed: {e}")
            self._status = IntegrationStatus.ERROR
            return SyncResult(
                success=False,
                records_synced=0,
                errors=[str(e)],
            )
    
    async def test_connection(self) -> bool:
        """Test Salesforce connection."""
        return self._status == IntegrationStatus.CONNECTED
    
    async def _fetch_opportunities(self) -> List[CRMDeal]:
        """Fetch opportunities from Salesforce."""
        # Placeholder - in production, call Salesforce SOQL API
        return []
    
    async def _fetch_contacts(self) -> List[CRMContact]:
        """Fetch contacts from Salesforce."""
        # Placeholder - in production, call Salesforce SOQL API
        return []
    
    async def get_pipeline_metrics(self) -> Optional[PipelineMetrics]:
        """Calculate pipeline metrics from opportunities."""
        if self._status != IntegrationStatus.CONNECTED:
            return None
        
        deals = await self._fetch_opportunities()
        if not deals:
            return PipelineMetrics(
                total_pipeline_value=0,
                weighted_pipeline=0,
                deal_count=0,
                average_deal_size=0,
                average_close_time_days=0,
                win_rate=0,
                deals_by_stage={},
            )
        
        total = sum(d.amount for d in deals)
        weighted = sum(d.amount * d.probability for d in deals)
        
        stages: Dict[str, int] = {}
        for d in deals:
            stages[d.stage] = stages.get(d.stage, 0) + 1
        
        return PipelineMetrics(
            total_pipeline_value=total,
            weighted_pipeline=weighted,
            deal_count=len(deals),
            average_deal_size=total / len(deals) if deals else 0,
            average_close_time_days=30,  # Placeholder
            win_rate=0.25,  # Placeholder
            deals_by_stage=stages,
        )


class HubSpotIntegration(IntegrationBase):
    """HubSpot CRM integration."""
    
    PROVIDER_NAME = "hubspot"
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        if config is None:
            config = IntegrationConfig(provider=self.PROVIDER_NAME)
        super().__init__(config)
    
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to HubSpot using API key or OAuth.
        
        Credentials should contain:
        - access_token: OAuth access token (preferred)
        - api_key: HubSpot API key (deprecated)
        """
        try:
            self.config.api_key = credentials.get("access_token") or credentials.get("api_key")
            self.config.refresh_token = credentials.get("refresh_token")
            self._status = IntegrationStatus.CONNECTED
            logger.info("Connected to HubSpot")
            return True
        except Exception as e:
            logger.error(f"HubSpot connection failed: {e}")
            self._status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from HubSpot."""
        self.config.api_key = None
        self.config.refresh_token = None
        self._status = IntegrationStatus.NOT_CONNECTED
        return True
    
    async def sync(self) -> SyncResult:
        """Sync deals and contacts from HubSpot."""
        if self._status != IntegrationStatus.CONNECTED:
            return SyncResult(
                success=False,
                records_synced=0,
                errors=["Not connected to HubSpot"],
            )
        
        try:
            self._status = IntegrationStatus.SYNCING
            
            # In production, call HubSpot API:
            # - GET /crm/v3/objects/deals
            # - GET /crm/v3/objects/contacts
            
            deals = await self._fetch_deals()
            contacts = await self._fetch_contacts()
            
            self.config.last_sync = datetime.utcnow()
            self._status = IntegrationStatus.CONNECTED
            
            return SyncResult(
                success=True,
                records_synced=len(deals) + len(contacts),
                errors=[],
                data={
                    "deals": [d.to_dict() for d in deals],
                    "contacts": [c.to_dict() for c in contacts],
                },
            )
        except Exception as e:
            logger.error(f"HubSpot sync failed: {e}")
            self._status = IntegrationStatus.ERROR
            return SyncResult(
                success=False,
                records_synced=0,
                errors=[str(e)],
            )
    
    async def test_connection(self) -> bool:
        """Test HubSpot connection."""
        return self._status == IntegrationStatus.CONNECTED
    
    async def _fetch_deals(self) -> List[CRMDeal]:
        """Fetch deals from HubSpot."""
        # Placeholder - in production, call HubSpot CRM API
        return []
    
    async def _fetch_contacts(self) -> List[CRMContact]:
        """Fetch contacts from HubSpot."""
        # Placeholder - in production, call HubSpot CRM API
        return []
    
    async def get_pipeline_metrics(self) -> Optional[PipelineMetrics]:
        """Calculate pipeline metrics from deals."""
        if self._status != IntegrationStatus.CONNECTED:
            return None
        
        deals = await self._fetch_deals()
        if not deals:
            return PipelineMetrics(
                total_pipeline_value=0,
                weighted_pipeline=0,
                deal_count=0,
                average_deal_size=0,
                average_close_time_days=0,
                win_rate=0,
                deals_by_stage={},
            )
        
        total = sum(d.amount for d in deals)
        weighted = sum(d.amount * d.probability for d in deals)
        
        stages: Dict[str, int] = {}
        for d in deals:
            stages[d.stage] = stages.get(d.stage, 0) + 1
        
        return PipelineMetrics(
            total_pipeline_value=total,
            weighted_pipeline=weighted,
            deal_count=len(deals),
            average_deal_size=total / len(deals) if deals else 0,
            average_close_time_days=30,  # Placeholder
            win_rate=0.25,  # Placeholder
            deals_by_stage=stages,
        )


def get_crm_integration(provider: str) -> Optional[IntegrationBase]:
    """Factory to get CRM integration by provider name."""
    providers = {
        "salesforce": SalesforceIntegration,
        "hubspot": HubSpotIntegration,
    }
    
    integration_class = providers.get(provider.lower())
    if integration_class:
        return integration_class()
    return None
