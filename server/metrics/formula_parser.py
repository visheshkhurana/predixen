"""
Formula DSL parser for metric computations.

Supports:
- sum(field)
- avg(field)
- count()
- min(field), max(field)
- Arithmetic: sum(revenue) - sum(cost)
- Filters: sum(amount) where status == "active"
"""

import re
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass


class FormulaError(Exception):
    """Error in formula parsing or evaluation."""
    pass


@dataclass
class AggregateFunction:
    """Represents an aggregate function call."""
    name: str
    field: Optional[str]
    filter_field: Optional[str] = None
    filter_op: Optional[str] = None
    filter_value: Optional[str] = None


class FormulaParser:
    """
    Parser and evaluator for the metric formula DSL.
    
    Examples:
        sum(revenue)
        avg(amount)
        count()
        sum(amount) - sum(cost)
        sum(amount) where status == "active"
    """
    
    AGGREGATE_FUNCTIONS = {"sum", "avg", "count", "min", "max", "first", "last"}
    OPERATORS = {"+": lambda a, b: a + b, "-": lambda a, b: a - b, "*": lambda a, b: a * b, "/": lambda a, b: a / b if b != 0 else 0}
    COMPARISONS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}
    
    PATTERN_FUNC = re.compile(r'(\w+)\(([^)]*)\)')
    PATTERN_WHERE = re.compile(r'(.+?)\s+where\s+(\w+)\s*(==|!=|>|<|>=|<=)\s*["\']?([^"\']+)["\']?', re.IGNORECASE)
    
    def __init__(self, formula: str):
        self.formula = formula.strip()
        self.parsed = self._parse()
    
    def _parse(self) -> Dict[str, Any]:
        """Parse the formula into an AST-like structure."""
        formula = self.formula
        
        where_match = self.PATTERN_WHERE.match(formula)
        filter_clause = None
        if where_match:
            formula = where_match.group(1).strip()
            filter_clause = {
                "field": where_match.group(2),
                "op": where_match.group(3),
                "value": where_match.group(4),
            }
        
        tokens = self._tokenize(formula)
        
        return {
            "tokens": tokens,
            "filter": filter_clause,
        }
    
    def _tokenize(self, expr: str) -> List[Dict[str, Any]]:
        """Tokenize the expression into functions and operators."""
        tokens = []
        i = 0
        expr = expr.strip()
        
        while i < len(expr):
            if expr[i].isspace():
                i += 1
                continue
            
            if expr[i] in "+-*/":
                tokens.append({"type": "operator", "value": expr[i]})
                i += 1
                continue
            
            func_match = self.PATTERN_FUNC.match(expr[i:])
            if func_match:
                func_name = func_match.group(1).lower()
                func_arg = func_match.group(2).strip() or None
                
                if func_name not in self.AGGREGATE_FUNCTIONS:
                    raise FormulaError(f"Unknown function: {func_name}")
                
                tokens.append({
                    "type": "function",
                    "name": func_name,
                    "field": func_arg,
                })
                i += func_match.end()
                continue
            
            if expr[i].isalnum() or expr[i] == '_':
                start = i
                while i < len(expr) and (expr[i].isalnum() or expr[i] == '_'):
                    i += 1
                tokens.append({"type": "field", "value": expr[start:i]})
                continue
            
            i += 1
        
        return tokens
    
    def evaluate(self, data: List[Dict[str, Any]]) -> float:
        """
        Evaluate the formula against a list of data records.
        
        Args:
            data: List of dictionaries representing raw data events
            
        Returns:
            Computed metric value
        """
        filter_clause = self.parsed.get("filter")
        if filter_clause:
            op = self.COMPARISONS.get(filter_clause["op"])
            if op:
                data = [
                    d for d in data
                    if filter_clause["field"] in d 
                    and op(str(d[filter_clause["field"]]), filter_clause["value"])
                ]
        
        tokens = self.parsed["tokens"]
        
        if len(tokens) == 1 and tokens[0]["type"] == "function":
            return self._evaluate_function(tokens[0], data)
        
        result = None
        pending_op = None
        
        for token in tokens:
            if token["type"] == "operator":
                pending_op = token["value"]
            elif token["type"] == "function":
                value = self._evaluate_function(token, data)
                if result is None:
                    result = value
                elif pending_op:
                    result = self.OPERATORS[pending_op](result, value)
                    pending_op = None
        
        return result if result is not None else 0.0
    
    def _evaluate_function(self, func: Dict[str, Any], data: List[Dict[str, Any]]) -> float:
        """Evaluate a single aggregate function."""
        name = func["name"]
        field = func.get("field")
        
        if name == "count":
            return float(len(data))
        
        if not field:
            raise FormulaError(f"Function {name} requires a field argument")
        
        values = []
        for d in data:
            if field in d:
                val = d[field]
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass
        
        if not values:
            return 0.0
        
        if name == "sum":
            return sum(values)
        elif name == "avg":
            return sum(values) / len(values)
        elif name == "min":
            return min(values)
        elif name == "max":
            return max(values)
        elif name == "first":
            return values[0]
        elif name == "last":
            return values[-1]
        
        return 0.0
    
    def get_required_fields(self) -> List[str]:
        """Get list of fields required by this formula."""
        fields = set()
        
        for token in self.parsed["tokens"]:
            if token["type"] == "function" and token.get("field"):
                fields.add(token["field"])
        
        if self.parsed.get("filter"):
            fields.add(self.parsed["filter"]["field"])
        
        return list(fields)
