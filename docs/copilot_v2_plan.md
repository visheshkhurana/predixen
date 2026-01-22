# Copilot v2 Architecture Plan

## Current Architecture Analysis

### Existing Stack

**Frontend (client/src/pages/copilot.tsx)**
- Chat interface with structured response display
- Mock fallback mode when API unavailable
- Data source badges showing agent contributions
- Collapsible sections for agent outputs

**Backend API (server/api/copilot.py)**
- `/companies/{company_id}/chat` - Main chat endpoint
- `/companies/{company_id}/ckb` - GET/PUT CKB endpoints
- Request model: `CopilotChatRequest` with message, include_financials, include_market, include_strategy
- Response model: `CopilotChatResponse` with executive_summary, company_snapshot, financials, etc.

**Agent System (server/copilot/agents/)**
- `router.py` - RouterAgent routes to specialists based on keyword matching
- `cfo_agent.py` - CFOAgent for financial analysis, FX conversion, metrics
- `market_agent.py` - MarketAgent for competitors, ICP, benchmarks
- `strategy_agent.py` - StrategyAgent for GTM, vertical expansion, 30/60/90 plans
- `base.py` - BaseAgent, AgentResponse, CompanyKnowledgeBase dataclasses

**CKB Storage (server/copilot/ckb_storage.py)**
- Persists to `companies.metadata_json` column
- Current structure: overview, financials, market, strategy, icp, competitors, risks, decisions_made

**Message Storage**: Currently NO message persistence - messages are session-only in frontend state

**Scenarios**: Existing `Scenario` model in `server/models/scenario.py` - used for simulation scenarios

### V2 Additions Location Map

| Feature | Files to Create/Modify |
|---------|----------------------|
| CKB v2 Layers | `server/copilot/agents/base.py`, `server/copilot/ckb_storage.py` |
| Decision Objects | `server/models/decision.py` (NEW), `server/api/decisions.py` (NEW) |
| Company Scenarios | `server/models/company_scenario.py` (NEW), `server/api/scenarios.py` (NEW) |
| Enhanced Chat API | `server/api/copilot.py` |
| Challenge Mode | `server/copilot/agents/strategy_agent.py` |
| Investor Lens | All agents |
| Market Agent Targets | `server/copilot/agents/market_agent.py` |
| Memo Export | `server/api/memo.py` (NEW) |
| UI Upgrades | `client/src/pages/copilot.tsx`, `client/src/pages/decisions.tsx` (NEW), `client/src/pages/scenarios.tsx` (NEW) |

## Data Model Changes

### 1. CKB v2 Layers
```python
class CompanyKnowledgeBaseV2:
    company_id: int
    company_name: str
    
    # Layers
    facts: Dict[str, Any]       # Extracted business facts + financials
    beliefs: List[Belief]       # Assumptions with timestamps
    decisions: List[str]        # References to company_decisions
    outcomes: List[Outcome]     # Results tied to decisions
    
    # Legacy fields (kept for compatibility)
    overview, financials, market, strategy, icp, competitors, risks
```

### 2. company_decisions Table
```sql
CREATE TABLE company_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER REFERENCES companies(id),
    title TEXT NOT NULL,
    context TEXT,
    options_json JSONB,         -- [{name, description, pros, cons, cost, risk}]
    recommendation_json JSONB,  -- {option, rationale, next_steps}
    status TEXT DEFAULT 'proposed',  -- proposed|approved|rejected|revisited
    owner TEXT,
    tags JSONB,
    confidence TEXT DEFAULT 'medium',  -- high|medium|low
    sources_json JSONB,
    created_from_message_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. company_scenarios Table
```sql
CREATE TABLE company_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER REFERENCES companies(id),
    name TEXT NOT NULL,
    base_scenario_id UUID REFERENCES company_scenarios(id),
    assumptions_json JSONB,     -- {raise_usd, cac_change_pct, ...}
    outputs_json JSONB,         -- {runway, revenue_impact, ...}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### Enhanced Chat
```
POST /companies/{company_id}/chat
{
  "message": string,
  "mode": {
    "challenge": boolean,
    "investor_lens": "none"|"vc"|"growth_pe"|"crossover"|"strategic",
    "confidence_reporting": boolean
  },
  "scenario": {
    "scenario_id": string|null,
    "fork": boolean,
    "assumptions": object|null
  },
  "create_decision": boolean
}
```

### Decisions
- GET `/companies/{company_id}/decisions` - List
- POST `/companies/{company_id}/decisions` - Create
- PATCH `/companies/{company_id}/decisions/{id}` - Update

### Scenarios
- GET `/companies/{company_id}/scenarios` - List
- POST `/companies/{company_id}/scenarios` - Create/Fork

### Memo Export
- POST `/companies/{company_id}/memo` - Generate markdown memo

## Agent Output Contract
Each agent returns:
```json
{
  "agent": "cfo|market|strategy",
  "findings": ["string"],
  "structured": {},
  "assumptions_risks": ["string"],
  "next_questions": ["string"],
  "confidence": "high|medium|low"
}
```

## Implementation Order
1. Database models and migrations
2. Backend API endpoints (decisions, scenarios, enhanced chat)
3. Agent upgrades (challenge mode, investor lens, sales targets)
4. Memo export endpoint
5. UI pages (decisions, scenarios, enhanced copilot)
6. Testing and QA
