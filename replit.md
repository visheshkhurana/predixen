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