# Copilot Trust Audit

**Last Updated**: 2026-02-02

## Overview
This document captures the architecture paths for the Copilot × Simulation Trust Refactor.

## Implementation Status

| Issue | Status | Notes |
|-------|--------|-------|
| COP-002: Missing Provenance | **IMPLEMENTED** | Provenance block added to chat responses |
| COP-008: Load Scenario Fabrication | **FIXED** | Returns NOT_AVAILABLE if no run exists |
| COP-009: Contradiction Handling | **IMPLEMENTED** | UNVERIFIED_MISMATCH detection added |
| COP-013: Strict Output Modes | **IMPLEMENTED** | Schema-locked response envelopes implemented |
| SIM-002/3/4: Validation Flags | **IMPLEMENTED** | compute_run_validation_flags() added |
| Grounding Rules | **IMPLEMENTED** | All agents updated with strict grounding rules |

### Known Limitations (Phase 2)

1. **Not All Paths Unified**: The copilot chat endpoint uses fetchVerifiedRunResult for main responses, but simulation_handler still uses direct SimulationRun queries. Full unification requires routing all simulation responses through the trust module.

2. **Dual Validation Sources**: There are two validation flag computations - one in `canonical_state.py` and one in `trust.py`. These should be consolidated into a single canonical implementation.

3. **Context-Aware UNVERIFIED_MISMATCH**: The simpler fetchVerifiedRunResult doesn't fully enforce UNVERIFIED_MISMATCH detection based on CopilotContext. For full enforcement, use `fetch_verified_run_result(ctx, db)` with a proper CopilotContext object.

## New Components

### 1. Trust Module (`server/copilot/trust.py`)
- `fetchVerifiedRunResult()`: Deterministic run fetching with grounding status
- `GroundingStatus` enum: VERIFIED, UNVERIFIED, NOT_AVAILABLE, UNVERIFIED_MISMATCH
- `RunResult` dataclass: Canonical run result with provenance

### 2. Grounding Rules (`server/copilot/grounding_rules.py`)
- Strict grounding rules for all agents
- Canonical data usage rules
- Provenance requirements

### 3. Validation Flags (`server/api/canonical_state.py`)
- `compute_run_validation_flags()`: Post-simulation validation
- Flags: runwayCashBurnMismatch, survivalRunwayMismatch, monteCarloZeroVariance

### 4. Tests (`server/tests/test_copilot_trust.py`)
- Acceptance tests for grounding, provenance, validation flags

## 1. Active Context Determination

### Company ID
- **Frontend Store**: `client/src/store/founderStore.ts` - `currentCompany.id`
- **API Context**: Passed via URL params `/companies/{company_id}/...`

### Scenario ID
- **Frontend State**: Managed in page components (e.g., `client/src/pages/scenarios.tsx`)
- **Top Bar Selection**: Currently not centralized; each page manages its own selected scenario
- **API**: Fetched via `/api/canonical/companies/{company_id}/scenarios`

### Run ID (Latest for Scenario)
- **Endpoint**: `GET /api/canonical/scenarios/{scenario_id}/runs/latest`
- **Backend**: `server/api/canonical_state.py:243-258`
- **Returns**: Latest completed run or `{status: "not_run"}`

## 2. Copilot Backend Entrypoints

### Main Endpoints (`server/api/copilot.py`)
| Endpoint | Purpose |
|----------|---------|
| `GET /companies/{company_id}/context` | Build context pack for Copilot |
| `POST /companies/{company_id}/simulate` | Quick simulation with deltas |
| `POST /companies/{company_id}/decision/compare` | Compare multiple decisions |
| `POST /companies/{company_id}/copilot/chat` | Main chat endpoint (lines ~400+) |

### Tools/Functions That Fetch Data
1. **`build_context_pack()`** - `server/copilot/context_pack.py`
   - Fetches company, truth scan, scenarios, latest runs
   
2. **`extract_metric_value()`** - `server/api/simulations.py:31-44`
   - Extracts numeric values from metric dicts
   
3. **Truth Scan Metrics** - Fetched from `TruthScan.outputs_json`

4. **Simulation Results** - Fetched from `SimulationRun.outputs_json`

5. **Scenario Lists** - Fetched via `Scenario` model queries

## 3. Current UI Displays

### Sidebar "Latest Simulation"
- **Component**: `client/src/components/app-sidebar.tsx`
- **Issue**: Does NOT currently show latest simulation metrics in sidebar
- **Fix Needed**: Add survival/runway display with proper data binding

### "Load Scenario" Behavior
- **Location**: Copilot chat handler processes "load scenario X" requests
- **Issue**: May fabricate zeros if no run exists
- **Fix Needed**: Use canonical run fetcher, return NOT_AVAILABLE if no run

### Run Metrics Display
- **Scenarios Page**: `client/src/pages/scenarios.tsx`
- **Decision Cards**: Show survival, runway from simulation outputs
- **Copilot Responses**: Currently may compute metrics instead of fetching canonical values

## 4. Canonical State API (`server/api/canonical_state.py`)

### Existing Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /canonical/companies/{company_id}/state` | Get canonical company state |
| `PUT /canonical/companies/{company_id}/state` | Update state (invalidates runs) |
| `GET /canonical/companies/{company_id}/scenarios` | List scenarios with latestRunId |
| `POST /canonical/companies/{company_id}/scenarios` | Create scenario |
| `PUT /canonical/scenarios/{scenario_id}` | Update scenario |
| `GET /canonical/scenarios/{scenario_id}/runs/latest` | Get latest run for scenario |
| `GET /canonical/runs/{run_id}` | Get specific run by ID |
| `POST /canonical/companies/{company_id}/scenarios/{scenario_id}/run` | Execute simulation |

### Schemas (`server/schemas/canonical.py`)
- `Provenance` - Basic provenance tracking
- `SimulationMetrics` - With P10/P50/P90 percentile metrics
- `SimulationOutput` - Full output including provenance
- `PercentileMetric` - p10, p50, p90 values

## 5. Issues Identified

### COP-002: Missing Provenance in Answers
- Copilot responses with numbers don't include provenance block
- No runId/scenarioId/timestamp citation

### COP-008: "Load Scenario" Fabrication
- May return zeros when no run exists instead of NOT_AVAILABLE

### COP-009: Contradiction Handling
- No detection of mismatch between Copilot response and UI-visible run

### COP-013: Strict Output Modes
- No schema-locked response envelopes
- No JSON-only or TOKEN-only modes

### SIM-002/3/4: Validation Flags
- No post-simulation validation flags for metric inconsistencies
- No runwayCashBurnMismatch, survivalRunwayMismatch detection

### Sidebar Binding
- Sidebar doesn't show latest simulation metrics
- No loading/error states for simulation data

## 6. Implementation Plan

1. **Extend RunResult schema** with validation flags and full provenance
2. **Create CopilotContext** schema for explicit context passing
3. **Implement fetchVerifiedRunResult()** deterministic fetcher
4. **Add CopilotEnvelope** with NARRATIVE/JSON/TOKEN modes
5. **Add provenance block** to all numeric Copilot responses
6. **Implement contradiction detection** and UNVERIFIED_MISMATCH
7. **Fix sidebar binding** to use canonical fetcher
8. **Add simulation validation flags** computed post-run
9. **Update Copilot prompts** with strict grounding rules

---
*Generated: 2026-02-02*
