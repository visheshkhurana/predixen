# FounderConsole — Full System Audit

**Date:** March 13, 2026
**Auditor:** Senior Software Architect
**Scope:** Complete architecture review — no code changes, analysis only

---

## STEP 1 — PROJECT STRUCTURE

```
.
├── client/                       # Frontend (React + TypeScript + Vite)
│   ├── public/                   #   Static assets & email assets
│   └── src/
│       ├── api/                  #   API client hooks & fetchers
│       ├── components/           #   UI components
│       │   ├── admin/            #     Admin-specific components
│       │   ├── board-export/     #     Board deck PDF generation
│       │   ├── connectors/       #     Connector marketplace UI
│       │   ├── fundraising/      #     Cap table & fundraising UI
│       │   ├── integrations/     #     Integration management
│       │   ├── Layout/           #     App layout (sidebar, header)
│       │   ├── marketing/        #     Public marketing pages
│       │   ├── simulation/       #     Charts, bands, tornado diagrams
│       │   └── ui/               #     Shadcn/Radix base components
│       ├── config/               #   App configuration constants
│       ├── hooks/                #   Custom React hooks (useToast, etc.)
│       ├── lib/                  #   Utilities, query client, helpers
│       │   ├── __tests__/        #     Unit tests
│       │   ├── integrations/     #     Integration helpers
│       │   └── simulation/       #     Simulation utilities
│       ├── pages/                #   Page components (~50 routes)
│       │   └── admin/            #     Admin dashboard pages
│       ├── services/             #   Frontend service layer
│       └── store/                #   Zustand state stores
│
├── server/                       # Backend (FastAPI + Python 3.11)
│   ├── ai-governance/            #   AI safety rules & governance
│   ├── alerts/                   #   Smart alerting system
│   ├── api/                      #   FastAPI route handlers (67 files)
│   ├── connectors/               #   Data connectors (33+ providers)
│   │   └── queue_manager.py      #     Prioritized sync queue
│   ├── copilot/                  #   AI Copilot system
│   │   └── agents/               #     7 specialized AI agents
│   ├── core/                     #   DB, security, config, middleware
│   ├── decision/                 #   Decision engine & pattern matching
│   ├── email/                    #   Email service (Resend integration)
│   ├── forecasting/              #   Time-series forecasting engine
│   ├── ingest/                   #   PDF/Excel data extraction
│   ├── integrations/             #   Third-party integration configs
│   ├── lib/                      #   Shared libraries
│   │   ├── evals/                #     AI evaluation framework
│   │   ├── fundraising/          #     Fundraising calculations
│   │   ├── llm/                  #     Multi-LLM router & clients
│   │   └── privacy/              #     PII redaction
│   ├── metrics/                  #   Metric DSL, templates, suggestions
│   ├── middleware/               #   CSRF, rate limiting, request logging
│   ├── models/                   #   SQLAlchemy ORM models (~20 tables)
│   ├── replit_integrations/      #   Replit-specific AI integrations
│   ├── scripts/                  #   Utility scripts
│   ├── seed/                     #   Database seeding
│   ├── services/                 #   Business logic layer
│   ├── simulate/                 #   Monte Carlo engine
│   ├── sms/                      #   Twilio SMS service
│   ├── templates/                #   Server-side templates
│   ├── tests/                    #   Backend test suite
│   ├── truth/                    #   Truth Scan validation logic
│   ├── utils/                    #   Backend utilities
│   ├── whatsapp/                 #   WhatsApp integration
│   └── workers/                  #   Background job workers
│
├── shared/                       # Shared TypeScript schemas
│   └── models/                   #   Drizzle/Zod schema definitions
│
├── docs/                         # Architecture & product docs
├── qa-lab/                       # QA datasets & test scenarios
├── script/                       # Production build scripts
├── scripts/                      # Launch gate & utility scripts
│
├── main.py                       # Python entry point
├── package.json                  # Node.js dependencies
├── pyproject.toml                # Python dependencies
├── vite.config.ts                # Frontend build config
├── drizzle.config.ts             # DB migration config
└── tailwind.config.ts            # CSS framework config
```

**Entry Points:**
- **Frontend:** `client/src/main.tsx` → React app mounted to DOM, routes defined in `client/src/App.tsx`
- **Backend:** `main.py` → launches FastAPI app defined in `server/main.py`
- **Dev Server:** `npm run dev` → starts both Vite dev server and FastAPI backend concurrently

---

## STEP 2 — SYSTEM ARCHITECTURE

### Layer Diagram

```
┌─────────────────────────────────────────────────┐
│                 FRONTEND LAYER                   │
│  React 18 + TypeScript + Vite + Wouter          │
│  Zustand (state) + TanStack Query (data)        │
│  Shadcn/ui + Tailwind CSS + Recharts            │
└──────────────────────┬──────────────────────────┘
                       │ HTTP/JSON (cookie auth)
┌──────────────────────▼──────────────────────────┐
│                   API LAYER                      │
│  FastAPI (67 route files, ~456 endpoints)        │
│  Middleware: CSRF, Rate Limiting, Request Log    │
│  Auth: JWT cookies + RBAC + Company Access       │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                SERVICE LAYER                     │
│  Digital Twin     │  Intelligence Graph          │
│  Truth Scan       │  Simulation Copilot          │
│  KPI Calculations │  Notifications               │
│  Decision Engine  │  Forecasting Engine           │
│  AI Copilot (7 agents) │  Connector Queue         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  DATA LAYER                      │
│  PostgreSQL (SQLAlchemy ORM + Alembic)           │
│  ~20 tables, company_id-based multi-tenancy      │
│  JSON/JSONB columns for flexible schemas         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│             INFRASTRUCTURE LAYER                 │
│  Simulation Worker (threaded, polling)           │
│  Background Tasks (FastAPI built-in)             │
│  Resend (email) │ Twilio (SMS)                   │
│  Multi-LLM: OpenAI, Anthropic, Gemini,          │
│              Perplexity, OpenRouter/Grok         │
└─────────────────────────────────────────────────┘
```

### Key Implementation Files Per Layer

| Layer | Key Files |
|-------|-----------|
| Frontend | `client/src/App.tsx`, `client/src/pages/*`, `client/src/components/*` |
| API | `server/api/*.py` (67 files), `server/middleware/*.py` |
| Service | `server/services/*.py`, `server/copilot/agents/*.py`, `server/simulate/*.py` |
| Data | `server/models/*.py`, `server/core/db.py`, Alembic migrations |
| Infrastructure | `server/workers/*.py`, `server/lib/llm/*.py`, `server/email/*.py` |

---

## STEP 3 — FRONTEND UI STRUCTURE

### All Routes (50+ pages)

#### Core Application Routes
| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `PublicOrAuthHome` | Landing page (unauthenticated) or Dashboard (authenticated) |
| `/overview` | `OverviewPage` | Main financial dashboard |
| `/kpi-board` | `KPIBoardPage` | Stakeholder-facing KPI display |
| `/truth-scan` | `TruthScanPage` | Data validation & integrity checking |
| `/data` | `DataInputPage` | Upload CSV/Excel, manual entry |
| `/data/verify/:sessionId` | `DataVerificationPage` | Review imported data session |
| `/scenarios` | `ScenariosPage` | Financial scenario management |
| `/scenarios/:id` | `ScenariosPage` | Individual scenario detail |
| `/decisions` | `DecisionsPage` | AI-powered decision recommendations |
| `/copilot` | `CopilotPage` | AI Copilot chat interface |
| `/integrations` | `IntegrationsPage` | Connected data sources |
| `/marketplace` | `ConnectorMarketplacePage` | Browse available connectors |
| `/add-data-source` | `AddDataSourcePage` | Guided connector setup |
| `/alerts` | `AlertsPage` | Smart alerts & monitoring |
| `/templates` | `TemplatesPage` | Scenario templates |
| `/docs` | `DocsPage` | Help & documentation |
| `/cap-table` | `CapTablePage` | Equity & cap table management |
| `/fundraising` | `FundraisingPage` | Fundraising round planning |
| `/investor-room` | `InvestorRoomPage` | Investor-facing data room |
| `/dashboards` | `DashboardsPage` | Custom dashboard builder list |
| `/dashboard/:id` | `DashboardBuilderPage` | Custom dashboard editor |
| `/metrics` | `MetricCatalogPage` | Metric definitions & catalog |
| `/suggested-metrics` | `SuggestedMetricsPage` | AI-suggested metrics |
| `/journal` | `JournalPage` | Decision journal |
| `/goals` | `GoalsPage` | OKR/goal tracking |
| `/hiring-planner` | `HiringPlannerPage` | Headcount planning & runway impact |
| `/doc-generator` | `DocGeneratorPage` | AI document generation |
| `/ai-graphics` | `AIGraphicsPage` | AI image generation studio |
| `/digital-twin` | `DigitalTwinPage` | Company digital twin dashboard |
| `/intelligence` | `IntelligenceGraphPage` | Cross-company intelligence network |
| `/onboarding` | `OnboardingPage` | New user/company setup flow |

#### Public/Marketing Routes
| Route | Component | Purpose |
|-------|-----------|---------|
| `/auth` | `AuthPage` | Login/Register |
| `/auth/callback` | `AuthCallback` | OAuth callback handler |
| `/pricing` | `PricingPage` | Pricing tiers |
| `/features` | `MarketingFeaturesPage` | Feature showcase (lazy) |
| `/about` | `AboutPage` | Company info (lazy) |
| `/contact` | `ContactPage` | Contact form (lazy) |
| `/blog` | `BlogPage` | Blog listing (lazy) |
| `/faq` | `FAQPage` | FAQ page (lazy) |
| `/demo` | `DemoPage` | Product demo (lazy) |

#### Admin Routes
| Route | Component | Purpose |
|-------|-----------|---------|
| `/admin` | `AdminDashboard` | Admin overview |
| `/admin/users` | `AdminUsers` | User management |
| `/admin/companies` | `AdminCompanies` | Company management |
| `/admin/billing` | `AdminBilling` | Subscription management |
| `/admin/metrics` | `AdminMetrics` | System metrics |
| `/admin/login-history` | `AdminLoginHistory` | Security audit log |
| `/admin/activity` | `AdminActivity` | Activity feed |
| `/admin/invites` | `AdminInvites` | Invitation management |
| `/admin/email-templates` | `AdminEmailTemplates` | Email template editor |
| `/admin/email-tracking` | `AdminEmailTracking` | Email delivery stats |
| `/admin/llm-audit` | `AdminLLMAudit` | LLM usage & cost audit |
| `/admin/evals` | `AdminEvals` | AI evaluation runs |
| `/admin/ai-governance` | `AiGovernancePage` | AI safety policies |
| `/admin/team` | `AdminTeam` | Internal team management |
| `/admin/messaging` | `MessagingPage` | SMS/WhatsApp messaging |
| `/qa` | `QAFrontPage` | QA test runner |

### Sidebar Navigation Structure

```
┌─────────────────────────────┐
│  FounderConsole              │
│  [Company Switcher]          │
│                              │
│  ★ AI Copilot (gradient CTA) │
│                              │
│  ── CORE ──                  │
│  Dashboard                   │
│  Simulate         [3]        │
│  Doc Generator     NEW       │
│  Decisions         [2]       │
│  Digital Twin      NEW       │
│  Intelligence      NEW       │
│  Alerts            [5]       │
│                              │
│  ── FINANCE ──               │
│  Cap Table                   │
│  Fundraising                 │
│  Health Check                │
│                              │
│  ── TRACK ──                 │
│  Decision Journal  NEW       │
│  Goals                       │
│  Hiring Planner              │
│                              │
│  ── Settings & Tools ──      │
│  (Drawer: Data, Metrics,     │
│   Stakeholders, Admin)       │
└─────────────────────────────┘
```

### UI Flow

```
Auth → Onboarding → Dashboard
                       ├── Simulate → Run Monte Carlo → Compare Scenarios
                       ├── Decisions → AI Recommendations → Decision Journal
                       ├── Copilot → Multi-Agent Chat → Action Items
                       ├── Data Input → Truth Scan → Verified Metrics
                       ├── Cap Table → Fundraising → Investor Room
                       ├── Digital Twin → Live State + Events + Simulations
                       ├── Intelligence → Peer Network + Benchmarks + AI Insights
                       ├── Alerts → Threshold Monitoring → Email/SMS Notifications
                       └── Settings → Integrations → Connector Marketplace
```

---

## STEP 4 — CORE SERVICES

### Service Inventory

| Service | File | Responsibility |
|---------|------|----------------|
| **Digital Twin** | `server/services/digital_twin.py` | Assembles unified company state from financials, metrics, events, and decisions. Computes risk indicators (runway < 6 months, burn spikes > 20%), health score (0-100), and bridges to Monte Carlo simulation. Emits state-change events to Intelligence Graph. |
| **Intelligence Graph** | `server/services/intelligence_graph.py` | Cross-company intelligence via PostgreSQL. Finds similar companies using weighted scoring (industry, stage, MRR, growth), analyzes decision patterns across platform, generates AI-driven strategy insights, processes real-time events from Digital Twin pipeline. |
| **Truth Scan** | `server/services/truth_scan.py` | Multi-stage data validation pipeline. Infers currency/time/scale assumptions, normalizes raw data into canonical "Facts" JSON, runs arithmetic/accounting rule validation, auto-repairs minor issues, computes derived metrics (net burn, runway). |
| **Simulation Copilot** | `server/services/simulation_copilot.py` | Context-aware AI guidance for simulations. Analyzes slider changes, explains primary/secondary effects, generates plain-English narratives from Monte Carlo results, ranks key financial drivers. |
| **KPI Calculations** | `server/services/kpi_calculations.py` | Single source of truth for financial formulas using Decimal precision. ARPA, ARR, gross margin, burn, runway, LTV/CAC ratio, payback period. Includes fixture-based validation against Excel ground truth. |
| **Notifications** | `server/services/notifications.py` | Email delivery via Resend. Feature notifications, AI copilot announcements, styled HTML templates. |
| **Monte Carlo Engine** | `server/simulate/simulation_engine.py` | 500-1000 iteration Monte Carlo simulations with stochastic growth/margin/cost shocks. P10/P50/P90 bands for revenue/cash/burn over 24-month horizons. |
| **Enhanced Monte Carlo** | `server/simulate/enhanced_monte_carlo.py` | Advanced engine with ScenarioEvent support (funding rounds, market shocks, hiring plans), varied probability distributions (normal, lognormal, triangular, discrete). |
| **Decision Engine** | `server/decision/decision_engine.py` | Pattern-based decision ranking. Matches current company risks against decision library, ranks by predicted survival probability impact. |
| **Forecasting Engine** | `server/forecasting/engine.py` | Time-series predictions using Holt-Winters exponential smoothing and linear regression. Z-score anomaly detection. Provides baseline projections for simulation scenarios. |
| **AI Copilot** | `server/copilot/agents/*.py` | 7-agent multi-LLM system: Router (orchestrator), CFO, Strategy, Decision Advisor, Market, Operations, Review. Router dispatches to specialists, merges outputs, synthesizes executive summaries. |
| **Multi-LLM Router** | `server/lib/llm/llm_router.py` | Intelligent model selection per task type. GPT-4o (financial analysis), Claude Sonnet (strategy), Gemini Flash (general chat), Perplexity (web search), Grok (news). Includes fallback chains and audit logging. |
| **Sensitivity Analysis** | `server/simulate/sensitivity.py` | One-at-a-time parameter perturbation to identify most influential financial drivers. Generates tornado chart data. |
| **Connector Queue** | `server/connectors/queue_manager.py` | Priority-based sync scheduling with provider-specific rate limits. SyncJob lifecycle (PENDING → RUNNING → COMPLETED/FAILED), exponential backoff retries. |

---

## STEP 5 — DATA MODEL

### Database Tables

#### Core Business Tables

| Table | Key Columns | Foreign Keys | Purpose |
|-------|-------------|--------------|---------|
| `users` | id, email, password_hash, role, oauth_provider, is_platform_admin | — | User accounts |
| `companies` | id, user_id, name, industry, stage, currency | users.id | Company (tenant) records |
| `financial_records` | id, company_id, period_start/end, revenue, cogs, opex, payroll, cash_balance, mrr, arr, net_burn, runway_months, headcount, customers, mom_growth, ltv, cac, ndr | companies.id | Monthly financial snapshots |
| `company_states` | id, company_id (unique), state_json, snapshot_id, cash_balance, monthly_burn, revenue_monthly | — | Current company state (Digital Twin) |
| `company_decisions` | id (UUID), company_id, title, context, options_json, recommendation_json, status, confidence | companies.id | Strategic decisions |
| `scenarios` | id, company_id, name, inputs_json, overrides_json, outputs_json, version, parent_id | companies.id, scenarios.id (self-ref) | Simulation scenarios |
| `simulation_runs` | id, scenario_id, n_sims, outputs_json, data_snapshot_id, status | scenarios.id | Monte Carlo run results |
| `decisions` | id, simulation_run_id, recommended_actions_json | simulation_runs.id | Simulation-linked decisions |

#### Data Management Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `datasets` | id, company_id, type, file_name, row_count | Uploaded data files |
| `import_sessions` | id, company_id, source_type, filename, status, raw_data | CSV/Excel import tracking |
| `truth_scan_uploads` | id (UUID), company_id, source_kind, status, file_hash | Truth Scan audit trail |
| `truth_datasets` | id (UUID), company_id, version, facts, assumptions, derived, coverage | Validated canonical data |
| `raw_data_events` | id, company_id, connector_id, source, payload | Connector sync events |
| `metric_definitions` | id, company_id, key, name, formula, grain, status | Custom metric catalog |

#### Event & Intelligence Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `twin_events` | id, company_id, event_type, source, payload, created_at | Digital Twin event ledger |

#### User & Access Tables

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `workspace_members` | user_id, company_id, role | Multi-user company access |
| `audit_log` | user_id, action, target_id, metadata | Security audit trail |
| `rate_limits` | identifier, category, count, window_start | Rate limiting state |

### Entity Relationship Diagram

```
users ──1:N──> companies ──1:N──> financial_records
                  │                     │
                  ├──1:N──> scenarios ──1:N──> simulation_runs ──1:N──> decisions
                  │
                  ├──1:1──> company_states
                  │
                  ├──1:N──> twin_events
                  │
                  ├──1:N──> company_decisions
                  │
                  ├──1:N──> datasets
                  │
                  ├──1:N──> import_sessions ──1:N──> financial_records
                  │
                  ├──1:N──> truth_scan_uploads ──1:N──> truth_datasets
                  │
                  ├──1:N──> raw_data_events
                  │
                  ├──1:N──> metric_definitions
                  │
                  └──N:M──> users (via workspace_members)
```

### Multi-Tenancy Implementation

- **Shared database, logical isolation**: Every data table contains a `company_id` foreign key
- **Access enforcement**: FastAPI dependency `get_user_company(db, company_id, user)` on every route validates the user can access the requested company
- **Access paths**: Owner (`company.user_id == user.id`), Workspace member (`workspace_members`), or Platform admin (`is_platform_admin=True`)
- **Cascading deletion**: Company deletion removes records across 20+ tables to prevent orphaned data

---

## STEP 6 — DIGITAL TWIN / STATE MODEL

### Current Architecture

**Yes, the system has a comprehensive Digital Twin implementation.**

#### Company State Model (`company_states` table)
- **Schema**: `state_json` (full JSON blob) + denormalized top-level fields (`cash_balance`, `monthly_burn`, `revenue_monthly`, `revenue_growth_rate`, `expenses_monthly`)
- **Uniqueness**: One state per company (`company_id` is unique)
- **Snapshot tracking**: `snapshot_id` hash for version control
- **Update mechanism**: Updated by Truth Scan finalization, connector syncs, and manual input

#### Digital Twin Assembly (`server/services/digital_twin.py`)
The twin state is computed dynamically, not stored as a single record:

```
get_twin_state(db, company_id) assembles:
├── CompanyState (latest snapshot)
├── Financial History (12-month records with MoM trends)
├── Derived Metrics (LTV, CAC, Churn, ARPU)
├── Risk Indicators (runway < 6mo, burn spikes, revenue decline)
├── Twin Health Score (0-100, based on data freshness + completeness)
├── Active Scenarios (count & latest simulation results)
├── Recent Decisions (with outcomes)
└── Recent Events (twin_events, last 20)
```

#### Event Ledger (`twin_events` table)
- **12 event types**: `state_update`, `revenue_update`, `expense_update`, `simulation_run`, `decision_made`, `decision_outcome`, `alert_triggered`, `connector_sync`, `truth_scan_complete`, `fundraising_update`, `headcount_change`, `data_ingestion`
- **Pipeline**: `emit_twin_event()` → auto-triggers `process_graph_event()` in Intelligence Graph (fail-safe, wrapped in try/except)
- **Source tracking**: Every event records its origin (`seed`, `copilot`, `user`, `system`, connector name)

#### Metric Aggregation
- **Primary**: `financial_records` table stores monthly snapshots with 25+ financial fields
- **Derived**: `company_states.state_json` stores latest aggregated metrics
- **Real-time**: `get_twin_state()` computes risk indicators and health on-the-fly
- **Historical**: 12-month lookback from `financial_records` for trend analysis

---

## STEP 7 — SIMULATION ENGINE

### Architecture Overview

```
User Adjusts Sliders (Frontend)
        │
        ▼
Scenario Creation/Update (API)
        │
        ▼
┌──────────────────────────────┐
│      Monte Carlo Engine       │
│  500-1000 iterations          │
│  24-month projection horizon  │
│                               │
│  Per iteration:               │
│  ├── Apply growth rate ± σ    │
│  ├── Apply margin noise       │
│  ├── Apply cost volatility    │
│  ├── Process scenario events  │
│  │   (funding, hiring, etc.)  │
│  ├── Compute monthly cash     │
│  └── Detect runway exhaustion │
│                               │
│  Output: P10/P50/P90 bands    │
└──────────┬───────────────────┘
           │
           ▼
Results stored in simulation_runs.outputs_json
           │
           ▼
Frontend renders: Band Charts, Survival Curves, Tornado Diagrams
```

### Where Simulations Run
- **Synchronous**: Directly in the FastAPI request cycle (default for most scenarios)
- **Asynchronous**: Via `simulation_worker.py` — a dedicated polling worker using `ThreadPoolExecutor` (max 3 concurrent), claiming jobs with `FOR UPDATE SKIP LOCKED`
- **Job recovery**: Stale jobs auto-marked as FAILED after 30-minute timeout

### Scenario Definition
Scenarios contain `inputs_json` with:
- `pricing_change_pct`, `growth_uplift_pct`, `burn_reduction_pct`
- `hiring_plan` (list of roles with costs/timing)
- `fundraise_amount` and `fundraise_month`
- Default templates: `baseline`, `conservative`, `moderate_growth`, `aggressive_growth`, `cost_cutting`
- Version control via `ScenarioVersion` system with diffing

### Results Storage
`simulation_runs.outputs_json` contains:
- Time-series bands (P10/P50/P90) for Revenue, Cash, Burn
- Survival probability at 6/12/18/24 months
- Median runway, final cash, average burn
- `data_snapshot_id` for reproducibility

### Frontend Display Components
- `BandsChart.tsx` / `ProjectionChart.tsx` — uncertainty corridors
- `SurvivalCurveChart.tsx` — probability of survival over time
- `TornadoChart.tsx` — sensitivity analysis visualization
- `ScenarioComparisonTable.tsx` — side-by-side comparison

### Advanced Features
- **Counter-Moves**: Pre-defined strategic adjustments automatically simulated against any scenario
- **Sensitivity Analysis**: OAT perturbation method identifying most influential drivers
- **Macro Modifiers**: Global inflation, interest rate, and market growth factors
- **Enhanced Engine**: ScenarioEvent support with varied probability distributions

---

## STEP 8 — AI SYSTEM

### Multi-Agent Copilot Architecture

```
User Query
    │
    ▼
┌───────────────────────────────────────────┐
│           ROUTER AGENT                     │
│  (Gemini Flash for intent classification)  │
│                                           │
│  Determines which specialists to invoke    │
│  Keyword heuristics + LLM classification   │
└───┬───┬───┬───┬───┬───┬───────────────────┘
    │   │   │   │   │   │
    ▼   ▼   ▼   ▼   ▼   ▼
┌─────┐ ┌───┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│ CFO │ │MKT│ │STRATEGY│ │DECIS.│ │  OPS   │ │  REVIEW  │
│Agent│ │Agt│ │ Agent  │ │ADVSR │ │ Agent  │ │  Agent   │
└──┬──┘ └─┬─┘ └───┬────┘ └──┬───┘ └───┬────┘ └────┬─────┘
   │      │       │         │         │           │
   └──────┴───────┴────┬────┴─────────┴───────────┘
                       │
                       ▼
              Synthesis (Gemini Flash)
              → Unified Executive Summary
```

### Agent Details

| Agent | Model | Specialization |
|-------|-------|----------------|
| **Router** | Gemini Flash | Intent classification, dispatch, synthesis |
| **CFO** | GPT-4o | Financial extraction, metric computation, Truth Scan grounding |
| **Market** | Perplexity Sonar | Market research, competitor analysis, real-time web data |
| **Strategy** | Claude Sonnet | Growth planning, market entry, strategic advisory |
| **Decision Advisor** | Claude/GPT-4o | Decision-to-lever mapping, Monte Carlo-backed recommendations |
| **Operations** | Claude | Implementation roadmaps, task execution planning |
| **Review** | GPT-4o | Output validation, hallucination detection, math checking |

### Multi-LLM Router (`server/lib/llm/llm_router.py`)

| Task Type | Primary Model | Fallback |
|-----------|--------------|----------|
| `FINANCIAL_ANALYSIS` | GPT-4o | Claude → Gemini |
| `METRICS_EXTRACTION` | GPT-4o | Claude → Gemini |
| `STRATEGY` | Claude Sonnet | GPT-4o → Gemini |
| `COMPLEX_REASONING` | Claude Opus | GPT-4o → Gemini |
| `GENERAL_CHAT` | Gemini Flash | GPT-4o |
| `WEB_SEARCH` | Perplexity Sonar | — |
| `MARKET_RESEARCH` | Perplexity Sonar | — |
| `NEWS_CURRENT_EVENTS` | Grok 4.1 | Perplexity |

### Company Knowledge Base (CKB)
Structured persistent memory per company:
- **Facts**: Verified data from Truth Scans, APIs, document extraction
- **Beliefs**: AI-generated inferences with confidence levels
- **Decisions**: Decision log with simulation outcomes
- **Outcomes**: Tracked results for closed-loop learning

### Supporting AI Components
- **Simulation Copilot**: Context-aware guidance during scenario editing
- **AI Graphics Studio**: OpenAI gpt-image-1 for professional financial graphics
- **Document Generator**: AI-powered financial models, investor memos, KPI reports
- **Prompt Injection Defense**: `server/copilot/prompt_injection_defense.py`
- **Trust Module**: `server/copilot/trust.py` — grounding rules for data accuracy
- **AI Governance**: `server/ai-governance/` — safety rules and output policies

---

## STEP 9 — EVENT / JOB SYSTEM

### Background Processing Architecture

```
┌─────────────────────────────────────┐
│         SIMULATION WORKER            │
│  (Dedicated polling process)         │
│                                     │
│  Poll DB every 2s for PENDING jobs   │
│  ThreadPoolExecutor (max 3)          │
│  FOR UPDATE SKIP LOCKED claiming     │
│  30-min timeout → auto-FAILED        │
│  Results → WebSocket broadcast       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│     FASTAPI BACKGROUND TASKS         │
│  (In-process, after response sent)   │
│                                     │
│  • Metrics recomputation             │
│  • Connector data sync               │
│  • Assumption-triggered simulations  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        STARTUP TASKS                 │
│  (server/main.py lifespan)           │
│                                     │
│  • Schema creation                   │
│  • Alembic migrations                │
│  • Intelligence Graph indexes        │
│  • Demo data seeding                 │
│  • Benchmark data seeding            │
│  • Rate limiter cleanup (5-min loop) │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│      CONNECTOR QUEUE MANAGER         │
│  (In-process scheduling)             │
│                                     │
│  Priority-based: CRITICAL → LOW      │
│  Provider rate limits:               │
│    Stripe: 25 RPM                    │
│    QuickBooks: 10 RPM                │
│  Exponential backoff retries         │
│  24h job retention with cleanup      │
└─────────────────────────────────────┘
```

### Job States
- Simulation: `PENDING → RUNNING → COMPLETED/FAILED`
- Connector sync: `PENDING → RUNNING → COMPLETED/FAILED/RETRYING/RATE_LIMITED`

### No External Job Queue
- No Celery, Redis, or RabbitMQ
- No cron jobs registered in application
- All async work is either in-process (FastAPI BackgroundTasks) or via the polling simulation worker

---

## STEP 10 — INTEGRATIONS

### Data Connector Catalog (33+ Providers)

| Category | Connectors |
|----------|------------|
| **Accounting/ERP** | QuickBooks, Xero, Zoho Books, Tally, FreshBooks, Wave, Bench |
| **Billing/Revenue** | Stripe, Chargebee, Recurly, ProfitWell |
| **Payroll/HRIS** | Gusto, Rippling, Deel, RazorpayX, Keka, greytHR |
| **CRM/Sales** | HubSpot, Salesforce, Pipedrive, Close CRM |
| **Analytics** | Google Analytics, Mixpanel, Amplitude |
| **Banking** | Plaid, Mercury, Brex, Ramp |
| **Commerce** | Shopify |
| **Data Sources** | MySQL, Google Sheets, REST API |

### Connector Architecture
```
BaseConnector (abstract)
├── authenticate()        # Validate credentials
├── test_connection()     # Health check
├── fetch_employees()     # Payroll data
├── fetch_payroll_runs()  # Pay periods
├── fetch_ledger()        # GL entries
├── fetch_invoices()      # AR data
└── map_to_financials()   # Normalize to standard schema
         │
         ▼
    FinancialRecord (database)
```

### Sync Flow
1. **Authenticate**: Validate credentials, store encrypted in `company.metadata_json`
2. **Execute**: Instantiate connector, call `sync_all()`
3. **Validate**: Run financial metric validation
4. **Persist**: Convert to `FinancialRecord`, save to database
5. **Event**: Emit `connector_sync` twin event

### Other Integrations
- **Resend**: Email delivery (feature announcements, alerts, password resets)
- **Twilio**: SMS/WhatsApp notifications (2FA, alerts, weekly briefings)
- **Slack Bot**: 5 slash commands for copilot access
- **Google OAuth**: Social login via `/auth/google/login` callback flow
- **PostHog**: Frontend analytics (page views, user identification, custom events)

---

## STEP 11 — SECURITY

### Authentication
- **Mechanism**: JWT tokens stored in HTTP-only cookies
- **Token Types**: Access token (`auth_token` cookie) + Refresh token (path-restricted to `/api/auth`)
- **Algorithm**: HS256 with server-side secret
- **Revocation**: In-memory JTI-based revocation list
- **OAuth**: Google OAuth2 with callback handling
- **Master User**: Special ID=-1 for platform-level operations (audited)

### Authorization (RBAC)
- **User Roles**: `OWNER`, `ADMIN`, `ANALYST`, `VIEWER`
- **Company Access**: Checked via `get_user_company()` on every endpoint
  - Owner: `company.user_id == user.id`
  - Workspace member: `WorkspaceMember` model with per-company roles
  - Platform admin: `is_platform_admin=True` bypasses ownership checks
- **Admin Routes**: Separate route group requiring `is_platform_admin` check
- **Audit Logging**: All admin/master user access logged to `AuditLog` table

### CSRF Protection
- **Pattern**: Double-submit cookie
- **Flow**: Safe requests (GET/HEAD) set CSRF cookie → State-changing requests require `X-CSRF-Token` header matching cookie
- **Validation**: 64 hex character format check
- **Exemptions**: `/health`, `/auth/login`, `/auth/register`

### Rate Limiting
- **Storage**: PostgreSQL-backed fixed-window algorithm
- **Categories**:
  - Auth: 5 req/min
  - Admin auth: 3 req/min
  - Simulations: 10 req/min
  - API general: 60 req/min
  - Uploads: 10 req/min
- **Concurrency**: Atomic `INSERT ... ON CONFLICT DO UPDATE`
- **Cleanup**: Background task every 5 minutes

### Data Isolation
- Every data table has `company_id` foreign key
- Access validated on every route via dependency injection
- Cascading deletion across 20+ tables on company removal
- PII redaction module in `server/lib/privacy/`

---

## STEP 12 — CURRENT PRODUCT CAPABILITIES

### Feature Matrix

| Category | Features |
|----------|----------|
| **Financial Dashboard** | Real-time KPIs, 12-month trends, MoM/YoY growth, cash runway, burn rate, gross margin |
| **Data Ingestion** | CSV upload, Excel/PDF AI extraction, manual entry, 33+ automated connectors, multi-currency support |
| **Data Validation** | Multi-stage Truth Scan (assumption inference, rule validation, auto-repair, canonical normalization) |
| **Simulation Engine** | Monte Carlo (P10/P50/P90), 24-month projections, scenario versioning, counter-moves, sensitivity analysis, macro modifiers, tornado charts |
| **AI Copilot** | 7-agent system (CFO, Market, Strategy, Decision Advisor, Operations, Review), multi-LLM routing, CKB memory, prompt injection defense |
| **Decision System** | AI-powered recommendations, decision journal, pattern engine, outcome tracking, confidence scoring |
| **Cap Table** | Shareholder registry, equity issuance, option grants, convertible notes, waterfall analysis, dilution modeling, 409A summary |
| **Fundraising** | Round planning, dilution simulation, readiness scoring, AI investment one-pager, investor benchmarks |
| **Investor Room** | Diligence reports, financial memo generation, benchmark comparisons |
| **Digital Twin** | Live company state, event ledger (12 types), risk indicators, health scoring, embedded Monte Carlo explorer |
| **Intelligence Graph** | Cross-company peer matching, decision pattern analysis, AI strategy insights, network visualization, industry benchmarks |
| **Alerts & Monitoring** | Smart alerts (burn spike, MRR drop, churn), custom rules, severity filtering, email/SMS delivery, weekly briefings |
| **Forecasting** | Holt-Winters, linear regression, Z-score anomaly detection, threshold monitoring |
| **Document Generation** | AI financial models, investor memos, KPI reports, pitch deck outlines |
| **AI Graphics** | Professional financial imagery via gpt-image-1, multiple styles and aspect ratios |
| **Board Export** | AI-powered presentations (Monthly Update, Fundraising Prep, Scenario Analysis) with PDF download |
| **Hiring Planner** | Role/department/location planning, salary modeling, runway impact analysis |
| **KPI Board** | Stakeholder-facing metric display, custom dashboards, widget builder |
| **Metrics Catalog** | Metric DSL, AI-suggested metrics, industry templates, formula validation |
| **Goals & OKRs** | Goal tracking, progress monitoring |
| **Workspace** | Multi-user company access, role-based permissions, invitation system |
| **Admin Platform** | User management, company overview, billing, LLM audit, AI evaluations, governance, email templates, login history |
| **Notifications** | Email (Resend), SMS/WhatsApp (Twilio), Slack bot integration |
| **Marketing Site** | Landing page, pricing, features, about, blog, FAQ, contact, demo |

---

## STEP 13 — ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                       │
│  React 18 + TypeScript + Vite + Wouter + Zustand + TanStack Query           │
│  Shadcn/ui + Tailwind CSS + Recharts + Lucide Icons                         │
│  50+ pages, dark mode default                                               │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTP/JSON (cookie-based JWT auth)
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                            API GATEWAY                                      │
│  FastAPI (Python 3.11) — 67 route files, ~456 endpoints                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │     CSRF     │  │ Rate Limiter │  │   JWT Auth   │                      │
│  │  Middleware   │  │ (PostgreSQL) │  │ + RBAC Guard │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                         │                           │
        ▼                         ▼                           ▼
┌───────────────┐  ┌──────────────────────────┐  ┌────────────────────────┐
│  SIMULATION   │  │      AI COPILOT          │  │    DATA SERVICES       │
│   LAYER       │  │                          │  │                        │
│ Monte Carlo   │  │ Router → [CFO, MKT,      │  │ Truth Scan Pipeline    │
│ Enhanced MC   │  │  Strategy, Decision,     │  │ Connector Framework    │
│ Sensitivity   │  │  Ops, Review] → Synth    │  │ Forecasting Engine     │
│ Counter-moves │  │                          │  │ KPI Calculations       │
│ Sim Worker    │  │ Multi-LLM Router:        │  │ Metrics DSL            │
│               │  │ GPT-4o, Claude, Gemini,  │  │ Ingest (PDF/Excel)     │
│               │  │ Perplexity, Grok         │  │                        │
└───────┬───────┘  └────────────┬─────────────┘  └────────────┬───────────┘
        │                       │                              │
        └───────────────────────┼──────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│                          CORE SERVICES                                    │
│  Digital Twin (state assembly, risk, health) ◄──► Intelligence Graph      │
│  Decision Engine (pattern matching, ranking)      (peer matching,         │
│  Notification Service (email, SMS)                 benchmarks, AI)        │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│                          DATA LAYER                                       │
│  PostgreSQL (SQLAlchemy ORM + Alembic migrations)                         │
│  ~20 tables, company_id multi-tenancy                                     │
│  JSON/JSONB flexible schemas                                              │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                  │
│  OpenAI │ Anthropic │ Gemini │ Perplexity │ Grok/OpenRouter               │
│  Resend (email) │ Twilio (SMS/WhatsApp) │ Google OAuth                    │
│  Stripe │ QuickBooks │ HubSpot │ Plaid │ + 29 more connectors             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 14 — UX ANALYSIS

### Navigation Clarity
**Score: 7/10**
- **Strengths**: Clear 3-section sidebar grouping (Core, Finance, Track) with badge counts for actionable items. AI Copilot given prominent CTA position. Settings/Tools drawer hides less-used features cleanly.
- **Weaknesses**: 50+ pages creates deep navigation. Some features are discoverable only through the drawer (Data Input, Integrations, Metric Catalog). Multiple entry points for similar concepts (e.g., `/scenarios` vs `/scenarios/:id`, multiple simulation endpoints). "Health Check" is a non-obvious alias for Truth Scan.

### Onboarding Flow
**Score: 6/10**
- **Strengths**: Dedicated `/onboarding` route with step-by-step flow. Sample data seeding available via API (`seed-sample`).
- **Weaknesses**: No clear indication of minimum data requirements before simulation features become useful. New users face empty states across many modules simultaneously. No guided tour or progressive disclosure.

### Dashboard Readability
**Score: 8/10**
- **Strengths**: KPI cards with clear financial metrics (Cash, Burn, Revenue, Runway). Dark mode default is appropriate for financial data. Recharts visualizations with proper labeling.
- **Weaknesses**: Dense information on Digital Twin page (financial grid + tabs + health + status). Custom dashboard builder adds flexibility but requires user effort.

### Simulation Usability
**Score: 8/10**
- **Strengths**: Pre-defined scenario templates (baseline, conservative, aggressive). Visual P10/P50/P90 bands. Tornado charts for sensitivity. Counter-moves feature for quick "what-if" exploration.
- **Weaknesses**: Monte Carlo complexity may overwhelm non-technical founders. Slider interactions lack immediate feedback before running full simulation. Scenario versioning adds power but also cognitive load.

### Overall UX Assessment
- **Target Audience Fit**: Good for data-savvy startup founders; may overwhelm first-time entrepreneurs
- **Feature Density**: Very high — 30+ modules could benefit from progressive disclosure
- **Mobile Responsiveness**: Responsive Tailwind layout, but data-heavy pages are desktop-optimized
- **AI Integration**: AI Copilot is well-positioned as primary entry point; agents provide clear value

---

## STEP 15 — IDENTIFIED PROBLEMS

### Architecture Issues

1. **No message queue / task broker**: All async work runs in-process or via a polling worker. No Redis, Celery, or proper job queue. The simulation worker uses database polling with `FOR UPDATE SKIP LOCKED`, which works but doesn't scale well beyond a single worker instance.

2. **In-memory token revocation**: `_revoked_tokens` in `security.py` is a Python set — not shared across processes/replicas. Token revocation won't work in multi-instance deployments.

3. **JSON column overuse**: Extensive use of `state_json`, `inputs_json`, `outputs_json`, `options_json`, `recommendation_json` as catch-all storage. While flexible, this prevents database-level querying, indexing, and referential integrity for data inside these blobs.

4. **Intelligence Graph uses PostgreSQL, not a graph database**: Cross-company relationship queries are implemented with standard SQL joins and scoring algorithms. This works for the current scale but may limit sophisticated graph traversal queries.

5. **No WebSocket infrastructure**: Real-time updates depend on polling or post-simulation HTTP callbacks. No native WebSocket server for live collaboration or real-time simulation progress.

6. **Monolithic backend**: 67 API route files in a single FastAPI application. While organized into modules, there's no service boundary separation — all services share the same process, database pool, and memory space.

### Missing Layers

7. **No caching layer**: No Redis/Memcached for frequently-accessed data (company state, KPIs, user sessions). Every request hits PostgreSQL directly.

8. **No API versioning**: All endpoints are un-versioned. Breaking changes would affect all clients simultaneously.

9. **No structured logging/observability**: No centralized log aggregation, distributed tracing, or metrics collection (beyond PostHog frontend analytics). The LLM audit log is a good start but limited.

10. **No data export/backup strategy**: While CSV/PDF export exists for users, there's no automated database backup or disaster recovery plan visible in the codebase.

### Scalability Risks

11. **Simulation compute**: Monte Carlo simulations are CPU-intensive and run in-process (or in a single worker). Under load, simulations could starve the API server.

12. **Multi-LLM latency**: Sequential agent execution (Router → Specialists → Review → Synthesis) creates chain latency. A complex query may hit 4-5 LLMs sequentially.

13. **Rate limiter in PostgreSQL**: Using the main database for rate limiting adds load to every request. A dedicated in-memory store would be more appropriate.

14. **Connector sync volume**: 33+ connectors all syncing through the same queue manager. High-volume connectors (Stripe with thousands of transactions) could block lower-priority syncs.

### UX Confusion Points

15. **Feature fragmentation**: Similar capabilities spread across multiple routes — scenarios, simulations, and the simulation copilot overlap in purpose. Users may not know which to use.

16. **Empty state experience**: New users see empty dashboards, zero events, no simulations. The path from "I just signed up" to "I see valuable insights" requires navigating multiple modules.

17. **Admin vs. user boundary**: Admin pages are accessible via sidebar drawer but mixed with user-facing settings. The boundary could be clearer.

### Technical Debt

18. **Hardcoded demo data**: Seed scripts contain hardcoded values (user IDs, company IDs) that can break in different environments. (Partially fixed — peer company seeding now looks up the demo user dynamically.)

19. **Dual ORM situation**: The project has both SQLAlchemy (Python, primary) and Drizzle (TypeScript, shared schemas). The Drizzle schemas may drift from the actual database schema managed by Alembic.

20. **Test coverage**: Limited automated test suite visible in the codebase. The `qa-lab/` folder contains test datasets but not comprehensive unit/integration tests for all 456 endpoints.

21. **Email versioning**: Email scripts are versioned as `send_update_vNN.py` (currently v29) — file proliferation instead of template-driven approach.

---

## STEP 16 — RECOMMENDED IMPROVEMENTS

### Architecture Improvements

| Priority | Improvement | Rationale |
|----------|-------------|-----------|
| **High** | Add Redis for caching + session/token management | Eliminates in-memory revocation limitation, adds caching for company state/KPIs, enables proper rate limiting |
| **High** | Introduce a proper job queue (e.g., Redis + Bull, or Celery) | Simulation workers, connector syncs, and AI agent orchestration need reliable async processing beyond DB polling |
| **Medium** | Add WebSocket support | Real-time simulation progress, live collaboration, instant alert delivery |
| **Medium** | API versioning (`/v1/`, `/v2/`) | Enables non-breaking API evolution as the product matures |
| **Low** | Extract heavy services into microservices | Simulation engine and AI copilot are natural candidates for service extraction when scale demands |

### Service Restructuring

| Priority | Change | Benefit |
|----------|--------|---------|
| **High** | Parallelize AI agent execution | Router can dispatch CFO + Market + Strategy concurrently, cutting copilot latency by 50-70% |
| **Medium** | Consolidate scenario/simulation routes | 3 separate API files handle overlapping simulation concerns — merge into coherent API surface |
| **Medium** | Template-based email system | Replace v1-v29 email scripts with a template engine (Jinja2 + stored templates) |
| **Low** | Graph database for Intelligence Graph | Neo4j or similar for richer relationship queries as company count grows |

### UI Improvements

| Priority | Change | Benefit |
|----------|--------|---------|
| **High** | Guided onboarding wizard | Step-by-step: Upload data → Truth Scan → First simulation → See insights |
| **High** | Progressive disclosure | Hide advanced features (sensitivity, counter-moves, Intelligence Graph) until user completes basic flow |
| **Medium** | Unified simulation experience | Merge scenarios page, simulation copilot, and advanced simulation into one cohesive workspace |
| **Medium** | Context-aware empty states | Each empty module should explain what it does AND link to the prerequisite step |
| **Low** | Mobile-optimized views | Simplified KPI cards and charts for mobile founders |

### Missing Components

| Priority | Component | Purpose |
|----------|-----------|---------|
| **High** | Structured logging & monitoring | Centralized logs, error tracking (Sentry), performance monitoring |
| **High** | Automated database backups | Scheduled backups with point-in-time recovery capability |
| **Medium** | Comprehensive test suite | Unit tests for services, integration tests for API endpoints, E2E tests for critical flows |
| **Medium** | Feature flags system | Progressive rollout of new features, A/B testing |
| **Low** | Webhook system for integrations | Allow external services to push data instead of polling |
| **Low** | Multi-language/i18n support | International startup founders |

---

## APPENDIX — QUICK REFERENCE

### Key Metrics
- **Frontend pages**: 50+
- **Backend API files**: 67
- **Total endpoints**: ~456 (213 GET, 191 POST, 16 PUT, 14 PATCH, 22 DELETE)
- **Database tables**: ~20
- **Data connectors**: 33+
- **AI agents**: 7
- **LLM integrations**: 5 (OpenAI, Anthropic, Gemini, Perplexity, Grok)
- **Event types**: 12
- **Demo seed scripts**: 3

### Technology Stack
- **Frontend**: React 18, TypeScript, Vite, Wouter, Zustand, TanStack Query, Tailwind CSS, Shadcn/ui, Recharts
- **Backend**: FastAPI, Python 3.11, SQLAlchemy, Alembic, Pydantic
- **Database**: PostgreSQL
- **Auth**: JWT (HS256) in HTTP-only cookies
- **Email**: Resend
- **SMS**: Twilio
- **AI**: OpenAI GPT-4o, Anthropic Claude, Google Gemini, Perplexity Sonar, xAI Grok
