# Predixen Intelligence OS

## Overview
Predixen Intelligence OS is an AI-powered financial intelligence platform for startups. Its purpose is to maximize survival and growth while minimizing risk and dilution. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to guide financial planning. The platform helps startups understand their financial health, predict future outcomes, and make informed strategic decisions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform uses a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It focuses on data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design encompassing data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved with FastAPI and PostgreSQL. UI/UX prioritizes data visualization and interactive components using Tailwind CSS and shadcn/ui. Data integrity is maintained with Zod, Pydantic, and Alembic, and security is based on JWT authentication and RBAC.

### Frontend Architecture
-   **Frameworks**: React 18 with TypeScript, Wouter, Zustand, TanStack React Query.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.
-   **Build Tool**: Vite.

### Backend Architecture
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based.
-   **Validation**: Pydantic models.

### Key Features and Technical Implementations
1.  **Data Ingestion**: Supports CSV upload, manual entry, and AI-powered extraction from Excel/PDFs.
2.  **Truth Scan**: A multi-stage validation layer ensuring data quality before simulations, with data provenance tracking and auto-fix capabilities.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, various probability distributions, asynchronous execution, and custom event modeling.
4.  **Sensitivity Analysis**: Generates tornado charts to identify key drivers by perturbing single variables.
5.  **Scenario Versioning**: Provides version control for scenarios, including macro-economic modifiers.
6.  **Constrained Multi-Objective Optimization**: An advanced optimizer for financial metrics using a weighted composite score.
7.  **Automated Recommendations Engine**: Generates health-based recommendations with version history and rollback.
8.  **Multi-Agent Fund Flow Copilot V2+**: An AI system with a Router/Orchestrator Agent directing queries to specialized agents (CFO, Market, Strategy, Decision Advisor). It uses a Company Knowledge Base (CKB) for context, provides structured responses with citations, and integrates multi-LLM for task-specific model selection.
    -   **Decision Advisor Agent**: Detects decision-oriented queries, extracts context, maps decisions to financial levers, runs simulations, provides risk analysis, and delivers recommendations.
9.  **Real-Time Simulation Copilot**: AI guidance integrated into the simulation workflow, providing context-aware prompts and narrative summaries.
10. **Fundraising OS**: Module for cap table management, dilution calculations, fundraising round tracking, and an Investor Room.
11. **Forecasting**: Utilizes Holt-Winters exponential smoothing and linear regression.
12. **Alerts**: Implements Z-score anomaly detection, threshold monitoring, and runway warnings.
13. **Admin Dashboard**: Centralized management for users, companies, billing, and platform metrics with RBAC.
14. **Payroll & ERP Connector Framework**: Extensible system for syncing financial data.
15. **Multi-LLM Router**: Unified interface for intelligent task-based model selection across various LLMs, with task routing, fallbacks, and audit logging.
16. **Copilot Trust Module**: Ensures AI-generated financial predictions are grounded in verified simulation data with full provenance tracking, never fabricating or estimating numbers.
17. **Natural Copilot Conversation**: Enhanced conversational AI with automatic context passing, various response modes (EXPLAIN, COMPARE, PLAN, TEACH, JSON), enhanced citations, clarification detection, causal explanations, and prompt templates.
18. **Production Data Connectors**: 37 implemented connectors across finance/accounting, CRM, payroll/HRIS, banking/spend, analytics, and ERP/database categories.
19. **Smart CSV Import**: AI-powered CSV detection and import with column mapping.
20. **Copilot Quick Chat with Web Research**: Natural language financial queries supported by internal data and real-time web research using Perplexity for market benchmarks and industry trends.
21. **Consultant-Grade Copilot Persona**: System prompts upgraded to a McKinsey + a16z partner persona, providing structured, opinionated recommendations backed by data.
22. **Simulation Experience Upgrade**: Before/After Delta Cards for scenario comparison (auto-detects baseline), Payback Clock Widget with P10-P90 range, Risk Alert Banner (warning/critical thresholds), data-driven recommendations with GO/CONDITIONAL/NO-GO verdicts, second-order effects detection, and confidence scoring.
23. **Automatic Counter-Move Simulation**: When a scenario is simulated, the system automatically runs 3 counter-move simulations (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) using 500-iteration Monte Carlo with additive overrides on top of current scenario inputs. Results show runway/survival deltas vs current scenario. Users can "Apply" any counter-move to create a new derived scenario. Backend endpoint: `POST /scenarios/{id}/counter-moves`. Frontend: `CounterMoveCards` component in `ScenarioDeltas.tsx`.
24. **AI Decision Summary**: Gradient-bordered card at top of simulation results with consultant-grade 1-2 sentence recommendation, Decision Score (1-10), GO/CONDITIONAL/NO-GO verdict, and 3 supporting bullet points (Key Risk, Key Opportunity, Watch metric). Component: `AIDecisionSummary.tsx`.
25. **Reorganized Simulation Results Hierarchy**: Results flow in decision-intelligence-first order: AI Summary → Decision Recommendations → Before/After → Sensitivity Levers + Breaking Points → Stress Tests → P10/P50/P90 Monte Carlo → Charts → Fundraising Intelligence. No hidden sections or Advanced View toggle.
26. **Dual-Path "Or" Detection**: When users type "X or Y" / "X vs Y" in the scenario input, the system detects two separate decision paths, runs both Monte Carlo simulations in parallel, and sets up side-by-side comparison. Visual preview indicator below search bar, loading/completion banners, and partial-failure handling via `Promise.allSettled`.
27. **Cross-Page Intelligence Alerts**: Reusable `CrossPageIntelligence` component that fetches latest simulation data via `useScenarios`/`useSimulation` hooks and generates contextual alerts (critical/warning/opportunity) based on survival, runway, and burn metrics. Displayed on Dashboard, Data Input, and Fundraising pages.
28. **Narrative Strategic Briefing (Decisions Page Redesign v2)**: Complete redesign of the Decisions page into a text-based, narrative-driven "founder's briefing document." No charts, bar graphs, percentage badges, or KPI cards. The page reads like a strategic memo from an advisor. Five sections:
    - **Section 1 "The Situation"**: AI-generated 3-5 sentence paragraph describing current financial state using real data (MRR, burn rate, runway, growth rate).
    - **Section 2 "What We Recommend"**: Bold action headline + 2-3 paragraphs of written rationale (WHY this action, WHY now, trade-offs, consequences of waiting) + urgency text indicator.
    - **Section 3 "What Happens If You Do Nothing"**: 2-3 paragraph narrative projection of inaction consequences with specific numbers, exhaustion date, and break-even growth requirements.
    - **Section 4 "Execution Playbook"** (THE MOST IMPORTANT SECTION): 6-10 specific, team-ready action items the founder can forward directly, grouped into phases. Each item has: phase (Phase 1: Preparation Week 1-2, Phase 2: Execution Week 3-4, Phase 3: Optimization Week 5-8), action (clear directive), owner (role responsible), timeline (specific deadline within phase), definition_of_done (verifiable completion criteria). Different playbooks generated for survival (<12mo runway) vs growth (>12mo runway) scenarios. Backend helper `_build_fallback_playbook()` generates data-driven items using actual company numbers. Frontend groups items by phase with phase headers and renders "Done when:" labels.
    - **Section 5 "Key Risks & Contingency Plans"**: 3-5 specific, data-driven risks with likelihood (High/Medium/Low), impact description, and concrete contingency actions. Backend helper `_build_fallback_key_risks()` generates risks based on actual metrics (runway, growth, burn). LLM prompt enforces executable contingency plans, not vague advice.
    - Backend: `GET /api/companies/{id}/strategic-diagnosis` returns `situation_narrative`, `recommendation_headline`, `recommendation_narrative`, `urgency_text`, `inaction_narrative`, `execution_playbook[]`, `key_risks[]`. Uses `useStrategicDiagnosisQuery` hook for auto-fetch via TanStack Query. LLM prompt includes net burn, exhaustion date, and break-even growth data.
    - Frontend: `decisions.tsx` renders as clean prose document (max-w-3xl, article markup). Playbook renders as numbered action items with owner/deadline/outcome metadata. Risks render as numbered items with likelihood/impact/contingency labels. Defensive guards handle malformed LLM output.

29. **Centralized Financial Metrics Hook** (`useFinancialMetrics`): Single source of truth for all financial metrics across pages. Merges data from computed metrics API, truth scan, and financial baseline. Tracks metric source provenance (`reported`/`computed`/`estimated`) for AI Estimated badges. Fields: mrr, arr, cashOnHand, burnRate, netBurn, runway, cac, ltv, ltvCacRatio, grossMargin, churnRate, totalCustomers, headcount, arpu, paybackPeriod, burnMultiple, revenuePerEmployee, monthlyGrowthRate, ndr, sources.
30. **Multi-Currency Support**: `useCurrency` hook provides company-specific currency formatting. Currency auto-detected from website TLD during onboarding (25+ TLD mappings). Currency selector in onboarding with 20 currencies. `formatCurrencyAbbrev` and `formatCurrencyFull` in `lib/utils.ts` accept currency parameter.
31. **Industry-Adaptive Terminology**: `useIndustryTerms` hook maps industry-specific terms (customer→patient for healthcare, customer→learner for edtech, etc.). Applied to overview page KPI labels. Covers 11 industry verticals.
32. **Extended Onboarding Options**: 15 industry categories (SaaS, Fintech, E-commerce, D2C, Marketplace, Healthcare, EdTech, AgriTech, DeepTech, Climate, Media, Logistics, Real Estate, Food, Other) and 8 company stages (Pre-seed, Seed, Pre-Series A, Series A, Series B+, Growth, Pre-IPO, Public).

### User Roles
-   **Platform Admin**: Application owner.
-   **Company Level Roles**: `owner`, `admin`, `analyst`, `viewer` with varying access levels.

## External Dependencies

-   **OpenAI**: For financial analysis, metrics extraction, and vision tasks.
-   **Anthropic**: For complex reasoning, coding, and strategy.
-   **Google Gemini**: For general chat and high-volume tasks.
-   **Perplexity**: For real-time web search, market research, and benchmark data in the copilot.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.