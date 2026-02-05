"""
Metric DSL Validator - validates metric definitions for semantic correctness.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from server.metrics.dsl.schema import (
    MetricDSLSchema, 
    AggregateLogic, 
    ComposeLogic,
    FilterOperator,
    AggType,
)


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    level: str
    code: str
    message: str
    path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(self, code: str, message: str, path: Optional[str] = None):
        self.issues.append(ValidationIssue("error", code, message, path))
        self.is_valid = False
    
    def add_warning(self, code: str, message: str, path: Optional[str] = None):
        self.issues.append(ValidationIssue("warning", code, message, path))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "error_count": sum(1 for i in self.issues if i.level == "error"),
            "warning_count": sum(1 for i in self.issues if i.level == "warning"),
        }


class ValidationError(Exception):
    """Validation failed with errors."""
    def __init__(self, result: ValidationResult):
        self.result = result
        super().__init__(f"Validation failed with {len(result.issues)} issues")


class DSLValidator:
    """
    Semantic validator for Metric DSL definitions.
    
    Validates:
    - Metric ID format
    - Required fields
    - Operator usage
    - Macro syntax
    - Dependency references
    - Composed metric references
    """
    
    ALLOWED_MACROS = {"time_bucket", "coalesce", "to_number", "lower", "date_trunc"}
    RESERVED_FIELDS = {"id", "company_id", "occurred_at", "created_at", "payload"}
    MAX_ID_LENGTH = 100
    
    def __init__(self, schema: MetricDSLSchema):
        self.schema = schema
        self.result = ValidationResult()
    
    def validate(self) -> ValidationResult:
        """
        Run all validations on the schema.
        
        Returns:
            ValidationResult with all issues found
        """
        self._validate_meta()
        self._validate_dependencies()
        self._validate_mapping()
        self._validate_logic()
        self._validate_postprocess()
        
        return self.result
    
    def _validate_meta(self):
        """Validate metadata section."""
        meta = self.schema.meta
        
        if not meta.id:
            self.result.add_error("META_MISSING_ID", "Metric ID is required", "meta.id")
        elif not meta.id.replace("_", "").replace("-", "").isalnum():
            self.result.add_error(
                "META_INVALID_ID",
                "Metric ID must contain only alphanumeric characters, hyphens, and underscores",
                "meta.id"
            )
        elif len(meta.id) > self.MAX_ID_LENGTH:
            self.result.add_error(
                "META_ID_TOO_LONG",
                f"Metric ID must be {self.MAX_ID_LENGTH} characters or less",
                "meta.id"
            )
        
        if not meta.name:
            self.result.add_error("META_MISSING_NAME", "Metric name is required", "meta.name")
        
        if meta.unit and meta.unit not in {"USD", "%", "count", "days", "ratio", "number"}:
            self.result.add_warning(
                "META_UNUSUAL_UNIT",
                f"Unusual unit '{meta.unit}'. Common units: USD, %, count, days, ratio",
                "meta.unit"
            )
    
    def _validate_dependencies(self):
        """Validate dependency declarations."""
        seen_sources = set()
        for i, dep in enumerate(self.schema.dependencies):
            if not dep.data_source_type:
                self.result.add_error(
                    "DEP_MISSING_TYPE",
                    "Dependency must specify data_source_type",
                    f"dependencies[{i}].data_source_type"
                )
            
            source_key = f"{dep.data_source_type}:{dep.event_type or '*'}"
            if source_key in seen_sources:
                self.result.add_warning(
                    "DEP_DUPLICATE",
                    f"Duplicate dependency: {source_key}",
                    f"dependencies[{i}]"
                )
            seen_sources.add(source_key)
    
    def _validate_mapping(self):
        """Validate field mappings."""
        if not self.schema.mapping:
            return
        
        for field_name, jsonpath in self.schema.mapping.fields.items():
            if not jsonpath.startswith("$.") and not jsonpath.startswith("raw_events."):
                self.result.add_warning(
                    "MAPPING_UNUSUAL_PATH",
                    f"Field path '{jsonpath}' should start with '$.' for payload or 'raw_events.' for columns",
                    f"mapping.fields.{field_name}"
                )
            
            if field_name in self.RESERVED_FIELDS:
                self.result.add_warning(
                    "MAPPING_RESERVED_FIELD",
                    f"Field '{field_name}' is a reserved field name",
                    f"mapping.fields.{field_name}"
                )
    
    def _validate_logic(self):
        """Validate computation logic."""
        logic = self.schema.logic
        
        if isinstance(logic, AggregateLogic):
            self._validate_aggregate_logic(logic)
        elif isinstance(logic, ComposeLogic):
            self._validate_compose_logic(logic)
    
    def _validate_aggregate_logic(self, logic: AggregateLogic):
        """Validate aggregate-type logic."""
        if not logic.measures:
            self.result.add_error(
                "LOGIC_NO_MEASURES",
                "Aggregate logic must define at least one measure",
                "logic.measures"
            )
        
        measure_names = set()
        for i, measure in enumerate(logic.measures):
            if not measure.name:
                self.result.add_error(
                    "MEASURE_MISSING_NAME",
                    "Measure must have a name",
                    f"logic.measures[{i}].name"
                )
            
            if measure.name in measure_names:
                self.result.add_error(
                    "MEASURE_DUPLICATE_NAME",
                    f"Duplicate measure name: {measure.name}",
                    f"logic.measures[{i}].name"
                )
            measure_names.add(measure.name)
            
            if measure.agg == AggType.COUNT and measure.field != "*":
                self.result.add_warning(
                    "MEASURE_COUNT_WITH_FIELD",
                    "COUNT aggregation typically uses '*' as field",
                    f"logic.measures[{i}].field"
                )
        
        for i, dim in enumerate(logic.dimensions):
            self._validate_dimension_expr(dim.expr, f"logic.dimensions[{i}].expr")
    
    def _validate_dimension_expr(self, expr: str, path: str):
        """Validate dimension expression for allowed macros."""
        import re
        macro_pattern = r'(\w+)\s*\('
        for match in re.finditer(macro_pattern, expr):
            macro_name = match.group(1).lower()
            if macro_name not in self.ALLOWED_MACROS:
                self.result.add_warning(
                    "DIMENSION_UNKNOWN_MACRO",
                    f"Unknown macro '{macro_name}'. Allowed: {', '.join(self.ALLOWED_MACROS)}",
                    path
                )
    
    def _validate_compose_logic(self, logic: ComposeLogic):
        """Validate compose-type logic."""
        if not logic.metrics:
            self.result.add_error(
                "COMPOSE_NO_METRICS",
                "Composed metric must reference at least one other metric",
                "logic.metrics"
            )
        
        if not logic.expression:
            self.result.add_error(
                "COMPOSE_NO_EXPRESSION",
                "Composed metric must have an expression",
                "logic.expression"
            )
        
        metric_refs = {m.alias or m.metric_id for m in logic.metrics}
        
        import re
        expr_vars = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', logic.expression))
        expr_vars -= {"if", "else", "and", "or", "not", "true", "false"}
        
        for var in expr_vars:
            if var not in metric_refs:
                self.result.add_warning(
                    "COMPOSE_UNDEFINED_REF",
                    f"Variable '{var}' in expression not found in metric references",
                    "logic.expression"
                )
    
    def _validate_postprocess(self):
        """Validate postprocessing operations."""
        for i, op in enumerate(self.schema.postprocess):
            if op.op not in {"scale", "currency_convert", "clamp", "round", "abs"}:
                self.result.add_warning(
                    "POSTPROCESS_UNKNOWN_OP",
                    f"Unknown postprocess operation: {op.op}",
                    f"postprocess[{i}].op"
                )
            
            if op.op == "scale" and op.factor is None:
                self.result.add_error(
                    "POSTPROCESS_SCALE_NO_FACTOR",
                    "Scale operation requires 'factor'",
                    f"postprocess[{i}]"
                )
            
            if op.op == "clamp":
                if op.min is None and op.max is None:
                    self.result.add_error(
                        "POSTPROCESS_CLAMP_NO_BOUNDS",
                        "Clamp operation requires at least 'min' or 'max'",
                        f"postprocess[{i}]"
                    )
