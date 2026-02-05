"""
Suggestion Service - orchestrates suggestion generation and management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from server.models.metric_suggestion import MetricSuggestion, SuggestionEvent
from server.models.metric_definition import MetricDefinition
from server.metrics.suggestions.engine import SuggestionEngine
from server.metrics.suggestions.capability import CapabilityDiscovery
from server.metrics.suggestions.rules.base import SuggestionOutput

logger = logging.getLogger(__name__)


class SuggestionService:
    """
    Service for managing metric suggestions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.engine = SuggestionEngine()
    
    def generate_suggestions(
        self,
        company_id: int,
        data_source_id: Optional[int] = None,
        adapter_key: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestions for a company based on connected data sources.
        
        Args:
            company_id: The company ID
            data_source_id: Optional specific data source to generate for
            adapter_key: Optional specific adapter to use
            force_refresh: If True, rediscover capabilities first
        
        Returns:
            List of created/updated suggestions
        """
        if adapter_key and force_refresh:
            CapabilityDiscovery.discover_for_adapter(
                adapter_key, {}, self.db, company_id, data_source_id
            )
        
        all_capabilities = CapabilityDiscovery.get_all_capabilities(self.db, company_id)
        
        if not all_capabilities:
            logger.info(f"No capabilities found for company {company_id}")
            return []
        
        org_context = {
            "company_id": company_id,
            "available_adapters": list(all_capabilities.keys()),
        }
        
        suggestion_outputs = self.engine.run_all(all_capabilities, org_context)
        
        existing_metrics = [
            m.key for m in self.db.query(MetricDefinition).filter(
                MetricDefinition.company_id == company_id
            ).all()
        ]
        
        results = []
        for output in suggestion_outputs:
            is_satisfied, missing = self.engine.check_dependencies_satisfied(
                output, existing_metrics, org_context["available_adapters"]
            )
            
            status = "new" if is_satisfied else "blocked"
            
            suggestion = self._upsert_suggestion(
                company_id=company_id,
                data_source_id=data_source_id,
                output=output,
                status=status,
                missing_deps=missing if not is_satisfied else None
            )
            
            results.append(suggestion.to_dict())
        
        return results
    
    def _upsert_suggestion(
        self,
        company_id: int,
        data_source_id: Optional[int],
        output: SuggestionOutput,
        status: str,
        missing_deps: Optional[List[str]] = None
    ) -> MetricSuggestion:
        """
        Create or update a suggestion (idempotent by suggestion_key).
        """
        existing = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.company_id == company_id,
            MetricSuggestion.suggestion_key == output.suggestion_key
        ).first()
        
        reason = output.reason.copy()
        if missing_deps:
            reason["blocked_by"] = missing_deps
        
        if existing:
            if existing.status not in ["accepted", "dismissed"]:
                existing.title = output.title
                existing.description = output.description
                existing.category = output.category
                existing.metric_dsl_yaml = output.metric_dsl_yaml
                existing.dependencies = output.dependencies
                existing.confidence_score = output.confidence
                existing.reason = reason
                existing.status = status
                existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing
        else:
            suggestion = MetricSuggestion(
                company_id=company_id,
                data_source_id=data_source_id,
                suggestion_key=output.suggestion_key,
                title=output.title,
                description=output.description,
                category=output.category,
                metric_dsl_yaml=output.metric_dsl_yaml,
                dependencies=output.dependencies,
                confidence_score=output.confidence,
                reason=reason,
                status=status,
            )
            self.db.add(suggestion)
            self.db.commit()
            self.db.refresh(suggestion)
            
            self._log_event(company_id, suggestion.id, None, "generated", {
                "adapter_key": output.adapter_key,
                "confidence": output.confidence,
            })
            
            return suggestion
    
    def list_suggestions(
        self,
        company_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        data_source_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List suggestions with optional filters.
        """
        query = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.company_id == company_id
        )
        
        if status:
            query = query.filter(MetricSuggestion.status == status)
        if category:
            query = query.filter(MetricSuggestion.category == category)
        if data_source_id:
            query = query.filter(
                or_(
                    MetricSuggestion.data_source_id == data_source_id,
                    MetricSuggestion.data_source_id.is_(None)
                )
            )
        
        suggestions = query.order_by(
            MetricSuggestion.confidence_score.desc(),
            MetricSuggestion.created_at.desc()
        ).all()
        
        return [s.to_dict() for s in suggestions]
    
    def get_suggestion(self, suggestion_id: int, company_id: int) -> Optional[Dict[str, Any]]:
        """Get a single suggestion by ID."""
        suggestion = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.id == suggestion_id,
            MetricSuggestion.company_id == company_id
        ).first()
        
        return suggestion.to_dict() if suggestion else None
    
    def accept_suggestion(
        self,
        suggestion_id: int,
        company_id: int,
        user_id: Optional[int] = None,
        auto_compute: bool = False
    ) -> Dict[str, Any]:
        """
        Accept a suggestion and create the metric.
        
        Args:
            suggestion_id: The suggestion to accept
            company_id: Company ID for verification
            user_id: User accepting the suggestion
            auto_compute: Whether to immediately compute the metric
        
        Returns:
            Dict with created metric info
        """
        suggestion = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.id == suggestion_id,
            MetricSuggestion.company_id == company_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        if suggestion.status == "accepted":
            raise ValueError("Suggestion already accepted")
        
        import yaml
        try:
            dsl_data = yaml.safe_load(suggestion.metric_dsl_yaml)
            meta = dsl_data.get("meta", {})
        except Exception:
            meta = {}
        
        metric = MetricDefinition(
            company_id=company_id,
            key=meta.get("id", suggestion.suggestion_key),
            name=meta.get("name", suggestion.title),
            description=meta.get("description", suggestion.description),
            definition=suggestion.metric_dsl_yaml,
            grain=meta.get("grain", "monthly"),
            unit=meta.get("unit"),
            format_type=meta.get("format", "number"),
            status="draft",
            is_system=False,
            dependencies=suggestion.dependencies,
            tags=[suggestion.category.lower(), "suggested"],
        )
        
        self.db.add(metric)
        self.db.flush()
        
        suggestion.status = "accepted"
        suggestion.accepted_metric_id = metric.id
        suggestion.updated_at = datetime.utcnow()
        
        self._log_event(company_id, suggestion_id, user_id, "accepted", {
            "metric_id": metric.id,
            "metric_key": metric.key,
            "auto_compute": auto_compute,
        })
        
        self.db.commit()
        
        result = {
            "suggestion": suggestion.to_dict(),
            "metric": metric.to_dict(),
            "auto_compute_requested": auto_compute,
        }
        
        return result
    
    def dismiss_suggestion(
        self,
        suggestion_id: int,
        company_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dismiss a suggestion.
        """
        suggestion = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.id == suggestion_id,
            MetricSuggestion.company_id == company_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        suggestion.status = "dismissed"
        suggestion.updated_at = datetime.utcnow()
        
        self._log_event(company_id, suggestion_id, user_id, "dismissed", {
            "reason": reason
        })
        
        self.db.commit()
        
        return suggestion.to_dict()
    
    def explain_suggestion(
        self,
        suggestion_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed explanation for a suggestion.
        """
        suggestion = self.db.query(MetricSuggestion).filter(
            MetricSuggestion.id == suggestion_id,
            MetricSuggestion.company_id == company_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        compiled_sql = None
        try:
            from server.metrics.dsl.parser import MetricParser
            from server.metrics.dsl.compiler import MetricCompiler
            
            parsed = MetricParser.parse(suggestion.metric_dsl_yaml)
            if parsed.logic and parsed.logic.get("type") == "aggregate":
                compiled_sql = MetricCompiler.compile(parsed)
        except Exception as e:
            logger.warning(f"Could not compile suggestion DSL: {e}")
        
        return {
            "id": suggestion.id,
            "suggestion_key": suggestion.suggestion_key,
            "title": suggestion.title,
            "description": suggestion.description,
            "category": suggestion.category,
            "dependencies": suggestion.dependencies,
            "reason": suggestion.reason,
            "confidence_score": suggestion.confidence_score,
            "metric_dsl_yaml": suggestion.metric_dsl_yaml,
            "compiled_sql_preview": compiled_sql,
            "status": suggestion.status,
        }
    
    def _log_event(
        self,
        company_id: int,
        suggestion_id: int,
        actor_id: Optional[int],
        action: str,
        meta: Dict[str, Any]
    ) -> None:
        """Log a suggestion event."""
        event = SuggestionEvent(
            company_id=company_id,
            suggestion_id=suggestion_id,
            actor_id=actor_id,
            action=action,
            meta=meta,
        )
        self.db.add(event)
