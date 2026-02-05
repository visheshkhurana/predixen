"""
Metric Engine - computes metrics from raw data events using DSL or formula.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import yaml

from server.models.raw_data_event import RawDataEvent
from server.models.metric_definition import MetricDefinition
from server.models.metric_value import MetricValue
from server.metrics.formula_parser import FormulaParser, FormulaError

logger = logging.getLogger(__name__)


class MetricEngine:
    """
    Engine for computing metrics from raw data events.
    
    Supports two computation modes:
    1. DSL mode: Uses YAML definition with DSL compiler for SQL execution
    2. Formula mode: Uses simple formula parser for in-memory evaluation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def recompute_all_metrics(self, company_id: int) -> Dict[str, Any]:
        """
        Recompute all metrics for a company.
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
        Uses DSL mode if definition exists, otherwise falls back to formula mode.
        """
        if metric.definition:
            return self._compute_with_dsl(metric, period_start, period_end)
        else:
            return self._compute_with_formula(metric, period_start, period_end)
    
    def _compute_with_dsl(
        self,
        metric: MetricDefinition,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> MetricValue:
        """Compute metric using DSL compiler."""
        from server.metrics.dsl.parser import DSLParser
        from server.metrics.dsl.compiler import DSLCompiler
        
        parser = DSLParser(metric.definition)
        schema = parser.parse()
        
        compiler = DSLCompiler(schema, metric.company_id)
        compiled = compiler.compile()
        
        now = datetime.utcnow()
        if period_start is None:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_end is None:
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        try:
            result = self.db.execute(
                text(compiled.sql),
                {f"param_{i+1}": p for i, p in enumerate(compiled.params)}
            )
            row = result.fetchone()
            value = float(row[1]) if row and row[1] is not None else 0.0
        except Exception as e:
            logger.error(f"SQL execution error for metric {metric.key}: {e}")
            value = 0.0
        
        existing = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric.id,
            MetricValue.period_start == period_start,
        ).first()
        
        if existing:
            existing.value = value
            existing.computed_at = now
            existing.metric_version = metric.version
            existing.source_versions = compiled.lineage
            existing.compiled_sql = compiled.sql[:2000]
            metric_value = existing
        else:
            metric_value = MetricValue(
                metric_id=metric.id,
                company_id=metric.company_id,
                value=value,
                period_start=period_start,
                period_end=period_end,
                metric_version=metric.version,
                source_versions=compiled.lineage,
                compiled_sql=compiled.sql[:2000],
            )
            self.db.add(metric_value)
        
        self.db.commit()
        return metric_value
    
    def _compute_with_formula(
        self,
        metric: MetricDefinition,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> MetricValue:
        """Compute metric using legacy formula parser."""
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
            parser = FormulaParser(metric.formula or "count()")
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
        """Get historical values for a metric."""
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
    
    SNAPSHOT_KEY_MAP = {
        "mrr": "mrr",
        "arr": "arr",
        "revenue": "monthly_revenue",
        "total_revenue": "monthly_revenue",
        "burn_rate": "net_burn",
        "runway": "runway_months",
        "gross_margin": "gross_margin",
        "churn_rate": "churn_rate",
        "customer_count": "headcount",
        "cash_balance": "cash_balance",
        "cac": "cac",
        "ltv": "ltv",
        "ltv_cac_ratio": "ltv_cac_ratio",
        "headcount": "headcount",
        "net_burn": "net_burn",
    }

    def _get_snapshot_value(self, company_id: int, metric_key: str) -> Optional[float]:
        """Fall back to real-time KPI snapshot for a metric value."""
        from server.api.realtime import get_company_kpi_metrics
        snapshot_key = self.SNAPSHOT_KEY_MAP.get(metric_key)
        if not snapshot_key:
            return None
        try:
            snapshot = get_company_kpi_metrics(company_id, self.db)
            val = snapshot.get(snapshot_key)
            return float(val) if val is not None else None
        except Exception:
            return None

    def get_metric_latest(
        self,
        company_id: int,
        metric_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the latest value for a metric, falling back to real-time snapshot."""
        metric = self.db.query(MetricDefinition).filter(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == metric_key,
        ).first()
        
        if not metric:
            return None
        
        value = self.db.query(MetricValue).filter(
            MetricValue.metric_id == metric.id,
        ).order_by(MetricValue.period_start.desc()).first()
        
        if value:
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

        snapshot_val = self._get_snapshot_value(company_id, metric_key)
        if snapshot_val is not None:
            now = datetime.utcnow()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return {
                "metric_key": metric_key,
                "metric_name": metric.name,
                "value": snapshot_val,
                "unit": metric.unit,
                "format_type": metric.format_type,
                "period_start": period_start.isoformat(),
                "period_end": now.isoformat(),
                "computed_at": now.isoformat(),
                "raw_event_count": 0,
                "contributing_connectors": ["financial_records"],
            }

        return None
    
    def get_metric_lineage(
        self,
        company_id: int,
        metric_key: str,
        time_bucket: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get lineage information for a metric value."""
        metric = self.db.query(MetricDefinition).filter(
            MetricDefinition.company_id == company_id,
            MetricDefinition.key == metric_key,
        ).first()
        
        if not metric:
            return None
        
        query = self.db.query(MetricValue).filter(MetricValue.metric_id == metric.id)
        
        if time_bucket:
            bucket_date = datetime.fromisoformat(time_bucket)
            query = query.filter(MetricValue.period_start == bucket_date)
        
        value = query.order_by(MetricValue.period_start.desc()).first()
        
        if not value:
            return None
        
        return {
            "metric_key": metric_key,
            "metric_version": value.metric_version,
            "compiled_sql": value.compiled_sql if metric.definition else None,
            "dependencies": metric.dependencies,
            "source_versions": value.source_versions,
            "raw_event_count": value.raw_event_count,
            "contributing_connectors": value.contributing_connectors,
            "period_start": value.period_start.isoformat(),
            "computed_at": value.computed_at.isoformat() if value.computed_at else None,
        }
    
    def create_system_metrics(self, company_id: int) -> List[MetricDefinition]:
        """Create default system metrics for a company."""
        from server.metrics.templates import SYSTEM_METRIC_TEMPLATES
        
        created = []
        for template in SYSTEM_METRIC_TEMPLATES:
            existing = self.db.query(MetricDefinition).filter(
                MetricDefinition.company_id == company_id,
                MetricDefinition.key == template["key"],
            ).first()
            
            if not existing:
                metric = MetricDefinition(
                    company_id=company_id,
                    key=template["key"],
                    name=template["name"],
                    description=template.get("description"),
                    formula=template.get("formula"),
                    definition=template.get("definition"),
                    unit=template.get("unit"),
                    format_type=template.get("format_type", "number"),
                    grain=template.get("grain", "monthly"),
                    is_system=True,
                    dependencies=template.get("dependencies"),
                    tags=template.get("tags"),
                )
                self.db.add(metric)
                created.append(metric)
        
        self.db.commit()
        return created
    
    def validate_definition(self, definition_yaml: str) -> Dict[str, Any]:
        """Validate a metric definition without saving."""
        from server.metrics.dsl.parser import DSLParser, DSLParseError
        from server.metrics.dsl.validator import DSLValidator
        
        try:
            parser = DSLParser(definition_yaml)
            schema = parser.parse()
        except DSLParseError as e:
            return {
                "is_valid": False,
                "parse_error": e.to_dict(),
                "validation_result": None,
            }
        
        validator = DSLValidator(schema)
        result = validator.validate()
        
        return {
            "is_valid": result.is_valid,
            "parse_error": None,
            "validation_result": result.to_dict(),
            "parsed_meta": schema.meta.model_dump() if result.is_valid else None,
        }
