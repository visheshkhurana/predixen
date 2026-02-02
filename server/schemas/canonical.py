"""
Canonical Data Types for Decision-Trust System.

These types define the single source of truth contract for company state,
scenario overrides, simulation inputs/outputs, and provenance tracking.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib
import json


def stable_stringify(obj: Any) -> str:
    """Create a stable JSON string with sorted keys for consistent hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def compute_hash(obj: Any) -> str:
    """Compute a SHA256 hash of an object for snapshotting."""
    stable_json = stable_stringify(obj)
    return hashlib.sha256(stable_json.encode('utf-8')).hexdigest()[:16]


class Financials(BaseModel):
    """Core financial metrics for a company."""
    cashBalance: float = Field(ge=0, description="Current cash on hand")
    monthlyBurn: float = Field(description="Monthly burn rate (positive = burning, negative = profitable)")
    revenueMonthly: float = Field(ge=0, default=0, description="Monthly revenue")
    revenueGrowthRate: float = Field(default=0, description="Monthly revenue growth rate as decimal (0.05 = 5%)")
    expensesMonthly: float = Field(ge=0, default=0, description="Total monthly expenses")


class FundraisingRoundSummary(BaseModel):
    """Summary of a fundraising round."""
    roundId: str
    type: str
    amount: float
    date: Optional[str] = None


class CompanyStateSchema(BaseModel):
    """Canonical company state - single source of truth for all modules."""
    companyId: int
    environment: str = Field(default="user", pattern="^(user|demo)$")
    updatedAt: Optional[datetime] = None
    snapshotId: str
    financials: Financials
    fundraisingRounds: List[FundraisingRoundSummary] = []
    stateJson: Optional[Dict[str, Any]] = None


class ScenarioOverrides(BaseModel):
    """Scenario parameter overrides applied on top of base company state."""
    expenseMultiplier: Optional[float] = Field(default=None, description="Expense multiplier (0.8 = -20%)")
    revenueGrowthDelta: Optional[float] = Field(default=None, description="Added to base growth rate (+0.03 = +3pp)")
    pricingDelta: Optional[float] = Field(default=None, description="Pricing adjustment (+0.1 = +10%)")
    hiringRateDelta: Optional[float] = Field(default=None, description="Hiring rate adjustment")
    fundraisingTimingShiftMonths: Optional[int] = Field(default=None, description="Shift fundraising by N months")
    fundraisingAddRounds: Optional[List[Dict[str, Any]]] = Field(default=None, description="Additional funding rounds")


class SimulationConfig(BaseModel):
    """Configuration for Monte Carlo simulation."""
    horizonMonths: int = Field(default=36, ge=1, le=264, description="Projection horizon in months")
    numPaths: int = Field(default=2000, ge=100, le=50000, description="Number of simulation paths")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class SimulationInput(BaseModel):
    """Frozen snapshot of simulation inputs for reproducibility."""
    companyId: int
    scenarioId: int
    runId: int
    dataSnapshotId: str
    asOf: datetime
    base: Financials
    overrides: ScenarioOverrides
    config: SimulationConfig


class PercentileMetric(BaseModel):
    """P10/P50/P90 percentile values."""
    p10: float
    p50: float
    p90: float


class SimulationMetrics(BaseModel):
    """Computed metrics from Monte Carlo simulation."""
    runwayMonths: PercentileMetric
    survival18mo: float = Field(ge=0, le=1, description="Probability of surviving 18 months")
    cashEnd: PercentileMetric
    burn: PercentileMetric


class Provenance(BaseModel):
    """Provenance tracking for simulation outputs."""
    updatedAt: datetime
    source: str = Field(pattern="^(actuals|scenario)$")
    inputHash: str
    dataSnapshotId: Optional[str] = None
    runId: Optional[int] = None
    scenarioId: Optional[int] = None


class SimulationOutput(BaseModel):
    """Complete output from a simulation run."""
    runId: int
    scenarioId: int
    companyId: int
    dataSnapshotId: str
    deterministic: bool = Field(description="True if P10=P50=P90 (no variance)")
    metrics: SimulationMetrics
    provenance: Provenance
    series: Optional[Dict[str, Any]] = Field(default=None, description="Time series data if available")
    debug: Optional[Dict[str, Any]] = None


class CompanyStateUpdate(BaseModel):
    """Request to update canonical company state."""
    financials: Optional[Financials] = None
    fundraisingRounds: Optional[List[FundraisingRoundSummary]] = None


class CreateScenarioRequest(BaseModel):
    """Request to create a new scenario."""
    name: str
    description: Optional[str] = None
    overrides: ScenarioOverrides = Field(default_factory=ScenarioOverrides)
    tags: List[str] = []


class UpdateScenarioRequest(BaseModel):
    """Request to update an existing scenario."""
    name: Optional[str] = None
    description: Optional[str] = None
    overrides: Optional[ScenarioOverrides] = None
    tags: Optional[List[str]] = None


class RunSimulationRequest(BaseModel):
    """Request to run a simulation for a scenario."""
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class RunSimulationResponse(BaseModel):
    """Response from running a simulation."""
    runId: int
    status: str = Field(pattern="^(queued|running|completed|failed|cancelled|invalid)$")
    dataSnapshotId: Optional[str] = None
    output: Optional[SimulationOutput] = None
    error: Optional[str] = None


class ValidationFlags(BaseModel):
    """Validation flags for simulation result integrity checks."""
    runwayCashBurnMismatch: bool = Field(
        default=False, 
        description="True if runway_p50 doesn't match cash/burn calculation within tolerance"
    )
    survivalRunwayMismatch: bool = Field(
        default=False, 
        description="True if runway >> 18mo but survival18 == 0 (or inverse)"
    )
    monteCarloZeroVariance: bool = Field(
        default=False, 
        description="True if P10=P50=P90 when model expected stochastic output"
    )
    notes: List[str] = Field(default_factory=list, description="Validation notes/warnings")

    def has_critical_issues(self) -> bool:
        """Return True if any critical validation flags are set."""
        return self.runwayCashBurnMismatch or self.survivalRunwayMismatch


class RunResultMetrics(BaseModel):
    """Metrics from a simulation run with P10/P50/P90 for Monte Carlo outputs."""
    runwayMonths: PercentileMetric
    survival6mo: float = Field(ge=0, le=1, description="Probability of surviving 6 months")
    survival12mo: float = Field(ge=0, le=1, description="Probability of surviving 12 months")
    survival18mo: float = Field(ge=0, le=1, description="Probability of surviving 18 months")
    survival24mo: float = Field(ge=0, le=1, description="Probability of surviving 24 months")
    cashBalance: float = Field(description="Current cash balance")
    netBurn: float = Field(description="Net monthly burn rate")
    cashEnd: Optional[PercentileMetric] = Field(default=None, description="Ending cash by horizon")


class RunResult(BaseModel):
    """
    Canonical simulation run result - the single source of truth for Copilot grounding.
    
    This is the contract that ensures Copilot never invents numeric facts.
    All numbers must come from a canonical run payload identified by (companyId, scenarioId, runId).
    """
    companyId: int
    scenarioId: int
    scenarioName: str
    runId: int
    runTimestamp: datetime
    dataSnapshotId: str = Field(description="Hash of company_state at run time")
    status: str = Field(pattern="^(queued|running|completed|failed|invalid)$")
    metrics: Optional[RunResultMetrics] = Field(
        default=None, 
        description="Metrics only present for completed runs"
    )
    validation: Optional[ValidationFlags] = Field(
        default=None, 
        description="Validation flags computed post-run"
    )
    inputHash: Optional[str] = Field(default=None, description="Hash of simulation inputs")


class ProvenanceBlock(BaseModel):
    """
    Provenance block for Copilot responses - must be present in all numeric outputs.
    
    This enables verification that Copilot answers match the canonical run.
    """
    companyId: int
    scenarioId: int
    scenarioName: str
    runId: int
    runTimestamp: datetime
    dataSnapshotId: str
    status: str
    validationFlags: Optional[List[str]] = Field(
        default=None, 
        description="List of validation flag names that are True"
    )

    @classmethod
    def from_run_result(cls, run: RunResult) -> "ProvenanceBlock":
        """Create a ProvenanceBlock from a RunResult."""
        flags = []
        if run.validation:
            if run.validation.runwayCashBurnMismatch:
                flags.append("runwayCashBurnMismatch")
            if run.validation.survivalRunwayMismatch:
                flags.append("survivalRunwayMismatch")
            if run.validation.monteCarloZeroVariance:
                flags.append("monteCarloZeroVariance")
        
        return cls(
            companyId=run.companyId,
            scenarioId=run.scenarioId,
            scenarioName=run.scenarioName,
            runId=run.runId,
            runTimestamp=run.runTimestamp,
            dataSnapshotId=run.dataSnapshotId,
            status=run.status,
            validationFlags=flags if flags else None,
        )


class CopilotContext(BaseModel):
    """
    Active context that must be passed with EVERY Copilot message.
    
    This ensures Copilot always knows exactly which company/scenario/run is active.
    """
    companyId: int
    activeScenarioId: Optional[int] = Field(
        default=None, 
        description="Currently selected scenario (e.g., from results page)"
    )
    activeRunId: Optional[int] = Field(
        default=None, 
        description="Currently selected run (if on results page)"
    )
    topBarScenarioId: Optional[int] = Field(
        default=None, 
        description="Scenario selected in top bar (if exists)"
    )
    mode: str = Field(
        default="FREE", 
        pattern="^(LOCKED_TO_ACTIVE|FREE)$",
        description="LOCKED_TO_ACTIVE: Copilot must use active context. FREE: Can ask for clarification"
    )
    uiSurface: Optional[str] = Field(
        default=None,
        pattern="^(SIM_RESULTS|SIM_BUILDER|TRUTH_SCAN|OVERVIEW|COPILOT)$",
        description="Which UI surface the user is on"
    )


class CopilotResponseNarrative(BaseModel):
    """Narrative response from Copilot."""
    kind: str = Field(default="NARRATIVE", pattern="^NARRATIVE$")
    text: str
    provenance: Optional[ProvenanceBlock] = None


class CopilotResponseJson(BaseModel):
    """Structured JSON response from Copilot."""
    kind: str = Field(default="JSON", pattern="^JSON$")
    json: Dict[str, Any]
    provenance: Optional[ProvenanceBlock] = None


class CopilotResponseToken(BaseModel):
    """Single token response for automated checks."""
    kind: str = Field(default="TOKEN", pattern="^TOKEN$")
    token: str = Field(
        pattern="^(OK|NOT_AVAILABLE|UNVERIFIED_NO_RUN|UNVERIFIED_MISMATCH|MISSING_INPUTS|UNKNOWN_SURVIVAL_DEFINITION|INVALID_RUN)$"
    )
    message: Optional[str] = Field(default=None, description="Optional explanation")


# Union type for all possible Copilot response envelopes
CopilotEnvelope = CopilotResponseNarrative | CopilotResponseJson | CopilotResponseToken
