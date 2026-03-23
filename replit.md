# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform for startups, designed to enhance survival and growth, mitigate financial risks and dilution, and support strategic financial planning. It provides investor-grade diligence, probabilistic simulations, and ranked decision recommendations to transform how startups manage their finances and interact with investors.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The platform utilizes a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. The UI/UX focuses on interactive data visualization using Tailwind CSS and shadcn/ui, with a dark mode default. Scalability is achieved with FastAPI and PostgreSQL, ensuring responsive design and fast loading for critical routes.

**Technical Implementations:**
-   **Frontend**: React 18, TypeScript, Wouter, Zustand, TanStack React Query, Tailwind CSS, shadcn/ui, Recharts for data visualization, React Hook Form with Zod for forms.
-   **Backend**: FastAPI (Python 3.11), PostgreSQL (SQLAlchemy ORM, Alembic migrations), JWT authentication with refresh token rotation, Pydantic for data validation.
-   **Redis Layer**: Optional caching, job queues (SIMULATION, CONNECTOR_SYNC, AI_AGENT, NOTIFICATION), and pub/sub. Graceful fallback to `_NullRedis`.
-   **WebSocket Layer**: Company-scoped real-time connections.
-   **Background Workers**: Unified worker with `ThreadPoolExecutor` processing Redis queue jobs.
-   **AI Copilot System**: Multi-agent Fund Flow Copilot with a Router/Orchestrator Agent, Company Knowledge Base (CKB), structured responses, and multi-LLM integration. Includes a Real-Time Simulation Copilot for context-aware prompts and data-backed recommendations. Features parallel AI agent execution for reduced latency.
-   **Key Features**:
    -   **Data Management**: CSV upload, manual entry, AI extraction, multi-currency.
    -   **Truth Scan**: Multi-stage data validation.
    -   **Simulation Engine**: Enhanced Monte Carlo simulations (24-month projections, custom events, sensitivity analysis, scenario versioning), including automatic counter-move simulations and Monte Carlo P10/P50/P90.
    -   **Optimization & Recommendations**: Constrained multi-objective optimization and automated recommendations engine.
    -   **Fundraising OS**: Cap table management, dilution calculations, fundraising round tracking, Investor Room, equity management, exit waterfall analysis.
    -   **Forecasting & Alerts**: Holt-Winters, linear regression, Z-score anomaly detection, threshold monitoring, automated metric monitoring with severity-based filtering.
    -   **Data Connectors**: Framework for payroll & ERP, with 37 production connectors (e.g., QuickBooks Online, Stripe, Gusto).
    -   **Board Deck Export**: AI-powered generation of board deck presentations (PDF).
    -   **Hiring Planner**: Planning hires by role/department/location with salary modeling and runway impact.
    -   **Fundraising Readiness Score**: Weighted scoring, radar chart, recommendations, AI-generated investment one-pager.
    -   **Multi-LLM Routing**: Intelligent task-type routing to optimize LLM selection.
    -   **AI Graphics Studio**: Generates professional AI graphics via OpenAI's gpt-image-1.
    -   **Document Generator**: AI-powered generation for financial models, investor memos, KPI reports, pitch deck outlines.
    -   **Digital Twin**: Continuously updated virtual representation of the company, integrating CompanyState, simulations, decisions, and alerts with health scoring and risk indicators.
    -   **Event Ledger**: Append-only event sourcing system tracking all domain events.
    -   **Feature Flags**: Runtime feature toggle system with global, per-company, and per-user overrides.
    -   **AI Governance**: Agent permission and usage tracking, including daily request limits and human approval flags.
    -   **Data Confidence Engine**: Metric reliability scoring based on freshness, source diversity, and consistency.
    -   **Intelligence Graph v2**: Enhanced graph for related metrics and strategy patterns.
    -   **Founder Autopilot**: Daily automated risk detection and briefing generation, triggers monthly simulation accuracy computation.
    -   **Simulation Accuracy Tracker**: Compares past Monte Carlo predictions against actuals, computes accuracy scores, and provides an auto-calibration system.
    -   **Simulation Console** (`/simulate`): 5-tab workspace (Scenarios, Stress Tests, What-If, History, Flight Simulator). The Flight Simulator tab (merged from `/simulate-v2`) features a MiroFish-inspired glassmorphism 3-column layout with: horizontal step progress tracker, animated counters (SimAnimatedCounter), glassmorphism cards (SimGlassCard), status badges (SimStatusBadge), social-media-style agent event feed (SimEventCard with reason/impact/chain), shimmer skeleton loading states, background orbs, collapsible terminal log drawer, and staggered entrance animations. All `sim-*` UI components in `client/src/components/ui/`. CSS animations prefixed with `fc-` in `client/src/styles/simulate-design.css`, respecting `prefers-reduced-motion`.
    -   **Agent Simulation Engine v1** (`server/simulation_agents/`): Multi-agent orchestrator with knowledge graph, agent memory, environment engine. API at `/api/companies/{id}/simulation/agent-run`. Shareable results via `/api/simulation/shared/{token}`.
    -   **Agent Simulation Engine v2** (`server/services/simulation/`): MiroFish-inspired LLM-powered multi-agent engine. 7 agents (Founder, 2 Investors, Customer, Team, Market, Competitor) with LLM-generated personas, per-agent memory (short-term + long-term), round-by-round decision-making via OpenAI gpt-4o-mini, stage-based activity multipliers, and post-simulation LLM report. SSE streaming API at `POST /api/simulation/v2/run` with real-time progress/agent_event/round_complete/complete events. Frontend consumes SSE via fetch ReadableStream in the Flight Simulator tab.
    -   **AI Learning Loop**: Closed-loop feedback system for Copilot. Users rate responses (helpful/not helpful), feedback stored in `copilot_feedback` table, aggregated by `feedback_analyzer.py`, and injected into Copilot prompt via `learning_context.py`. Admin UI in 6th "AI Learning" tab of System Tools.
    -   **Activity Email Triggers**: Automatic email reports sent when simulations complete (P10/P50/P90 runway results), documents are generated (board decks, investor memos, KPI reports), and decision recommendations are created (ranked action list with scores). Implemented via `server/email/activity_triggers.py` with background async sending.
    -   **Cross-Company Learning & Platform Intelligence**: Privacy-first benchmarking with anonymized data, enriching Intelligence Graph, Decision Engine, and Copilot context.
    -   **Startup Survival Simulator**: Free, public tool calculating survival probability using the Monte Carlo engine, with AI recommendations and shareable results.

## External Dependencies
-   **OpenAI**: Financial analysis, metrics extraction, vision tasks, AI image generation (gpt-image-1).
-   **Anthropic**: Complex reasoning, coding, strategic tasks.
-   **Google Gemini**: General chat, high-volume tasks.
-   **Perplexity**: Real-time web search, market research, benchmark data.
-   **OpenRouter/Grok (xAI)**: News, current events, trend analysis.
-   **Redis**: Optional caching and job queue.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Typography (Inter, IBM Plex Mono).
-   **Resend**: Email delivery services.
-   **Twilio**: SMS/phone notifications.
-   **Google OAuth**: Social login functionality.
-   **PostHog**: Analytics for page views, user identification, custom events.
-   **Slack Webhooks**: Signup notifications via `SLACK_SIGNUP_WEBHOOK_URL` env var (async, non-blocking).

## Important Data Flow Notes
-   **Single Source of Truth**: Truth Scan (`TruthScan.outputs_json.metrics`) is the canonical source for all financial metrics. All features (Board Deck, Copilot, Health Check, Decisions) read from it.
-   **Metric Key Mapping**: Truth Scan stores `net_burn` (not `monthly_burn`), `runway_p50` (not `runway_months`), `headcount`, `is_profitable`, `runway_sustainable`.
-   **API Pagination**: `/api/metrics` returns `{items: [...], total, page, page_size}` — frontend queries must handle this paginated format.
-   **Simulation Engine**: Both `simulation_engine.py` and `enhanced_monte_carlo.py` expect `baseline_growth_rate` and `gross_margin` as raw percentages (e.g., 5 for 5%, 70 for 70%). They divide by 100 internally. Never pre-divide.
-   **Simulation Guardrails**: `engine.py` enforces: growth_rate capped at 50%/mo, MRR hard cap $100M, customers cap 1M, cash += MRR - burn (no disconnect). LLM impact deltas clamped to ±30%. Agent personas use deterministic fallbacks when LLM unavailable.
-   **Decision Score Calibration**: `enhanced_engine.py` uses survival-weighted scoring (survival 35%, downside 25%, upside 20%, optionality 10%, reversibility 10%). Hard caps: survival <50% → max score 4.5/10, <70% → max 6.5/10. Revenue decline (ARR ratio <0.7) applies 15% penalty.
-   **Stress Test Projections**: `sensitivityAnalysis.ts` projects up to 60 months (not 24) so stressed companies actually run out of cash within the projection window. Only returns "Sustainable" when truly cash-flow positive.
-   **Counter-Move Differentiation**: `enhanced_monte_carlo.py` uses max_cap=240 months. Profitable simulations compute proportional runway from growth trajectories instead of flat caps.
-   **Digital Twin Fallback**: `digital_twin.py` falls back to TruthScan metrics (cash_balance, net_burn, revenue) when CompanyState has zero/missing values.
-   **Fundraising Readiness Runway**: `fundraising_readiness.py` computes runway from cash/burn when `runway_months` field is missing or zero, checking both TruthScan and FinancialRecord sources.
-   **Copilot Follow-ups**: `copilot.py` generates context-aware follow-up suggestions using 10 topic categories with company-specific metric values, simulation context, and fundraising/churn scenario branches. No repeated generic suggestions.
