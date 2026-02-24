"""
Copilot Trust Module - Grounding and Provenance for Decision-Trust System.

This module implements the trust contract for Copilot:
- Deterministic run result fetching (never compute metrics, always fetch canonical values)
- Validation flag computation
- Provenance block generation
- Contradiction detection
"""

from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging


class GroundingStatus(Enum):
    """Grounding status for Copilot responses."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNVERIFIED_MISMATCH = "UNVERIFIED_MISMATCH"


@dataclass
class SimpleProvenance:
    """Simple provenance information for copilot responses."""
    company_id: int
    scenario_id: Optional[int]
    run_id: Optional[int]
    run_timestamp: Optional[datetime]
    data_snapshot_id: Optional[str]
    status: Optional[str]


@dataclass
class SimpleRunResult:
    """Simple run result for copilot integration."""
    grounding_status: GroundingStatus
    run_id: Optional[int]
    outputs: Optional[dict]
    provenance: Optional[SimpleProvenance]
    message: Optional[str] = None

from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.company_state import CompanyState
from server.schemas.canonical import (
    RunResult,
    RunResultMetrics,
    ValidationFlags,
    ProvenanceBlock,
    PercentileMetric,
    CopilotContext,
    CopilotResponseToken,
    CopilotResponseNarrative,
    CopilotEnvelope,
)

logger = logging.getLogger(__name__)

RUNWAY_TOLERANCE = 2.0


def compute_validation_flags(
    metrics: RunResultMetrics,
    cash_balance: float,
    net_burn: float,
) -> ValidationFlags:
    """
    Compute validation flags for a simulation run.
    
    These flags detect inconsistencies that should prevent Copilot from
    making recommendations based on potentially incorrect data.
    """
    flags = ValidationFlags()
    notes: List[str] = []
    
    if net_burn > 0 and cash_balance > 0:
        simple_runway = cash_balance / net_burn
        runway_p50 = metrics.runwayMonths.p50
        if abs(runway_p50 - simple_runway) > RUNWAY_TOLERANCE:
            flags.runwayCashBurnMismatch = True
            notes.append(
                f"Runway mismatch: P50={runway_p50:.1f}mo vs simple={simple_runway:.1f}mo"
            )
    
    runway_p50 = metrics.runwayMonths.p50
    survival18 = metrics.survival18mo
    
    if runway_p50 > 24 and survival18 < 0.5:
        flags.survivalRunwayMismatch = True
        notes.append(
            f"Survival mismatch: runway_p50={runway_p50:.1f}mo > 24 but survival18={survival18:.2%}"
        )
    elif runway_p50 < 12 and survival18 > 0.95:
        flags.survivalRunwayMismatch = True
        notes.append(
            f"Survival mismatch: runway_p50={runway_p50:.1f}mo < 12 but survival18={survival18:.2%}"
        )
    
    if (
        metrics.runwayMonths.p10 == metrics.runwayMonths.p50 == metrics.runwayMonths.p90
        and metrics.cashEnd
        and metrics.cashEnd.p10 == metrics.cashEnd.p50 == metrics.cashEnd.p90
    ):
        flags.monteCarloZeroVariance = True
        notes.append("Zero variance detected: P10=P50=P90 in Monte Carlo output")
    
    flags.notes = notes
    return flags


def extract_run_result_metrics(outputs_json: dict) -> Optional[RunResultMetrics]:
    """Extract RunResultMetrics from a simulation run outputs_json."""
    if not outputs_json:
        return None
    
    try:
        runway = outputs_json.get("runway_months", {})
        if isinstance(runway, dict):
            runway_metric = PercentileMetric(
                p10=float(runway.get("p10", 0)),
                p50=float(runway.get("p50", 0)),
                p90=float(runway.get("p90", 0)),
            )
        else:
            runway_val = float(runway) if runway else 0
            runway_metric = PercentileMetric(p10=runway_val, p50=runway_val, p90=runway_val)
        
        survival = outputs_json.get("survival_probability", {})
        if isinstance(survival, dict):
            survival_6 = float(survival.get("6mo", survival.get("6", 1.0)))
            survival_12 = float(survival.get("12mo", survival.get("12", 1.0)))
            survival_18 = float(survival.get("18mo", survival.get("18", 1.0)))
            survival_24 = float(survival.get("24mo", survival.get("24", 0.5)))
        else:
            survival_val = float(survival) if survival else 0.5
            survival_6 = survival_12 = survival_18 = survival_24 = survival_val
        
        cash_balance = float(outputs_json.get("cash_balance", 0))
        net_burn = float(outputs_json.get("net_burn", outputs_json.get("monthly_burn", 0)))
        
        cash_end = outputs_json.get("cash_end", outputs_json.get("ending_cash", {}))
        cash_end_metric = None
        if isinstance(cash_end, dict) and cash_end:
            cash_end_metric = PercentileMetric(
                p10=float(cash_end.get("p10", 0)),
                p50=float(cash_end.get("p50", 0)),
                p90=float(cash_end.get("p90", 0)),
            )
        
        return RunResultMetrics(
            runwayMonths=runway_metric,
            survival6mo=survival_6,
            survival12mo=survival_12,
            survival18mo=survival_18,
            survival24mo=survival_24,
            cashBalance=cash_balance,
            netBurn=net_burn,
            cashEnd=cash_end_metric,
        )
    except Exception as e:
        logger.error(f"Failed to extract run metrics: {e}")
        return None


def fetch_verified_run_result(
    ctx: CopilotContext,
    db: Session,
) -> Tuple[Optional[RunResult], Optional[str]]:
    """
    Fetch a verified simulation run result for the given context.
    
    This is a DETERMINISTIC function - it does NOT compute metrics, only fetches
    canonical values from the database.
    
    Returns:
        Tuple of (RunResult, error_message)
        - If successful: (RunResult, None)
        - If no run: (None, "UNVERIFIED_NO_RUN")
        - If mismatch: (None, "UNVERIFIED_MISMATCH")
        - If invalid: (RunResult with status="invalid", None)
    """
    run: Optional[SimulationRun] = None
    scenario: Optional[Scenario] = None
    
    if ctx.activeRunId:
        run = db.query(SimulationRun).filter(SimulationRun.id == ctx.activeRunId).first()
        if run:
            scenario = db.query(Scenario).filter(Scenario.id == run.scenario_id).first()
            if scenario and scenario.company_id != ctx.companyId:
                logger.warning(
                    f"Run {ctx.activeRunId} belongs to company {scenario.company_id}, "
                    f"not {ctx.companyId}"
                )
                return None, "UNVERIFIED_MISMATCH"
    
    if not run:
        scenario_id = ctx.activeScenarioId or ctx.topBarScenarioId
        if scenario_id:
            scenario = db.query(Scenario).filter(
                Scenario.id == scenario_id,
                Scenario.company_id == ctx.companyId
            ).first()
            
            if scenario:
                run = db.query(SimulationRun).filter(
                    SimulationRun.scenario_id == scenario_id
                ).order_by(SimulationRun.created_at.desc()).first()
    
    if not run:
        scenarios = db.query(Scenario).filter(
            Scenario.company_id == ctx.companyId,
            Scenario.is_archived == 0
        ).order_by(Scenario.updated_at.desc()).all()
        
        for s in scenarios:
            latest_run = db.query(SimulationRun).filter(
                SimulationRun.scenario_id == s.id
            ).order_by(SimulationRun.created_at.desc()).first()
            if latest_run:
                run = latest_run
                scenario = s
                break
    
    if not run:
        return None, "UNVERIFIED_NO_RUN"
    
    if not scenario:
        scenario = db.query(Scenario).filter(Scenario.id == run.scenario_id).first()
    
    if not scenario:
        return None, "UNVERIFIED_NO_RUN"
    
    metrics = extract_run_result_metrics(run.outputs_json)
    
    state = db.query(CompanyState).filter(
        CompanyState.company_id == ctx.companyId
    ).first()
    
    validation = None
    if metrics and run.status == "completed":
        cash_balance = state.cash_balance if state else 0
        net_burn = state.monthly_burn if state else 0
        validation = compute_validation_flags(metrics, cash_balance, net_burn)
        
        if validation.has_critical_issues():
            run.status = "invalid"
    
    data_snapshot_id = run.data_snapshot_id or (state.snapshot_id if state else "unknown")
    input_hash = run.input_hash if hasattr(run, 'input_hash') else None
    
    result = RunResult(
        companyId=ctx.companyId,
        scenarioId=scenario.id,
        scenarioName=scenario.name,
        runId=run.id,
        runTimestamp=run.created_at,
        dataSnapshotId=data_snapshot_id,
        status=run.status,
        metrics=metrics,
        validation=validation,
        inputHash=input_hash,
    )
    
    return result, None


def create_provenance_block(run_result: RunResult) -> ProvenanceBlock:
    """Create a ProvenanceBlock from a RunResult."""
    return ProvenanceBlock.from_run_result(run_result)


def format_provenance_markdown(provenance: ProvenanceBlock) -> str:
    """Format a ProvenanceBlock as a markdown string for display."""
    lines = [
        "",
        "---",
        "**Provenance:**",
        f"- CompanyId: {provenance.companyId}",
        f"- Scenario: {provenance.scenarioName} (ID: {provenance.scenarioId})",
        f"- RunId: {provenance.runId}",
        f"- Run time: {provenance.runTimestamp.isoformat() if provenance.runTimestamp else 'N/A'}",
        f"- Data snapshot: {provenance.dataSnapshotId}",
        f"- Status: {provenance.status}",
    ]
    
    if provenance.validationFlags:
        lines.append(f"- Validation flags: {', '.join(provenance.validationFlags)}")
    
    return "\n".join(lines)


def create_unverified_response(
    token: str,
    message: Optional[str] = None,
) -> CopilotResponseToken:
    """Create an UNVERIFIED token response."""
    default_messages = {
        "UNVERIFIED_NO_RUN": "No simulation run available. Please run a scenario first.",
        "UNVERIFIED_MISMATCH": "Run ID does not match active context. Please refresh and try again.",
        "NOT_AVAILABLE": "The requested information is not available.",
        "MISSING_INPUTS": "Required inputs are missing. Please provide company and scenario context.",
        "INVALID_RUN": "The simulation run has validation errors. Recommendations cannot be made.",
    }
    
    return CopilotResponseToken(
        kind="TOKEN",
        token=token,
        message=message or default_messages.get(token, ""),
    )


def validate_context(ctx: CopilotContext) -> Optional[CopilotResponseToken]:
    """
    Validate the Copilot context.
    
    Returns None if valid, or an error token response if invalid.
    """
    if not ctx.companyId:
        return create_unverified_response("MISSING_INPUTS", "Company ID is required")
    
    if ctx.mode == "LOCKED_TO_ACTIVE":
        if not ctx.activeScenarioId and not ctx.topBarScenarioId:
            return create_unverified_response(
                "MISSING_INPUTS",
                "Locked mode requires an active scenario. Please select a scenario first."
            )
    
    return None


def fetchVerifiedRunResult(
    db: Session,
    company_id: int,
    scenario_id: Optional[int] = None,
) -> SimpleRunResult:
    """
    Simple function to fetch a verified run result for copilot integration.
    
    This is a simpler alternative to fetch_verified_run_result that doesn't
    require a full CopilotContext object.
    
    Args:
        db: Database session
        company_id: Company ID
        scenario_id: Optional scenario ID (if None, finds latest run across all scenarios)
    
    Returns:
        SimpleRunResult with grounding status, outputs, and provenance
    """
    run: Optional[SimulationRun] = None
    scenario: Optional[Scenario] = None
    
    if scenario_id:
        scenario = db.query(Scenario).filter(
            Scenario.id == scenario_id,
            Scenario.company_id == company_id
        ).first()
        
        if scenario:
            run = db.query(SimulationRun).filter(
                SimulationRun.scenario_id == scenario_id
            ).order_by(SimulationRun.created_at.desc()).first()
    else:
        scenarios = db.query(Scenario).filter(
            Scenario.company_id == company_id,
        ).order_by(Scenario.updated_at.desc()).all()
        
        for s in scenarios:
            latest_run = db.query(SimulationRun).filter(
                SimulationRun.scenario_id == s.id
            ).order_by(SimulationRun.created_at.desc()).first()
            if latest_run:
                run = latest_run
                scenario = s
                break
    
    if not run:
        return SimpleRunResult(
            grounding_status=GroundingStatus.NOT_AVAILABLE,
            run_id=None,
            outputs=None,
            provenance=None,
            message="No simulation run exists for this scenario"
        )
    
    if not scenario:
        scenario = db.query(Scenario).filter(Scenario.id == run.scenario_id).first()
    
    if run.status == "invalid":
        grounding = GroundingStatus.UNVERIFIED
    elif run.status == "completed":
        grounding = GroundingStatus.VERIFIED
    else:
        grounding = GroundingStatus.UNVERIFIED
    
    resolved_scenario_id: Optional[int] = None
    for candidate in (
        scenario_id,
        getattr(run, "scenario_id", None),
        getattr(scenario, "id", None),
    ):
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            resolved_scenario_id = candidate
            break

    provenance = SimpleProvenance(
        company_id=company_id,
        scenario_id=resolved_scenario_id,
        run_id=run.id,
        run_timestamp=run.created_at,
        data_snapshot_id=getattr(run, 'data_snapshot_id', None),
        status=run.status
    )
    
    return SimpleRunResult(
        grounding_status=grounding,
        run_id=run.id,
        outputs=run.outputs_json,
        provenance=provenance
    )


def should_include_provenance(response_text: str) -> bool:
    """Determine if a response contains numeric facts that require provenance."""
    import re
    
    numeric_patterns = [
        r'\$[\d,]+',
        r'\d+\s*months?',
        r'\d+\.?\d*\s*%',
        r'P\d+\s*[=:]\s*\d+',
        r'runway\s*[=:]\s*\d+',
        r'survival\s*[=:]\s*\d+',
        r'\d+\s*mo\b',
    ]
    
    for pattern in numeric_patterns:
        if re.search(pattern, response_text, re.IGNORECASE):
            return True
    
    return False


def detect_output_mode(prompt: str) -> str:
    """Detect the requested output mode from the user prompt."""
    prompt_lower = prompt.lower()
    
    if "json only" in prompt_lower or "respond in json" in prompt_lower:
        return "JSON"
    if "one token only" in prompt_lower or "single token" in prompt_lower:
        return "TOKEN"
    
    return "NARRATIVE"
