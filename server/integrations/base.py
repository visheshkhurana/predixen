"""
Base classes for external integrations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class IntegrationStatus(str, Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class IntegrationConfig:
    provider: str
    api_key: Optional[str] = None
    refresh_token: Optional[str] = None
    company_id: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    last_sync: Optional[datetime] = None
    status: IntegrationStatus = IntegrationStatus.NOT_CONNECTED


@dataclass
class SyncResult:
    success: bool
    records_synced: int
    errors: List[str]
    sync_time: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "records_synced": self.records_synced,
            "errors": self.errors,
            "sync_time": self.sync_time.isoformat(),
        }


class IntegrationBase(ABC):
    """Base class for all external integrations."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self._status = config.status
    
    @property
    def status(self) -> IntegrationStatus:
        return self._status
    
    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """Establish connection to the external service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the external service."""
        pass
    
    @abstractmethod
    async def sync(self) -> SyncResult:
        """Sync data from the external service."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection is still valid."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": self.config.provider,
            "status": self._status.value,
            "last_sync": self.config.last_sync.isoformat() if self.config.last_sync else None,
        }
