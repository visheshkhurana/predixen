# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform designed for startups. Its primary goal is to enhance survival and growth, mitigate financial risks and dilution, and support strategic financial planning. The platform achieves this by providing investor-grade diligence, probabilistic simulations, and ranked decision recommendations, aiming to transform how startups manage their finances and interact with investors.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform features a modern full-stack architecture, utilizing React/TypeScript for the frontend and FastAPI/Python for the backend. It prioritizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. Key functionalities include data ingestion, truth scanning, advanced simulation, AI-driven decision-making, and an AI copilot. Scalability is achieved with FastAPI and PostgreSQL, while the UI/UX focuses on interactive data visualization using Tailwind CSS and shadcn/ui. Data integrity is maintained with Zod, Pydantic, and Alembic, and security is based on JWT authentication and RBAC. The application is fully responsive, with critical routes loading quickly and other modules loading in the background.

### Technical Implementations
-   **Frontend**: Built with React 18, TypeScript, Wouter, Zustand, and TanStack React Query. UI components leverage Tailwind CSS (dark mode default) and shadcn/ui, with Recharts for data visualization. Form management uses React Hook Form with Zod validation.
-   **Backend**: Developed with FastAPI (Python 3.11). PostgreSQL is used as the database, managed with SQLAlchemy ORM and runtime migrations (`server/core/migrations.py`). Authentication is JWT-based with refresh token rotation. Pydantic models handle data validation.
-   **Redis Layer** (optional, graceful fallback): `server/core/redis_client.py` provides caching (`cache.py`), job queues (`job_queue.py` — 4 named queues: SIMULATION, CONNECTOR_SYNC, AI_AGENT, NOTIFICATION), and pub/sub (`infrastructure/pubsub.py`). Cache keys follow `fc:<prefix>:<id>` pattern. Falls back to `_NullRedis` when Redis is unavailable.
-   **WebSocket Layer**: `server/realtime/websocket_manager.py` provides company-scoped real-time connections. Routes registered in `server/realtime/routes.py`.
-   **Background Workers**: `server/workers/worker_runner.py` — unified worker with ThreadPoolExecutor processing jobs from Redis queues. Handlers in `server/workers/handlers/`.
-   **Navigation**: Grouped sidebar with 5 sections: Core (Dashboard, Simulate, Decisions, Alerts), Finance (Cap Table, Fundraising, Investor Room, Hiring Planner), Intelligence (Digital Twin, KPI Dashboards, Health Check), Data (Data Input), Integrations (Connectors). AI Copilot has a prominent gradient button at top. Settings drawer contains secondary tools (Marketplace, Doc Generator, Journal, Goals, Admin, Support, Legal). See `client/src/components/app-sidebar.tsx`. Simulate links to `/simulate` (unified workspace).
-   **Simulate Workspace**: `client/src/pages/simulate-workspace.tsx` — unified tabbed interface with 4 tabs: Scenarios (lazy-loads `scenarios.tsx`), Stress Tests (tornado chart, reverse stress test, stress test panel), What-If Explorer (real-time variable adjustment), History (saved scenario grid). `/scenarios` redirects to `/simulate`.
-   **Onboarding Wizard**: `client/src/pages/onboarding.tsx` — 5-step flow: Welcome → Connect Data → Health Check (Truth Scan) → First Simulation (educational) → AI Copilot intro → Launch Dashboard.
-   **Observability**: `server/core/observability.py` — `track_duration(op)` context manager, `@track_operation(op)` decorator, in-process metrics store, `/metrics/internal` endpoint.
-   **Landing Page**: `client/src/pages/landing.tsx` — "Flight Simulator for Founders" positioning with hero, how-it-works, features grid, differentiation, social proof, CTA sections.
-   **Key Features**:
    -   **Data Management**: Supports CSV upload, manual entry, AI-powered extraction, and multi-currency handling.
    -   **Truth Scan**: A multi-stage data validation layer ensures data accuracy.
    -   **Simulation Engine**: Offers enhanced Monte Carlo simulations with 24-month projections, asynchronous execution, custom event modeling, sensitivity analysis, and scenario versioning. Includes automatic counter-move simulations and Monte Carlo P10/P50/P90.
    -   **Optimization & Recommendations**: Features constrained multi-objective optimization and an automated recommendations engine.
    -   **AI Copilot System**: A multi-agent Fund Flow Copilot with a Router/Orchestrator Agent, Company Knowledge Base (CKB) for context, structured responses, and multi-LLM integration. It includes a Real-Time Simulation Copilot for context-aware prompts, narrative summaries, and consultant-grade, data-backed recommendations.
    -   **Fundraising OS**: Provides comprehensive cap table management, dilution calculations, fundraising round tracking, and an Investor Room. Features full equity management with shareholder registry, equity issuance, option grants, and exit waterfall analysis.
    -   **Forecasting & Alerts**: Utilizes Holt-Winters exponential smoothing, linear regression, Z-score anomaly detection, and threshold monitoring for runway warnings. Automated metric monitoring (Burn Spike, MRR Drop, Churn Spike) with severity-based filtering and custom rules.
    -   **Data Connectors**: A framework for payroll & ERP connectors, with 37 production data connectors, including QuickBooks Online, Stripe, and Gusto.
    -   **Enhanced AI Interaction**: Includes a Copilot Trust Module, natural conversational AI, and web research capabilities for market benchmarks.
    -   **User Management**: Implements user roles (Platform Admin, Company Level Roles), password reset, and email verification.
    -   **Analytics**: Integrates PostHog for tracking page views, user identification, and custom events.
    -   **Board Deck Export**: Generates AI-powered board deck presentations (Monthly Update, Fundraising Prep, Scenario Analysis) with PDF download.
    -   **Hiring Planner**: Facilitates planning hires by role/department/location with salary modeling and runway impact analysis.
    -   **Fundraising Readiness Score**: A weighted scoring system providing a radar chart, recommendations, and an AI-generated investment one-pager.
    -   **Multi-LLM Routing**: Intelligent task-type routing to optimize LLM selection based on task requirements (e.g., financial analysis to GPT-4o, strategy to Claude Sonnet).
    -   **AI Graphics Studio**: Generates professional AI graphics via OpenAI's gpt-image-1, supporting various styles and aspect ratios.
    -   **Document Generator**: AI-powered generation for financial models, investor memos, KPI reports, and pitch deck outlines, leveraging multi-LLM routing and optional web research.
    -   **Digital Twin**: A continuously updated virtual representation of the startup company. Mirrors real-time financial state, operational metrics, and strategic decisions. Integrates CompanyState, simulations, decisions, and alerts into a unified twin model with health scoring, risk indicators, event tracking, and an embedded Monte Carlo simulation explorer. Frontend dashboard at `/digital-twin`, API at `/companies/{id}/twin/*`.
    -   **Extended Agent Architecture**: Operations Agent (execution planning), Review/Reflection Agent (output validation), Auto-Trigger Simulations (alert-driven Monte Carlo), Cross-Company Decision Pattern Engine, Slack Copilot (5 slash commands), Enhanced Connector Queue (priority-based sync scheduling).
    -   **Parallel AI Agent Execution**: Router Agent dispatches specialist agents (CFO, Market, Strategy, Operations) concurrently via `asyncio.gather` — 50-70% latency reduction vs sequential. See `server/copilot/agents/router.py`.
    -   **Event Ledger**: Append-only event sourcing system (`server/events/event_store.py`). Tables: `events`, `event_payloads`, `event_consumers`, `event_projections`. Tracks all domain events (financial updates, simulation runs, decisions, alerts, autopilot runs).
    -   **Feature Flags**: Runtime feature toggle system (`server/core/feature_flags.py`). Tables: `feature_flags`, `company_flags`, `user_flags`. 10 default flags seeded on startup. Supports global, per-company, and per-user overrides.
    -   **AI Governance**: Agent permission and usage tracking (`server/copilot/ai_governance.py`). Tables: `ai_agent_permissions`, `ai_agent_logs`, `ai_agent_budgets`. 9 agents with daily request limits and human approval flags. Provides `check_permission()` guard and `log_usage()` audit trail.
    -   **Data Confidence Engine**: Metric reliability scoring (`server/services/data_confidence.py`). Table: `data_confidence_scores`. Computes freshness, source diversity, and consistency scores for financial metrics.
    -   **Intelligence Graph v2**: Enhanced with adjacency tables (`graph_nodes`, `graph_edges`). Functions: `upsert_graph_node`, `add_graph_edge`, `get_related_metrics`, `get_strategy_patterns` in `server/services/intelligence_graph.py`.
    -   **Founder Autopilot**: Daily automated risk detection and briefing generation (`server/services/founder_autopilot.py`). Table: `autopilot_runs`. 5 risk detection rules (burn spike, low runway, MRR drop, churn spike, cash crisis). Generates natural language briefings with state snapshots.
    -   **API Domain Routers**: 7 domain routers in `server/api/domain/` (company, finance, simulation, decision, connector-domain, ai, system). Registered in `main.py`. Prefix pattern: `/system`, `/finance`, etc. (NO `/api` prefix — Express proxy strips it).
    -   **Internal Admin Tools**: Admin System Tools page at `/admin/system` (`client/src/pages/admin/system-tools.tsx`). 4-tab UI: Events (event ledger viewer), Agents (AI governance dashboard), Flags (feature flag toggles), Autopilot (briefing viewer + run trigger).
    -   **Startup Survival Simulator**: Free viral tool at `/survival-simulator` (public, no auth). Uses existing Monte Carlo engine (1,000 simulations) to calculate survival probability. Features: input form (cash, revenue, expenses, growth, churn, hires, fundraising), grade system (A-D), survival gauges (6/12/18/24 months), runway distribution histogram, cash trajectory chart, AI recommendations, shareable results (`/survival/:simId`), export investor report (PDF via print), growth gating (1 free sim then signup prompt). Backend: `server/api/survival_simulator.py`, table: `survival_simulations`. SEO optimized with meta/OG tags.

## External Dependencies

-   **OpenAI**: Used for financial analysis, metrics extraction, vision tasks, and AI image generation (gpt-image-1).
-   **Anthropic**: Utilized for complex reasoning, coding, and strategic tasks.
-   **Google Gemini**: Employed for general chat and high-volume tasks.
-   **Perplexity**: Provides real-time web search, market research, and benchmark data.
-   **OpenRouter/Grok (xAI)**: Integrated for news, current events, and trend analysis.
-   **Redis**: Optional caching and job queue layer (graceful fallback when unavailable).
-   **PostgreSQL**: Serves as the primary relational database.
-   **Google Fonts**: Used for typography (Inter, IBM Plex Mono).
-   **Resend**: Handles email delivery services.
-   **Twilio**: Used for SMS/phone notifications.
-   **Google OAuth**: Provides social login functionality.

## Demo Data & Seeding

-   **Demo User**: `demo@founderconsole.ai` / `demo123` (owner role, platform admin).
-   **Demo Company**: TechFlow Analytics (SaaS, Series A). Company ID varies (first in user's company list).
-   **Seed Scripts**:
    -   `server/seed/seed_demo.py`: Core demo data — financials, scenarios, decisions, cap table, team, connectors, metrics.
    -   `server/seed/seed_twin_intelligence.py`: Digital Twin & Intelligence Graph data — 25 twin events per company, enriched CompanyState ($513K cash, $28K burn, $44K MRR), 12 months financial records, 8 peer SaaS companies with financial history, additional strategic decisions.
    -   `server/seed/seed_benchmarks.py`: Industry benchmark data.
-   **Startup Index Creation**: `ensure_graph_indexes()` runs on every startup (outside migrations branch) to create Intelligence Graph performance indexes.

## Operations Scripts

-   `scripts/db_backup.py`: Automated PostgreSQL backup with gzip compression, retention policy (default 7 backups).
-   `scripts/db_restore.py`: Backup restore utility with `--list` option to view available backups.

## Architecture Documentation

-   Full architecture documentation: `docs/ARCHITECTURE.md` — system overview, folder structure, data flow, deployment topology.
-   Health endpoint: `GET /health` — returns DB, Redis, and system status.