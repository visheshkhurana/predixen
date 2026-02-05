"""
ConnectorCapability model for storing discovered capabilities from data sources.
Tracks entities, fields, and supported operations discovered from each connector.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.sql import func
from server.core.db import Base


class ConnectorCapability(Base):
    """
    Stores discovered capabilities for a connected data source.
    Populated after connector setup or first successful ingestion.
    """
    __tablename__ = "connector_capabilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    data_source_id = Column(Integer, nullable=True, index=True)
    
    adapter_key = Column(String(100), nullable=False)
    
    discovered_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    capabilities = Column(JSON, nullable=False, default=dict)
    
    __table_args__ = (
        Index("ix_capability_company_adapter", "company_id", "adapter_key"),
        Index("ix_capability_data_source", "data_source_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "data_source_id": self.data_source_id,
            "adapter_key": self.adapter_key,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "capabilities": self.capabilities or {},
        }
