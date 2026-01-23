"""
Connector Registry - manages available connectors and their instantiation.
"""

from typing import Dict, Type, List, Optional, Any
import logging

from .base import BaseConnector, ConnectorConfig, ProviderCategory

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for all available connectors.
    Handles registration, instantiation, and discovery.
    """
    
    _connectors: Dict[str, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, connector_class: Type[BaseConnector]) -> Type[BaseConnector]:
        """
        Register a connector class. Can be used as a decorator.
        
        @ConnectorRegistry.register
        class MyConnector(BaseConnector):
            ...
        """
        provider_id = connector_class.PROVIDER_ID
        if provider_id in cls._connectors:
            logger.warning(f"Overwriting existing connector: {provider_id}")
        cls._connectors[provider_id] = connector_class
        logger.info(f"Registered connector: {provider_id}")
        return connector_class
    
    @classmethod
    def get_connector_class(cls, provider_id: str) -> Optional[Type[BaseConnector]]:
        """Get a connector class by provider ID."""
        return cls._connectors.get(provider_id)
    
    @classmethod
    def create_connector(cls, config: ConnectorConfig) -> Optional[BaseConnector]:
        """
        Instantiate a connector with the given configuration.
        """
        connector_class = cls.get_connector_class(config.provider_id)
        if not connector_class:
            logger.error(f"Unknown connector: {config.provider_id}")
            return None
        return connector_class(config)
    
    @classmethod
    def list_connectors(
        cls, 
        category: Optional[ProviderCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        List all registered connectors with their metadata.
        Optionally filter by category.
        """
        connectors = []
        for provider_id, connector_class in cls._connectors.items():
            if category and connector_class.PROVIDER_CATEGORY != category:
                continue
            
            # Create temp instance to get provider info
            temp_config = ConnectorConfig(
                provider_id=provider_id,
                company_id=0,
            )
            temp_instance = connector_class(temp_config)
            connectors.append(temp_instance.get_provider_info())
        
        return connectors
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of all registered provider IDs."""
        return list(cls._connectors.keys())
