# Predixen Intelligence OS

## Overview
Predixen Intelligence OS is an AI-powered financial intelligence platform for startups, designed to maximize survival and growth while minimizing risk and dilution. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to guide financial planning. The platform aims to help startups understand their financial health, predict future outcomes, and make informed strategic decisions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform utilizes a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It focuses on data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design encompassing data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved with FastAPI and PostgreSQL, while UI/UX prioritizes data visualization and interactive components using Tailwind CSS and shadcn/ui. Data integrity is maintained with Zod, Pydantic, and Alembic, and security is based on JWT authentication and RBAC.

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
-   **Production Hardening**: Environment-driven CORS, process supervision with graceful shutdown, configurable DB initialization, and health endpoints.

### Key Features and Technical Implementations
1.  **Data Ingestion**: Supports CSV upload, manual entry, and AI-powered extraction from Excel/PDFs with OpenAI Vision fallback.
2.  **Truth Scan**: A multi-stage validation layer (receive → normalize → validate → repair → finalize) ensuring data quality before simulations. It tracks full data provenance, categorizes issues, offers auto-fix capabilities with audit trails, and gates simulations until data is finalized.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, supporting various probability distributions, configurable iterations, asynchronous execution, regime-aware simulations, and custom event modeling.
4.  **Sensitivity Analysis**: Generates tornado charts by perturbing single variables to identify key drivers.
5.  **Scenario Versioning**: Provides version control for scenarios, including macro-economic modifiers and API for managing presets.
6.  **Constrained Multi-Objective Optimization**: An advanced optimizer handling constraints on financial metrics and using a weighted composite score for multi-objective decision-making.
7.  **Automated Recommendations Engine**: Generates health-based recommendations based on financial health indicators, with version history and rollback capabilities.
8.  **Multi-Agent Fund Flow Copilot V2+**: An AI system with a Router/Orchestrator Agent directing queries to specialized agents (CFO, Market, Strategy, Decision Advisor). It maintains a Company Knowledge Base (CKB) for context, provides structured responses with truth-first citations, and integrates multi-LLM for task-specific model selection.
    -   **Decision Advisor Agent**: Automatically detects decision-oriented queries, extracts context, maps decisions to financial levers, runs automatic Monte Carlo simulations, provides risk analysis, and delivers opinionated recommendations.
9.  **Real-Time Simulation Copilot**: AI guidance integrated into the simulation workflow, providing context-aware prompts, impact indicators, and narrative summaries as users adjust parameters.
10. **Fundraising OS**: A comprehensive module for cap table management, dilution calculations, fundraising round tracking, and an Investor Room for materials and pipeline management.
11. **Forecasting**: Utilizes Holt-Winters exponential smoothing and linear regression.
12. **Alerts**: Implements Z-score anomaly detection, threshold monitoring, and runway warnings.
13. **Admin Dashboard**: Centralized management for users, companies, billing, and platform metrics with RBAC.
14. **Payroll & ERP Connector Framework**: An extensible system for syncing financial data from Indian payroll and ERP providers.
15. **Feature Notification System**: Automated email notifications for platform changes via Resend.
16. **Multi-LLM Router**: Unified interface for intelligent task-based model selection across OpenAI, Anthropic, and Google Gemini, with task routing, graceful fallbacks, PII redaction, and audit logging.
17. **Copilot Trust Module**: Ensures all AI-generated financial predictions are grounded in verified simulation data with full provenance tracking. Includes:
    -   `fetchVerifiedRunResult()`: Deterministic run fetching with grounding status (VERIFIED/UNVERIFIED/NOT_AVAILABLE/UNVERIFIED_MISMATCH)
    -   Validation flags detecting runway/cash/burn mismatches, survival probability inconsistencies, zero-variance Monte Carlo outputs
    -   Strict grounding rules requiring all numeric values to come from verified simulations with provenance (companyId, scenarioId, runId, timestamp, dataSnapshotId)
    -   Never fabricates or estimates numbers; uses percentile ranges (P10/P50/P90) with citations
18. **Natural Copilot Conversation**: Enhanced conversational AI for more natural founder interactions:
    -   **Automatic Context Passing**: Session state tracking (active_scenario_id, active_run_id, baseline_run_id) passed invisibly
    -   **Response Modes**: Auto-detection and formatting for EXPLAIN, COMPARE, PLAN, TEACH, JSON modes
    -   **Enhanced Citations**: `ensure_citations()` with provenance blocks for all numeric claims
    -   **Clarification Detection**: Identifies ambiguous queries and requests context
    -   **Causal Explanations**: Top 3 driver extraction from sensitivity analysis
    -   **Prompt Templates Library**: Metric Summary, Comparison, Why Explanation, Decision Advice
    -   **Feedback Loop**: "Was this helpful?" endpoint with improvement capture

### User Roles
-   **Platform Admin**: Application owner with access to the Admin dashboard.
-   **Company Level Roles**: `owner`, `admin`, `analyst`, `viewer` with varying access levels.

## Recent Changes (Feb 2026)
-   **KPI Board**: Fixed data flickering/persistence bug by switching from WebSocket-only to React Query-cached historical data endpoint. Trend charts now load from financial records (up to 12 months) instead of only WebSocket updates.
-   **KPI Board Data Source**: Uses cascade: live snapshot → historical records → financial baseline. Data is cached with `staleTime: 60s` to prevent $0 flash on navigation.
-   **Metric Catalog**: Auto-initializes system metrics on first visit per company (uses company-scoped ref guard).
-   **Simulation Fixes**: Decision ranking uses scenario key mapping; query invalidation for timeseries/scenarios after simulation runs; churn rate KPI displays correctly as percentage.
-   **API**: Added `GET /api/realtime/kpi/{company_id}/history` endpoint for historical KPI data from financial records.

## External Dependencies

-   **OpenAI**: GPT-4o for financial analysis, metrics extraction, vision tasks.
-   **Anthropic**: Claude Opus/Sonnet/Haiku for complex reasoning, coding, strategy.
-   **Google Gemini**: Gemini 2.5/3 Flash/Pro for general chat, high-volume tasks.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.