"""
Dashboard and DashboardWidget models for custom KPI dashboards.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from server.core.db import Base


class Dashboard(Base):
    """
    A custom dashboard with a grid layout of widgets.
    """
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    layout_config = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")

    def to_dict(self, include_widgets=False):
        result = {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "layout_config": self.layout_config,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_widgets:
            result["widgets"] = [w.to_dict() for w in self.widgets]
        return result


class DashboardWidget(Base):
    """
    A widget on a dashboard displaying a metric.
    """
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True)
    widget_type = Column(String(50), nullable=False)
    metric_key = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    config = Column(JSON, nullable=True)
    position = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    dashboard = relationship("Dashboard", back_populates="widgets")

    def to_dict(self):
        return {
            "id": self.id,
            "dashboard_id": self.dashboard_id,
            "widget_type": self.widget_type,
            "metric_key": self.metric_key,
            "title": self.title,
            "config": self.config,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
