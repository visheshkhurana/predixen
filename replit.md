# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform designed for startups. Its primary goal is to enhance survival and growth while mitigating risk and dilution. The platform offers investor-grade diligence, probabilistic simulations, and ranked decision recommendations to support financial planning, enabling startups to understand their financial health, predict future outcomes, and make strategic decisions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform utilizes a modern full-stack architecture, combining React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. Key architectural components include data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved using FastAPI and PostgreSQL, while UI/UX focuses on data visualization and interactive components built with Tailwind CSS and shadcn/ui. Data integrity is enforced via Zod, Pydantic, and Alembic, with security based on JWT authentication and RBAC.

### Frontend Architecture
-   **Frameworks**: React 18 with TypeScript, Wouter, Zustand, TanStack React Query.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.

### Backend Architecture
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based.
-   **Validation**: Pydantic models.

### Key Features and Technical Implementations
1.  **Data Management**: Supports CSV upload, manual entry, AI-powered extraction, and multi-currency handling with industry-adaptive terminology.
2.  **Truth Scan**: A multi-stage data validation layer ensuring data quality and provenance.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, various probability distributions, asynchronous execution, and custom event modeling. Includes sensitivity analysis and scenario versioning.
4.  **Optimization & Recommendations**: Features constrained multi-objective optimization and an automated recommendations engine with version history.
5.  **AI Copilot System**: A Multi-Agent Fund Flow Copilot V2+ with a Router/Orchestrator Agent directing queries to specialized agents (CFO, Market, Strategy, Decision Advisor). It uses a Company Knowledge Base (CKB) for context, provides structured responses, and integrates multi-LLM for task-specific model selection.
6.  **Real-Time Simulation Copilot**: AI guidance integrated into the simulation workflow, offering context-aware prompts and narrative summaries.
7.  **Fundraising OS**: Module for cap table management, dilution calculations, fundraising round tracking, and an Investor Room.
8.  **Forecasting & Alerts**: Utilizes Holt-Winters exponential smoothing and linear regression for forecasting, and Z-score anomaly detection, threshold monitoring, and runway warnings for alerts.
9.  **Data Connectors**: Framework for payroll & ERP connectors and 37 production data connectors across various financial and operational categories.
10. **Enhanced AI Interaction**: Includes a Copilot Trust Module for data veracity, natural conversational AI with context passing and diverse response modes, and web research capabilities via Perplexity for market benchmarks.
11. **Consultant-Grade Copilot Persona**: System prompts are upgraded to provide structured, data-backed recommendations with a strategic persona.
12. **Simulation Experience Upgrade**: Features Before/After Delta Cards, Payback Clock Widget, Risk Alert Banner, data-driven recommendations (GO/CONDITIONAL/NO-GO), second-order effects detection, and confidence scoring.
13. **Automatic Counter-Move Simulation**: System automatically runs 3 counter-move simulations (Cost Cut 20%, Raise Prices 10%, Freeze Hiring) when a scenario is simulated, providing runway/survival deltas.
14. **AI Decision Summary**: A gradient-bordered card at the top of simulation results providing a 1-2 sentence recommendation, Decision Score, verdict, and supporting bullet points.
15. **Reorganized Simulation Results Hierarchy**: Presents results in a decision-intelligence-first order, starting with the AI Summary and proceeding through recommendations, comparisons, analyses, and forecasting.
16. **Dual-Path "Or" Detection**: Detects "X or Y" / "X vs Y" in scenario inputs, running both Monte Carlo simulations in parallel for side-by-side comparison.
17. **Cross-Page Intelligence Alerts**: Reusable component that fetches simulation data and generates contextual alerts across key pages based on financial metrics.
18. **Narrative Strategic Briefing (Decisions Page Redesign v2)**: Transforms the Decisions page into a text-based "founder's briefing document" with sections covering the situation, recommendations, consequences of inaction, an execution playbook, and key risks with contingency plans.
19. **Centralized Financial Metrics Hook**: Provides a single source of truth for all financial metrics, tracking provenance and supporting AI Estimated badges.

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