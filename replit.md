# Predixen Intelligence OS

## Overview
Predixen Intelligence OS is an AI-powered financial intelligence platform for startups. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to guide startups through financial planning. The platform helps startups understand their financial health, predict future outcomes, and make informed strategic decisions to maximize survival and growth while minimizing downside risk and dilution.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform is built on a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design for ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is ensured with FastAPI and PostgreSQL. UI/UX focuses on data visualization and interactive components, using Tailwind CSS and shadcn/ui. Data integrity is maintained with Zod, Pydantic, and Alembic, while security relies on JWT-based authentication and RBAC.

### Frontend Architecture
-   **Frameworks**: React 18 with TypeScript, Wouter for routing, Zustand for state management, TanStack React Query for server state.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.
-   **Build Tool**: Vite.

### Backend Architecture
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based.
-   **Validation**: Pydantic models.

### Production Hardening (Jan 2026)
-   **CORS**: Env-driven origins via `CORS_ORIGINS` (no wildcard with credentials). Defaults to localhost in dev, empty in prod.
-   **Process Supervision**: Node spawns uvicorn with graceful shutdown (SIGTERM/SIGKILL) and auto-restart with exponential backoff (max 5 attempts).
-   **DB Initialization Flags**: Schema creation, migrations, and seeding gated by env vars (`CREATE_SCHEMA`, `RUN_MIGRATIONS`, `SEED_BENCHMARKS`, `SEED_DEMO_DATA`). Default true in dev, false in prod.
-   **Health Endpoints**: `/health` on Node (includes FastAPI status) and `/health` on FastAPI.
-   **Pytest**: Configured via `pytest.ini` with pythonpath for test discovery from repo root.

### Key Features and Technical Implementations
1.  **Data Ingestion**: Supports CSV upload, manual baseline entry, and AI-powered extraction from Excel/PDFs using OpenAI, with a two-stage PDF extraction process including Vision fallback for scanned documents.
2.  **Truth Scan**: A comprehensive validation layer that sits between data uploads and simulation runs:
    - **Validation Pipeline**: Multi-stage process (receive → normalize → validate → repair → finalize) ensuring data quality before simulations
    - **Database Tables**: `truth_scan_uploads`, `truth_datasets`, `validation_reports`, `validation_issues`, `truth_decision_logs` for full provenance tracking
    - **Issue Categories**: Structural, arithmetic, accounting, plausibility, completeness, and conflict with severity levels (blocked, high, medium, low)
    - **Auto-fix Capabilities**: Safe repairs for net burn, runway months, and growth rate calculations with full audit trail
    - **Simulation Gating**: `/simulation-jobs/run` returns 409 if truth dataset not finalized, redirecting users to Truth Scan Gate UI
    - **API Endpoints**: `/truth-scan/from-import-session`, `/truth-scan/from-dataset`, `/truth-scan/from-manual-baseline`, `/truth-scan/uploads/{id}`, `/truth-scan/resolve`, `/truth-scan/finalize`
    - **Frontend Component**: `TruthScanGate.tsx` with tabs for auto-fixed issues, issues needing confirmation, and blocked issues
    - **Core Formulas**: `net_burn = revenue - total_expenses`, `runway = cash_balance / |monthly_burn|`
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, supporting various probability distributions, configurable iterations, and asynchronous job execution. It includes regime-aware simulations (Base, Downturn, Breakout) and custom event modeling with conditional triggering.
4.  **Sensitivity Analysis**: Generates data for tornado charts by performing One-At-a-Time (OAT) perturbation to identify key drivers impacting runway.
5.  **Scenario Versioning**: Provides full version control for scenarios, including macro-economic modifiers (optimistic, neutral, pessimistic, stagflation, boom) and API endpoints for managing presets.
6.  **Constrained Multi-Objective Optimization**: An advanced optimizer that handles constraints on key financial metrics (e.g., runway, survival, cash) and uses a weighted composite score for multi-objective decision-making.
7.  **Automated Recommendations Engine**: Generates health-based recommendations (e.g., reduce burn, fundraise) based on predefined thresholds for financial health indicators like runway and survival probability. It also includes version history, diff views, and rollback capabilities for scenarios.
8.  **Multi-Agent Fund Flow Copilot V2+**: A production-ready AI system featuring a Router/Orchestrator Agent that routes queries to specialized agents (CFO, Market, Strategy, Decision Advisor). It maintains a Company Knowledge Base (CKB) for persistent context, provides structured responses with truth-first citations, and includes data health scoring, operating cadence management, and automated alerts. The copilot now uses multi-LLM integration with task-specific model selection:
    - CFO Agent: GPT-4o for financial analysis (best at structured data)
    - Market Agent: Claude Sonnet for market research (balanced reasoning)
    - Strategy Agent: Claude Sonnet for strategic planning
    - Decision Advisor Agent: GPT-4o for decision-first, probability-driven advice
    - Router Agent: Gemini Flash for orchestration and response synthesis
    
    **Decision Advisor Agent (Jan 2026)**: A new specialized agent that transforms user questions into actionable, simulation-backed recommendations:
    - Automatically detects decision-oriented queries (e.g., "how can I extend runway", "what should I do about burn")
    - Extracts decision context including type, timeframe, and constraints
    - Maps decisions to quantitative financial levers with feasibility ratings (easy/moderate/difficult)
    - Runs automatic Monte Carlo simulations showing P10/P50/P90 runway and survival probabilities
    - Provides risk analysis with sensitivity tables and failure cascade narratives
    - Delivers opinionated recommendations with confidence levels (high/medium/low) and reasoning
    - Renders in a dedicated DecisionAdvisorPanel UI with collapsible sections for simulations, levers, and risks
9.  **Real-Time Simulation Copilot (Jan 2026)**: AI-powered guidance integrated into the simulation workflow:
    - **Context-Aware Prompts**: As users adjust simulation parameters (pricing, growth, burn, margins, churn, CAC), the AI explains the impact of each change on key metrics like runway, survival probability, and cash position
    - **Debounced API Calls**: Uses 300ms debounce to prevent excessive API calls while users drag sliders
    - **Impact Level Indicators**: Displays high/medium/low impact badges for parameter changes
    - **Narrative Summaries**: Generates plain-language explanations of simulation results including health status (healthy/warning/critical), top 5 key drivers by impact score, comparative insights, and actionable recommendations
    - **Components**: `AICopilotGuidance` for real-time slider feedback, `AISummaryCard` for result narratives
    - **Endpoints**: `/simulation-copilot/prompt/{company_id}` and `/simulation-copilot/narrative/{company_id}`
10.  **Copilot V6: Fundraising OS**: A comprehensive fundraising module with cap table management (common, preferred shares, option pools, convertible notes), a cap table engine for dilution calculations, fundraising round tracking, and a dilution simulator. It also includes an Investor Room for generating investor materials and managing an investor pipeline.
11. **Forecasting**: Utilizes Holt-Winters exponential smoothing and linear regression.
12. **Alerts**: Implements Z-score anomaly detection, threshold monitoring, and runway warnings.
13. **Admin Dashboard**: Centralized management for users, companies, billing, and platform metrics with RBAC, accessible only by the platform admin.
14. **Payroll & ERP Connector Framework**: An extensible system for syncing financial data from Indian payroll and ERP providers (e.g., RazorpayX Payroll, GreytHR, Zoho Books, Tally ERP) with a `BaseConnector` and `ConnectorRegistry` for various authentication types and data normalization.
15. **Feature Notification System**: Automated email notifications for platform changes and updates, delivered via Resend, with predefined recipients and professional HTML templates.
16. **Multi-LLM Router**: Unified interface for intelligent task-based model selection across multiple AI providers (OpenAI GPT-4o, Anthropic Claude, Google Gemini). It features intelligent task routing to optimal models, graceful fallback mechanisms, feature-aware routing for specific requests (e.g., JSON mode), PII redaction, and audit logging.

### User Roles
-   **Platform Admin**: Application owner with access to the Admin dashboard.
-   **Company Level Roles**: `owner`, `admin`, `analyst`, `viewer` with varying access levels to company data.

## Recent Changes (Feb 2026)

### Trust & Simulation Sprint 1 (Feb 2026)
- **Context Bar**: Added global context bar in app header showing Company • Scenario • Run ID • Timestamp • Data Freshness with tooltips for provenance details
- **KPI Provenance Tooltips**: MetricCard component now supports provenance data showing definition, formula, source (Truth Scan/Simulation/Manual), timestamp, run ID, and confidence score
- **Scenario/Run Tracking**: Added `currentScenario` and `latestRun` to global store for cross-module consistency
- **Glossary Integration**: Created KPI_DEFINITIONS export with standardized metric definitions (Runway, Net Burn, Survival Probability, etc.)

### QA Bug Fixes Deployment
- **PRED-001**: Overview page now syncs with Truth Scan data - fixed $0 cash display issue
- **PRED-002**: Net Burn labeling corrected - negative values properly indicate cash burn
- **PRED-003**: AI Copilot aligns with Truth Scan metrics - agents now cite exact values with timestamps
- **PRED-004**: Alerts page handles insufficient data gracefully - shows "More Data Needed" amber warning
- **PRED-005**: Alert CTAs route to correct pages - /data and /truth routes work properly
- **PRED-006**: Templates use selected company correctly - scenarios create properly
- **PRED-007**: Cap Table and Fundraising API calls fixed - forms submit correctly with proper JSON parsing
- **PRED-010/011**: Enhanced Monte Carlo engine with dynamic horizon extension (up to 264 months) - P10/P50/P90 now show realistic variance

### Simulation Engine Upgrade
- Upgraded from `run_monte_carlo` to `run_enhanced_monte_carlo` for all simulation runs
- Dynamic horizon extension: Simulations extend beyond initial horizon when survival probability remains high
- Removed deprecated `hiring_plan` parameter from enhanced simulation inputs

### Copilot Alignment
- Router and CFO agents now include explicit instructions to use Truth Scan validated values
- Citation format: "[value] (per Truth Scan, [date])" for all financial metrics
- Reduced KPI contradictions between chat responses and dashboard displays

## External Dependencies

-   **OpenAI**: GPT-4o for financial analysis, metrics extraction, vision tasks (via Replit AI Integrations).
-   **Anthropic**: Claude Opus/Sonnet/Haiku for complex reasoning, coding, strategy (via Replit AI Integrations).
-   **Google Gemini**: Gemini 2.5/3 Flash/Pro for general chat, high-volume tasks (via Replit AI Integrations).
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.