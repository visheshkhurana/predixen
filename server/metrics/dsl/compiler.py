"""
Metric DSL Compiler - converts validated DSL schemas to safe parameterized SQL.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from server.metrics.dsl.schema import (
    MetricDSLSchema,
    AggregateLogic,
    ComposeLogic,
    FilterOperator,
    AggType,
    Measure,
    MeasureWhere,
)
from server.metrics.dsl.macros import expand_expression, time_bucket_macro


@dataclass
class CompiledQuery:
    """Result of DSL compilation."""
    sql: str
    params: List[Any]
    lineage: Dict[str, Any]
    grain: str
    metric_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "params": self.params,
            "lineage": self.lineage,
            "grain": self.grain,
            "metric_id": self.metric_id,
        }


class CompileError(Exception):
    """Error during DSL compilation."""
    pass


class DSLCompiler:
    """
    Compiles MetricDSLSchema to parameterized PostgreSQL queries.
    
    Generates safe SQL that:
    - Scopes all queries by company_id
    - Filters by data source types and event types
    - Applies time range lookback
    - Extracts fields from payload using safe jsonb operators
    - Aggregates measures with time bucketing
    - Applies postprocessing operations
    """
    
    OPERATOR_MAP = {
        FilterOperator.EQ: "=",
        FilterOperator.NE: "!=",
        FilterOperator.GT: ">",
        FilterOperator.GTE: ">=",
        FilterOperator.LT: "<",
        FilterOperator.LTE: "<=",
        FilterOperator.IN: "IN",
        FilterOperator.NOT_IN: "NOT IN",
        FilterOperator.CONTAINS: "ILIKE",
    }
    
    AGG_FUNC_MAP = {
        AggType.SUM: "SUM",
        AggType.COUNT: "COUNT",
        AggType.AVG: "AVG",
        AggType.MAX: "MAX",
        AggType.MIN: "MIN",
    }
    
    def __init__(self, schema: MetricDSLSchema, company_id: int):
        self.schema = schema
        self.company_id = company_id
        self.params: List[Any] = []
        self.param_counter = 0
        self.lineage: Dict[str, Any] = {
            "data_source_types": [],
            "event_types": [],
            "extracted_fields": [],
        }
    
    def compile(self) -> CompiledQuery:
        """
        Compile the schema to a parameterized SQL query.
        
        Returns:
            CompiledQuery with SQL, params, and lineage
        """
        logic = self.schema.logic
        
        if isinstance(logic, AggregateLogic):
            sql = self._compile_aggregate()
        elif isinstance(logic, ComposeLogic):
            sql = self._compile_compose()
        else:
            raise CompileError(f"Unknown logic type: {type(logic)}")
        
        return CompiledQuery(
            sql=sql,
            params=self.params,
            lineage=self.lineage,
            grain=self.schema.meta.grain.value,
            metric_id=self.schema.meta.id,
        )
    
    def _add_param(self, value: Any) -> str:
        """Add a parameter and return its placeholder."""
        self.param_counter += 1
        self.params.append(value)
        return f"${self.param_counter}"
    
    def _get_field_expr(self, field_name: str) -> str:
        """
        Get SQL expression for a field, handling payload extraction.
        
        Args:
            field_name: Field name from DSL
            
        Returns:
            SQL expression to extract the field value
        """
        if self.schema.mapping and field_name in self.schema.mapping.fields:
            jsonpath = self.schema.mapping.fields[field_name]
            return self._jsonpath_to_sql(jsonpath)
        
        if field_name == "*":
            return "*"
        
        return f"(payload->>'{field_name}')::NUMERIC"
    
    def _jsonpath_to_sql(self, jsonpath: str) -> str:
        """
        Convert JSONPath-like selector to safe PostgreSQL jsonb extraction.
        
        Args:
            jsonpath: JSONPath like "$.amount" or "$.customer.id"
            
        Returns:
            SQL expression for jsonb extraction
        """
        if jsonpath.startswith("raw_events."):
            return jsonpath.replace("raw_events.", "")
        
        if jsonpath.startswith("$."):
            path = jsonpath[2:]
        else:
            path = jsonpath
        
        parts = path.split(".")
        
        if len(parts) == 1:
            return f"(payload->>'{parts[0]}')"
        else:
            path_expr = "->".join(f"'{p}'" for p in parts[:-1])
            return f"(payload->{path_expr}->>'{parts[-1]}')"
    
    def _compile_aggregate(self) -> str:
        """Compile aggregate logic to SQL."""
        logic: AggregateLogic = self.schema.logic
        grain = self.schema.meta.grain.value
        
        time_bucket_expr = time_bucket_macro(grain, "occurred_at")
        
        select_parts = [f"{time_bucket_expr} AS time_bucket"]
        
        for measure in logic.measures:
            measure_sql = self._compile_measure(measure)
            select_parts.append(f"{measure_sql} AS {measure.name}")
            self.lineage["extracted_fields"].append(measure.field)
        
        where_clauses = [f"company_id = {self._add_param(self.company_id)}"]
        
        if self.schema.dependencies:
            source_types = []
            event_types = []
            for dep in self.schema.dependencies:
                source_types.append(dep.data_source_type)
                self.lineage["data_source_types"].append(dep.data_source_type)
                if dep.event_type:
                    event_types.append(dep.event_type)
                    self.lineage["event_types"].append(dep.event_type)
            
            if source_types:
                placeholders = ", ".join(self._add_param(s) for s in source_types)
                where_clauses.append(f"source IN ({placeholders})")
            
            if event_types:
                placeholders = ", ".join(self._add_param(e) for e in event_types)
                where_clauses.append(f"(payload->>'type') IN ({placeholders})")
        
        if self.schema.inputs and self.schema.inputs.time_range:
            lookback = self.schema.inputs.time_range.lookback_days
            cutoff = datetime.utcnow() - timedelta(days=lookback)
            where_clauses.append(f"occurred_at >= {self._add_param(cutoff)}")
        
        if self.schema.inputs and self.schema.inputs.filters:
            for f in self.schema.inputs.filters:
                filter_sql = self._compile_filter(f.field, f.op, f.value)
                where_clauses.append(filter_sql)
        
        sql = f"""
SELECT
    {', '.join(select_parts)}
FROM raw_data_events
WHERE {' AND '.join(where_clauses)}
GROUP BY time_bucket
ORDER BY time_bucket DESC
"""
        
        postprocess_sql = self._apply_postprocess(sql.strip())
        
        return postprocess_sql
    
    def _compile_measure(self, measure: Measure) -> str:
        """Compile a single measure to SQL."""
        agg_func = self.AGG_FUNC_MAP[measure.agg]
        
        if measure.agg == AggType.COUNT:
            if measure.where:
                where_expr = self._compile_measure_where(measure.where)
                return f"COUNT(CASE WHEN {where_expr} THEN 1 END)"
            return "COUNT(*)"
        
        field_expr = self._get_field_expr(measure.field)
        
        if measure.where:
            where_expr = self._compile_measure_where(measure.where)
            return f"{agg_func}(CASE WHEN {where_expr} THEN CAST({field_expr} AS NUMERIC) END)"
        
        return f"{agg_func}(CAST({field_expr} AS NUMERIC))"
    
    def _compile_measure_where(self, conditions: List[MeasureWhere]) -> str:
        """Compile measure WHERE conditions."""
        parts = []
        for cond in conditions:
            field_expr = self._get_field_expr(cond.field)
            op = self.OPERATOR_MAP[cond.op]
            
            if cond.op == FilterOperator.CONTAINS:
                parts.append(f"{field_expr} ILIKE {self._add_param(f'%{cond.value}%')}")
            elif cond.op in (FilterOperator.IN, FilterOperator.NOT_IN):
                if isinstance(cond.value, list):
                    placeholders = ", ".join(self._add_param(v) for v in cond.value)
                else:
                    placeholders = self._add_param(cond.value)
                parts.append(f"{field_expr} {op} ({placeholders})")
            else:
                parts.append(f"{field_expr} {op} {self._add_param(cond.value)}")
        
        return " AND ".join(parts)
    
    def _compile_filter(self, field: str, op: FilterOperator, value: Any) -> str:
        """Compile a filter condition."""
        field_expr = self._get_field_expr(field)
        op_sql = self.OPERATOR_MAP[op]
        
        if op == FilterOperator.CONTAINS:
            return f"{field_expr} ILIKE {self._add_param(f'%{value}%')}"
        elif op in (FilterOperator.IN, FilterOperator.NOT_IN):
            if isinstance(value, list):
                placeholders = ", ".join(self._add_param(v) for v in value)
            else:
                placeholders = self._add_param(value)
            return f"{field_expr} {op_sql} ({placeholders})"
        else:
            return f"{field_expr} {op_sql} {self._add_param(value)}"
    
    def _compile_compose(self) -> str:
        """Compile composed metric logic to SQL."""
        logic: ComposeLogic = self.schema.logic
        grain = self.schema.meta.grain.value
        
        ctes = []
        for metric_ref in logic.metrics:
            alias = metric_ref.alias or metric_ref.metric_id
            cte_sql = f"""
{alias} AS (
    SELECT time_bucket, value
    FROM metric_values mv
    JOIN metric_definitions md ON mv.metric_id = md.id
    WHERE md.company_id = {self._add_param(self.company_id)}
    AND md.key = {self._add_param(metric_ref.metric_id)}
)"""
            ctes.append(cte_sql)
            self.lineage["extracted_fields"].append(metric_ref.metric_id)
        
        aliases = [m.alias or m.metric_id for m in logic.metrics]
        
        join_parts = [f"{aliases[0]} m0"]
        for i, alias in enumerate(aliases[1:], 1):
            join_parts.append(f"JOIN {alias} m{i} ON m0.time_bucket = m{i}.time_bucket")
        
        expr = logic.expression
        for i, alias in enumerate(aliases):
            expr = expr.replace(alias, f"m{i}.value")
        
        sql = f"""
WITH {', '.join(ctes)}
SELECT
    m0.time_bucket AS time_bucket,
    ({expr}) AS value
FROM {' '.join(join_parts)}
ORDER BY time_bucket DESC
"""
        
        return sql.strip()
    
    def _apply_postprocess(self, sql: str) -> str:
        """Apply postprocessing operations by wrapping SQL."""
        if not self.schema.postprocess:
            return sql
        
        value_expr = "value"
        for op in self.schema.postprocess:
            if op.op == "scale" and op.factor is not None:
                value_expr = f"({value_expr}) * {op.factor}"
            elif op.op == "clamp":
                if op.min is not None and op.max is not None:
                    value_expr = f"LEAST(GREATEST({value_expr}, {op.min}), {op.max})"
                elif op.min is not None:
                    value_expr = f"GREATEST({value_expr}, {op.min})"
                elif op.max is not None:
                    value_expr = f"LEAST({value_expr}, {op.max})"
            elif op.op == "round":
                value_expr = f"ROUND({value_expr})"
            elif op.op == "abs":
                value_expr = f"ABS({value_expr})"
        
        return f"""
SELECT
    time_bucket,
    {value_expr} AS value
FROM ({sql}) AS base_query
"""
