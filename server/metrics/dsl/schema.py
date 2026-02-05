"""
Metric DSL Schema definitions using Pydantic.
Defines the structure of YAML metric definitions.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from enum import Enum


class GrainType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class StatusType(str, Enum):
    DRAFT = "draft"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"


class FilterOperator(str, Enum):
    EQ = "="
    NE = "!="
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"


class AggType(str, Enum):
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MAX = "max"
    MIN = "min"


class MetricMeta(BaseModel):
    """Metadata section of metric definition."""
    id: str = Field(..., description="Stable slug identifier for the metric")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")
    unit: Optional[str] = Field(None, description="Unit of measurement (USD, %, count)")
    grain: GrainType = Field(GrainType.MONTHLY, description="Time granularity")
    owners: List[str] = Field(default_factory=list, description="Metric owners")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    version: int = Field(1, description="Definition version number")
    status: StatusType = Field(StatusType.DRAFT, description="Lifecycle status")


class Dependency(BaseModel):
    """Data source dependency."""
    data_source_type: str = Field(..., description="Source type (stripe, quickbooks, ga4)")
    event_type: Optional[str] = Field(None, description="Event type filter")
    required: bool = Field(True, description="Whether dependency is required")


class TimeRange(BaseModel):
    """Time range configuration."""
    lookback_days: int = Field(365, description="Days to look back")


class CurrencyConfig(BaseModel):
    """Currency configuration."""
    base: str = Field("USD", description="Base currency")
    fx_source: Optional[str] = Field(None, description="FX rate source")


class FilterCondition(BaseModel):
    """Filter condition for data."""
    field: str = Field(..., description="Field to filter on")
    op: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(None, description="Filter value")


class InputsConfig(BaseModel):
    """Inputs configuration section."""
    time_range: Optional[TimeRange] = None
    currency: Optional[CurrencyConfig] = None
    filters: List[FilterCondition] = Field(default_factory=list)


class FieldMapping(BaseModel):
    """Field mapping from payload."""
    fields: Dict[str, str] = Field(default_factory=dict, description="Field name to JSONPath mapping")


class MeasureWhere(BaseModel):
    """Where clause for measure."""
    field: str
    op: FilterOperator
    value: Any


class Measure(BaseModel):
    """Aggregate measure definition."""
    name: str = Field(..., description="Measure name in output")
    agg: AggType = Field(..., description="Aggregation function")
    field: str = Field("*", description="Field to aggregate")
    where: List[MeasureWhere] = Field(default_factory=list, description="Filter conditions")


class Dimension(BaseModel):
    """Dimension for grouping."""
    name: str = Field(..., description="Dimension name")
    expr: str = Field(..., description="Expression for dimension")


class AggregateLogic(BaseModel):
    """Aggregate logic definition."""
    type: Literal["aggregate"] = "aggregate"
    source: str = Field("raw_events", description="Source table")
    measures: List[Measure] = Field(default_factory=list)
    dimensions: List[Dimension] = Field(default_factory=list)


class MetricReference(BaseModel):
    """Reference to another metric for composed metrics."""
    metric_id: str
    alias: Optional[str] = None


class ComposeLogic(BaseModel):
    """Composed metric logic (references other metrics)."""
    type: Literal["compose"] = "compose"
    metrics: List[MetricReference] = Field(default_factory=list)
    expression: str = Field(..., description="Formula referencing metric aliases")


class PostprocessOp(BaseModel):
    """Postprocessing operation."""
    op: str = Field(..., description="Operation type (scale, currency_convert, clamp)")
    factor: Optional[float] = None
    to: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None


class OutputConfig(BaseModel):
    """Output configuration."""
    primary_value: str = Field("value", description="Primary value field name")
    time_bucket: str = Field("time_bucket", description="Time bucket field name")


class MetricDSLSchema(BaseModel):
    """Complete metric DSL schema."""
    meta: MetricMeta
    dependencies: List[Dependency] = Field(default_factory=list)
    inputs: Optional[InputsConfig] = None
    mapping: Optional[FieldMapping] = None
    logic: AggregateLogic | ComposeLogic
    postprocess: List[PostprocessOp] = Field(default_factory=list)
    output: Optional[OutputConfig] = None
    
    class Config:
        extra = "forbid"
