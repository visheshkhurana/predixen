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
    # Legacy storage keys that must keep resolving after a provider id rename.
    _aliases: Dict[str, str] = {}
    
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
        for alias in getattr(connector_class, "PROVIDER_ALIASES", ()) or ():
            if not alias or alias == provider_id:
                continue
            current = cls._aliases.get(alias)
            if current and current != provider_id:
                logger.warning(
                    f"Alias {alias} already points at {current}; not retargeting to {provider_id}"
                )
                continue
            if alias in cls._connectors and cls._connectors[alias] is not connector_class:
                logger.warning(f"Alias {alias} collides with a registered provider; skipping")
                continue
            cls._aliases[alias] = provider_id
        logger.info(f"Registered connector: {provider_id}")
        return connector_class

    @classmethod
    def canonical_provider_id(cls, provider_id: str) -> str:
        """Return the registered id for a provider, following aliases."""
        return cls._aliases.get(provider_id, provider_id)

    @classmethod
    def provider_ids_for(cls, provider_id: str) -> List[str]:
        """Canonical id plus aliases. Unknown ids are returned unchanged."""
        canonical = cls.canonical_provider_id(provider_id)
        connector_class = cls._connectors.get(canonical)
        if connector_class is None:
            return [provider_id]
        ids = [connector_class.PROVIDER_ID]
        for alias in getattr(connector_class, "PROVIDER_ALIASES", ()) or ():
            if alias and alias not in ids:
                ids.append(alias)
        return ids
    
    @classmethod
    def get_connector_class(cls, provider_id: str) -> Optional[Type[BaseConnector]]:
        """Get a connector class by provider ID or a registered alias."""
        return cls._connectors.get(cls.canonical_provider_id(provider_id))
    
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
            # One malformed connector must not take the whole catalogue down.
            # This loop used to raise straight through: `google_sheets` and
            # `rest_api` were registered while still abstract, so every call to
            # GET /connectors/providers answered 500 for EVERY provider, and
            # because `load_all_connectors()` runs at import the failure was
            # unconditional. Skipping is the safe half; the other half is the
            # test that asserts every registered class is constructible, so a
            # skip is loud in CI instead of silent in production.
            try:
                if category and connector_class.PROVIDER_CATEGORY != category:
                    continue

                # Create temp instance to get provider info
                temp_config = ConnectorConfig(
                    provider_id=provider_id,
                    company_id=0,
                )
                temp_instance = connector_class(temp_config)
                connectors.append(temp_instance.get_provider_info())
            except Exception as e:
                logger.error(
                    f"Skipping connector '{provider_id}': cannot be instantiated "
                    f"({type(e).__name__}: {e})"
                )

        return connectors
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of all registered provider IDs."""
        return list(cls._connectors.keys())
