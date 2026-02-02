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
    status: str = Field(pattern="^(queued|running|completed|failed|cancelled)$")
    dataSnapshotId: Optional[str] = None
    output: Optional[SimulationOutput] = None
    error: Optional[str] = None
