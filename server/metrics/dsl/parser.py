"""
Metric DSL Parser - converts YAML definitions to structured schemas.
"""

import yaml
from typing import Any, Dict, Optional
from pydantic import ValidationError as PydanticValidationError
from server.metrics.dsl.schema import MetricDSLSchema


class DSLParseError(Exception):
    """Error during DSL parsing."""
    def __init__(self, message: str, line: Optional[int] = None, details: Optional[Dict] = None):
        self.message = message
        self.line = line
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "line": self.line,
            "details": self.details,
        }


class DSLParser:
    """
    Parser for Metric DSL definitions.
    Converts YAML text to validated MetricDSLSchema objects.
    """
    
    def __init__(self, yaml_content: str):
        self.yaml_content = yaml_content
        self._raw_dict: Optional[Dict] = None
        self._schema: Optional[MetricDSLSchema] = None
    
    def parse(self) -> MetricDSLSchema:
        """
        Parse YAML content into MetricDSLSchema.
        
        Returns:
            Validated MetricDSLSchema object
            
        Raises:
            DSLParseError: If parsing or validation fails
        """
        try:
            self._raw_dict = yaml.safe_load(self.yaml_content)
        except yaml.YAMLError as e:
            line = getattr(e, 'problem_mark', None)
            line_num = line.line + 1 if line else None
            raise DSLParseError(f"YAML syntax error: {e}", line=line_num)
        
        if not isinstance(self._raw_dict, dict):
            raise DSLParseError("Definition must be a YAML object/dictionary")
        
        if "meta" not in self._raw_dict:
            raise DSLParseError("Missing required 'meta' section")
        if "logic" not in self._raw_dict:
            raise DSLParseError("Missing required 'logic' section")
        
        try:
            self._schema = MetricDSLSchema(**self._raw_dict)
        except PydanticValidationError as e:
            errors = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
            raise DSLParseError(
                f"Validation failed: {'; '.join(errors)}",
                details={"validation_errors": e.errors()}
            )
        
        return self._schema
    
    @property
    def raw_dict(self) -> Optional[Dict]:
        """Get raw parsed dictionary."""
        return self._raw_dict
    
    @property
    def schema(self) -> Optional[MetricDSLSchema]:
        """Get validated schema."""
        return self._schema
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MetricDSLSchema:
        """
        Create schema from dictionary (already parsed YAML).
        
        Args:
            data: Dictionary representation of metric definition
            
        Returns:
            Validated MetricDSLSchema
        """
        yaml_str = yaml.dump(data)
        parser = cls(yaml_str)
        return parser.parse()
    
    @staticmethod
    def to_yaml(schema: MetricDSLSchema) -> str:
        """
        Convert schema back to YAML string.
        
        Args:
            schema: MetricDSLSchema object
            
        Returns:
            YAML string representation
        """
        return yaml.dump(schema.model_dump(exclude_none=True), default_flow_style=False)
