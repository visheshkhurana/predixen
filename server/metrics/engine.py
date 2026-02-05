"""
Metric Engine - computes metrics from raw data events.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from server.models.raw_data_event import RawDataEvent
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.metrics.formula_parser import FormulaParser, FormulaError

logger = logging.getLogger(__name__)


class MetricEngine:
    """
    Engine for computing metrics from raw data events.
    
    Reads RawDataEvents, applies MetricDefinition formulas,
    and writes computed values to MetricValue records.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def recompute_all_metrics(self, company_id: int) -> Dict[str, Any]:
        """
        Recompute all metrics for a company.
        
        Args:
            company_id: The company to compute metrics for
            
        Returns:
            Summary of computation results
        """
        metrics = self.db.query(MetricDefinition).filter(
            MetricDefinition.company_id == company_id
        ).all()
        
        results = {
            "company_id": company_id,
            "metrics_processed": 0,
            "metrics_success": 0,
            "metrics_failed": 0,
            "errors": [],
        }
        
        for metric in metrics:
            try:
                self.compute_metric(metric)
                results["metrics_success"] += 1
            except Exception as e:
                logger.error(f"Error computing metric {metric.key}: {e}")
                results["errors"].append({
                    "metric_key": metric.key,
                    "error": str(e),
                })
                results["metrics_failed"] += 1
            results["metrics_processed"] += 1
        
        return results
    
    def compute_metric(
        self, 
        metric: MetricDefinition,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> MetricValue:
        """
        Compute a single metric for a given period.
        
        Args:
            metric: The metric definition to compute
            period_start: Start of the computation period (default: current month start)
            period_end: End of the computation period (default: current month end)
            
        Returns:
            The computed MetricValue record
        """
        now = datetime.utcnow()
        if period_start is None:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_end is None:
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        query = self.db.query(RawDataEvent).filter(
            RawDataEvent.company_id == metric.company_id,
            RawDataEvent.occurred_at >= period_start,
            RawDataEvent.occurred_at < period_end,
        )
        
        if metric.source_connector:
            query = query.filter(RawDataEvent.connector_id == metric.source_connector)
        
        events = query.all()
        
        data = [e.payload for e in events if e.payload]
        
        contributing_connectors = list(set(e.connector_id for e in events))
        
        try:
            parser = FormulaParser(metric.formula)
            value = parser.evaluate(data)
        except FormulaError as e:
            logger.error(f"Formula error for metric {metric.key}: {e}")
            value = 0.0
        
        existing = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric.id,
            MetricValue.period_start == period_start,
        ).first()
        
        if existing:
            existing.value = value
            existing.computed_at = now
            existing.raw_event_count = len(events)
            existing.contributing_connectors = contributing_connectors
            metric_value = existing
        else:
            metric_value = MetricValue(
                metric_id=metric.id,
                company_id=metric.company_id,
                value=value,
                period_start=period_start,
                period_end=period_end,
                raw_event_count=len(events),
                contributing_connectors=contributing_connectors,
            )
            self.db.add(metric_value)
        
        self.db.commit()
        return metric_value
    
    def get_metric_timeseries(
        self,
        company_id: int,
        metric_key: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Get historical values for a metric.
        
        Args:
            company_id: The company ID
            metric_key: The metric key to retrieve
            start_date: Start of the date range
            end_date: End of the date range
            limit: Maximum number of periods to return
            
        Returns:
            List of metric values with periods
        """
        metric = self.db.query(MetricDefinition).filter(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == metric_key,
        ).first()
        
        if not metric:
            return []
        
        query = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric.id,
        )
        
        if start_date:
            query = query.filter(MetricValue.period_start >= start_date)
        if end_date:
            query = query.filter(MetricValue.period_end <= end_date)
        
        values = query.order_by(MetricValue.period_start.desc()).limit(limit).all()
        
        return [{
            "period_start": v.period_start.isoformat(),
            "period_end": v.period_end.isoformat(),
            "value": v.value,
            "computed_at": v.computed_at.isoformat() if v.computed_at else None,
            "raw_event_count": v.raw_event_count,
            "contributing_connectors": v.contributing_connectors,
        } for v in reversed(values)]
    
    def get_metric_latest(
        self,
        company_id: int,
        metric_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest value for a metric.
        
        Args:
            company_id: The company ID
            metric_key: The metric key to retrieve
            
        Returns:
            Latest metric value or None
        """
        metric = self.db.query(MetricDefinition).filter(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == metric_key,
        ).first()
        
        if not metric:
            return None
        
        value = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric.id,
        ).order_by(MetricValue.period_start.desc()).first()
        
        if not value:
            return None
        
        return {
            "metric_key": metric_key,
            "metric_name": metric.name,
            "value": value.value,
            "unit": metric.unit,
            "format_type": metric.format_type,
            "period_start": value.period_start.isoformat(),
            "period_end": value.period_end.isoformat(),
            "computed_at": value.computed_at.isoformat() if value.computed_at else None,
            "raw_event_count": value.raw_event_count,
            "contributing_connectors": value.contributing_connectors,
        }
    
    def create_system_metrics(self, company_id: int) -> List[MetricDefinition]:
        """
        Create default system metrics for a company.
        
        Args:
            company_id: The company ID
            
        Returns:
            List of created metrics
        """
        system_metrics = [
            {
                "key": "mrr",
                "name": "Monthly Recurring Revenue",
                "description": "Total monthly recurring revenue from all sources",
                "formula": "sum(amount) where type == \"recurring\"",
                "unit": "USD",
                "format_type": "currency",
            },
            {
                "key": "total_revenue",
                "name": "Total Revenue",
                "description": "Total revenue including one-time and recurring",
                "formula": "sum(amount)",
                "unit": "USD",
                "format_type": "currency",
            },
            {
                "key": "customer_count",
                "name": "Customer Count",
                "description": "Total number of customers",
                "formula": "count()",
                "format_type": "number",
            },
            {
                "key": "avg_transaction",
                "name": "Average Transaction Value",
                "description": "Average value per transaction",
                "formula": "avg(amount)",
                "unit": "USD",
                "format_type": "currency",
            },
            {
                "key": "burn_rate",
                "name": "Burn Rate",
                "description": "Monthly burn rate (expenses minus revenue)",
                "formula": "sum(expense) - sum(revenue)",
                "unit": "USD",
                "format_type": "currency",
            },
        ]
        
        created = []
        for m in system_metrics:
            existing = self.db.query(MetricDefinition).filter(
                MetricDefinition.company_id == company_id,
                MetricDefinition.key == m["key"],
            ).first()
            
            if not existing:
                metric = MetricDefinition(
                    company_id=company_id,
                    key=m["key"],
                    name=m["name"],
                    description=m["description"],
                    formula=m["formula"],
                    unit=m.get("unit"),
                    format_type=m.get("format_type", "number"),
                    is_system=True,
                )
                self.db.add(metric)
                created.append(metric)
        
        self.db.commit()
        return created
