from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CalibratedInput:
    value: float
    confidence: ConfidenceLevel
    source: str
    is_imputed: bool = False
    original_value: Optional[float] = None
    benchmark_range: Optional[Tuple[float, float]] = None


@dataclass
class CalibrationResult:
    inputs: Dict[str, CalibratedInput]
    warnings: List[str] = field(default_factory=list)
    overall_confidence_score: float = 0.0


INDUSTRY_BENCHMARKS = {
    "saas": {
        "churn_rate": {"p25": 2.0, "p50": 4.0, "p75": 7.0, "default": 4.0},
        "gross_margin": {"p25": 65.0, "p50": 75.0, "p75": 85.0, "default": 75.0},
        "cac": {"p25": 200.0, "p50": 500.0, "p75": 1200.0, "default": 500.0},
        "dso": {"p25": 30.0, "p50": 45.0, "p75": 60.0, "default": 45.0},
        "growth_rate": {"p25": 5.0, "p50": 10.0, "p75": 20.0, "default": 10.0},
        "conversion_rate": {"p25": 2.0, "p50": 5.0, "p75": 10.0, "default": 5.0},
        "arpu": {"p25": 100.0, "p50": 300.0, "p75": 1000.0, "default": 300.0},
        "ltv_cac_ratio": {"p25": 2.0, "p50": 3.0, "p75": 5.0, "default": 3.0},
        "burn_multiple": {"p25": 1.0, "p50": 2.0, "p75": 4.0, "default": 2.0},
        "magic_number": {"p25": 0.5, "p50": 0.75, "p75": 1.0, "default": 0.75},
    },
    "fintech": {
        "churn_rate": {"p25": 1.5, "p50": 3.0, "p75": 5.0, "default": 3.0},
        "gross_margin": {"p25": 50.0, "p50": 65.0, "p75": 80.0, "default": 65.0},
        "cac": {"p25": 300.0, "p50": 800.0, "p75": 2000.0, "default": 800.0},
        "dso": {"p25": 25.0, "p50": 40.0, "p75": 55.0, "default": 40.0},
        "growth_rate": {"p25": 8.0, "p50": 15.0, "p75": 30.0, "default": 15.0},
        "conversion_rate": {"p25": 1.5, "p50": 4.0, "p75": 8.0, "default": 4.0},
        "arpu": {"p25": 50.0, "p50": 200.0, "p75": 800.0, "default": 200.0},
        "ltv_cac_ratio": {"p25": 2.5, "p50": 4.0, "p75": 6.0, "default": 4.0},
        "burn_multiple": {"p25": 1.5, "p50": 2.5, "p75": 5.0, "default": 2.5},
        "magic_number": {"p25": 0.4, "p50": 0.6, "p75": 0.9, "default": 0.6},
    },
    "marketplace": {
        "churn_rate": {"p25": 3.0, "p50": 6.0, "p75": 10.0, "default": 6.0},
        "gross_margin": {"p25": 30.0, "p50": 50.0, "p75": 70.0, "default": 50.0},
        "cac": {"p25": 50.0, "p50": 150.0, "p75": 400.0, "default": 150.0},
        "dso": {"p25": 15.0, "p50": 30.0, "p75": 45.0, "default": 30.0},
        "growth_rate": {"p25": 10.0, "p50": 20.0, "p75": 40.0, "default": 20.0},
        "conversion_rate": {"p25": 1.0, "p50": 3.0, "p75": 6.0, "default": 3.0},
        "arpu": {"p25": 20.0, "p50": 80.0, "p75": 250.0, "default": 80.0},
        "ltv_cac_ratio": {"p25": 1.5, "p50": 2.5, "p75": 4.0, "default": 2.5},
        "burn_multiple": {"p25": 2.0, "p50": 3.5, "p75": 6.0, "default": 3.5},
        "magic_number": {"p25": 0.3, "p50": 0.5, "p75": 0.8, "default": 0.5},
    },
    "default": {
        "churn_rate": {"p25": 2.5, "p50": 5.0, "p75": 8.0, "default": 5.0},
        "gross_margin": {"p25": 50.0, "p50": 65.0, "p75": 80.0, "default": 65.0},
        "cac": {"p25": 200.0, "p50": 500.0, "p75": 1000.0, "default": 500.0},
        "dso": {"p25": 30.0, "p50": 45.0, "p75": 60.0, "default": 45.0},
        "growth_rate": {"p25": 5.0, "p50": 10.0, "p75": 20.0, "default": 10.0},
        "conversion_rate": {"p25": 2.0, "p50": 5.0, "p75": 8.0, "default": 5.0},
        "arpu": {"p25": 100.0, "p50": 300.0, "p75": 800.0, "default": 300.0},
        "ltv_cac_ratio": {"p25": 2.0, "p50": 3.0, "p75": 4.5, "default": 3.0},
        "burn_multiple": {"p25": 1.5, "p50": 2.5, "p75": 5.0, "default": 2.5},
        "magic_number": {"p25": 0.4, "p50": 0.6, "p75": 0.9, "default": 0.6},
    },
}

VALIDATION_RULES = {
    "churn_rate": {"min": 0.0, "max": 100.0},
    "gross_margin": {"min": -100.0, "max": 100.0},
    "cac": {"min": 0.0, "max": 100000.0},
    "dso": {"min": 0.0, "max": 365.0},
    "growth_rate": {"min": -100.0, "max": 500.0},
    "conversion_rate": {"min": 0.0, "max": 100.0},
    "arpu": {"min": 0.0, "max": 1000000.0},
    "baseline_mrr": {"min": 0.0, "max": 1000000000.0},
    "cash_balance": {"min": 0.0, "max": 10000000000.0},
    "opex": {"min": 0.0, "max": 1000000000.0},
    "payroll": {"min": 0.0, "max": 1000000000.0},
    "headcount": {"min": 1, "max": 100000},
    "total_customers": {"min": 0, "max": 10000000},
}


class InputCalibrator:
    
    def __init__(self, industry: str = "saas"):
        self.industry = industry.lower() if industry else "default"
        self.benchmarks = INDUSTRY_BENCHMARKS.get(self.industry, INDUSTRY_BENCHMARKS["default"])
    
    def validate_input(self, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        if value is None:
            return True, None
        
        rules = VALIDATION_RULES.get(key)
        if not rules:
            return True, None
        
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return False, f"{key} must be a number"
        
        if numeric_value < rules["min"]:
            return False, f"{key} cannot be less than {rules['min']}"
        if numeric_value > rules["max"]:
            return False, f"{key} cannot be greater than {rules['max']}"
        
        return True, None
    
    def impute_missing(self, key: str, provided_inputs: Dict[str, Any]) -> Optional[float]:
        benchmark = self.benchmarks.get(key)
        if benchmark:
            return benchmark["default"]
        
        if key == "arpu" and "baseline_mrr" in provided_inputs and "total_customers" in provided_inputs:
            mrr = provided_inputs["baseline_mrr"]
            customers = provided_inputs["total_customers"]
            if customers and customers > 0:
                return mrr / customers
        
        if key == "total_customers" and "baseline_mrr" in provided_inputs and "arpu" in provided_inputs:
            mrr = provided_inputs["baseline_mrr"]
            arpu = provided_inputs["arpu"]
            if arpu and arpu > 0:
                return mrr / arpu
        
        return None
    
    def get_confidence(self, key: str, value: Any, source: str, is_imputed: bool) -> ConfidenceLevel:
        if is_imputed:
            return ConfidenceLevel.LOW
        
        if source == "user_provided":
            return ConfidenceLevel.HIGH
        elif source == "extracted_verified":
            return ConfidenceLevel.HIGH
        elif source == "extracted":
            return ConfidenceLevel.MEDIUM
        elif source == "derived":
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def get_benchmark_range(self, key: str) -> Optional[Tuple[float, float]]:
        benchmark = self.benchmarks.get(key)
        if benchmark:
            return (benchmark["p25"], benchmark["p75"])
        return None
    
    def normalize_units(self, key: str, value: float, unit: str = "monthly") -> float:
        annual_metrics = ["arr", "annual_revenue", "annual_burn"]
        monthly_metrics = ["mrr", "monthly_revenue", "monthly_burn", "baseline_mrr"]
        
        if key in annual_metrics and unit == "monthly":
            return value * 12
        elif key in monthly_metrics and unit == "annual":
            return value / 12
        
        return value
    
    def calibrate(
        self, 
        raw_inputs: Dict[str, Any],
        sources: Optional[Dict[str, str]] = None,
        required_fields: Optional[List[str]] = None
    ) -> CalibrationResult:
        sources = sources or {}
        required_fields = required_fields or [
            "baseline_mrr", "cash_balance", "gross_margin", "growth_rate", "churn_rate"
        ]
        
        calibrated = {}
        warnings = []
        
        for key, value in raw_inputs.items():
            is_valid, error = self.validate_input(key, value)
            if not is_valid:
                warnings.append(error or f"Invalid value for {key}")
                continue
            
            source = sources.get(key, "user_provided")
            is_imputed = False
            original_value = value
            
            if value is None:
                imputed_value = self.impute_missing(key, raw_inputs)
                if imputed_value is not None:
                    value = imputed_value
                    is_imputed = True
                    warnings.append(f"{key} imputed from industry benchmarks ({self.industry})")
                else:
                    continue
            
            confidence = self.get_confidence(key, value, source, is_imputed)
            benchmark_range = self.get_benchmark_range(key)
            
            calibrated[key] = CalibratedInput(
                value=float(value),
                confidence=confidence,
                source=source,
                is_imputed=is_imputed,
                original_value=original_value if is_imputed else None,
                benchmark_range=benchmark_range
            )
        
        for req_field in required_fields:
            if req_field not in calibrated:
                imputed_value = self.impute_missing(req_field, raw_inputs)
                if imputed_value is not None:
                    calibrated[req_field] = CalibratedInput(
                        value=imputed_value,
                        confidence=ConfidenceLevel.LOW,
                        source="benchmark_imputed",
                        is_imputed=True,
                        benchmark_range=self.get_benchmark_range(req_field)
                    )
                    warnings.append(f"Required field {req_field} imputed from benchmarks")
                else:
                    warnings.append(f"Required field {req_field} is missing and could not be imputed")
        
        total_fields = len(calibrated)
        if total_fields > 0:
            confidence_scores = {
                ConfidenceLevel.HIGH: 1.0,
                ConfidenceLevel.MEDIUM: 0.7,
                ConfidenceLevel.LOW: 0.4
            }
            total_score = sum(
                confidence_scores[inp.confidence] 
                for inp in calibrated.values()
            )
            overall_confidence = (total_score / total_fields) * 100
        else:
            overall_confidence = 0.0
        
        return CalibrationResult(
            inputs=calibrated,
            warnings=warnings,
            overall_confidence_score=overall_confidence
        )
    
    def to_simulation_inputs(self, calibration_result: CalibrationResult) -> Dict[str, float]:
        return {
            key: inp.value 
            for key, inp in calibration_result.inputs.items()
        }
    
    def get_confidence_summary(self, calibration_result: CalibrationResult) -> Dict[str, Any]:
        high_count = sum(1 for inp in calibration_result.inputs.values() if inp.confidence == ConfidenceLevel.HIGH)
        medium_count = sum(1 for inp in calibration_result.inputs.values() if inp.confidence == ConfidenceLevel.MEDIUM)
        low_count = sum(1 for inp in calibration_result.inputs.values() if inp.confidence == ConfidenceLevel.LOW)
        imputed_count = sum(1 for inp in calibration_result.inputs.values() if inp.is_imputed)
        
        return {
            "overall_score": round(calibration_result.overall_confidence_score, 1),
            "high_confidence_count": high_count,
            "medium_confidence_count": medium_count,
            "low_confidence_count": low_count,
            "imputed_count": imputed_count,
            "total_fields": len(calibration_result.inputs),
            "warnings": calibration_result.warnings,
            "fields": {
                key: {
                    "value": inp.value,
                    "confidence": inp.confidence.value,
                    "source": inp.source,
                    "is_imputed": inp.is_imputed,
                    "benchmark_range": inp.benchmark_range
                }
                for key, inp in calibration_result.inputs.items()
            }
        }
