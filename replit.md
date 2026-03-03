# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform for startups. Its purpose is to enhance survival and growth, mitigate risk and dilution, and support strategic financial planning through investor-grade diligence, probabilistic simulations, and ranked decision recommendations. The platform aims to revolutionize how startups manage their finances and interact with investors by providing tools to understand financial health, predict outcomes, and make informed decisions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform employs a modern full-stack architecture, utilizing React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. Key architectural components include data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved using FastAPI and PostgreSQL, while UI/UX focuses on data visualization and interactive components built with Tailwind CSS and shadcn/ui. Data integrity is enforced via Zod, Pydantic, and Alembic, with security based on JWT authentication and RBAC. All inner app pages are fully responsive. Critical routes (auth, billing, onboarding) register quickly, with other modules loading in the background.

### Frontend
-   **Frameworks**: React 18 with TypeScript, Wouter, Zustand, TanStack React Query.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.
-   **Marketing Site**: Redesigned public marketing site with shared `MarketingLayout` for pages like Landing, Features, About, Contact, Blog, FAQ, Demo.

### Backend
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based with refresh token rotation.
-   **Validation**: Pydantic models.
-   **Security**: HSTS and CSP headers, body parser limits, file upload size limits.

### Key Features
-   **Data Management**: Supports CSV upload, manual entry, AI-powered extraction, multi-currency handling.
-   **Truth Scan**: Multi-stage data validation layer.
-   **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, asynchronous execution, custom event modeling, sensitivity analysis, and scenario versioning. Includes automatic counter-move simulations and Monte Carlo P10/P50/P90. Features comprehensive input validation and runtime guardrails.
-   **Optimization & Recommendations**: Constrained multi-objective optimization and an automated recommendations engine.
-   **AI Copilot System**: Multi-Agent Fund Flow Copilot with a Router/Orchestrator Agent, Company Knowledge Base (CKB) for context, structured responses, and multi-LLM integration. Includes a Real-Time Simulation Copilot for context-aware prompts and narrative summaries. Provides consultant-grade, data-backed recommendations with a strategic persona, a Decision Summary, and a Narrative Strategic Briefing.
-   **Fundraising OS**: Cap table management, dilution calculations, fundraising round tracking, and an Investor Room. Features full equity management with shareholder registry, equity issuance, share transfers, option grants, transaction audit log, 409A valuation tracking, dilution scenario modeling, and ownership visualization.
-   **Forecasting & Alerts**: Holt-Winters exponential smoothing, linear regression for forecasting, Z-score anomaly detection, threshold monitoring, and runway warnings.
-   **Data Connectors**: Framework for payroll & ERP connectors, with 37 production data connectors. Implemented QuickBooks Online, Stripe, and Gusto connectors.
-   **Enhanced AI Interaction**: Copilot Trust Module for data veracity, natural conversational AI, and web research capabilities for market benchmarks. AI insights include disclaimers, collapsible sources, and data currency footers.
-   **Simulation Experience Upgrade**: Before/After Delta Cards, Payback Clock Widget, Risk Alert Banner, data-driven recommendations (GO/CONDITIONAL/NO-GO), second-order effects detection, and confidence scoring.
-   **User Roles**: Platform Admin and Company Level Roles (`owner`, `admin`, `analyst`, `viewer`).
-   **Onboarding Wizard**: 3-step wizard (Welcome → Connect Data → First Insight) with visual progress and localStorage tracking.
-   **User Management**: Password reset flow and email verification on signup.
-   **In-App Feedback Widget**: Floating button for submitting bugs, features, or general feedback.
-   **Help & Documentation Page**: Collapsible sections for Getting Started, Simulation Engine, AI Copilot, and Integrations guides.
-   **Analytics**: PostHog analytics for page views, user identification, and custom events.
-   **API Rate Limiting**: Monte Carlo simulation endpoints are rate-limited to 10 req/min per IP.
-   **Request ID Tracing**: Unique `X-Request-ID` header for every request for tracing.
-   **Board Deck Export**: Generate AI-powered board deck presentations (Monthly Update, Fundraising Prep, Scenario Analysis) with PDF download. Backend: `server/api/board_export.py`. Frontend: `client/src/components/board-export/`. Export button on Dashboard and Scenarios pages.
-   **Hiring Planner**: Plan hires by role/department/location with salary modeling, cost summaries, runway impact analysis, and Monte Carlo simulation. Backend: `server/api/hiring_planner.py` (data in `metadata_json["hiring_plans"]`). Frontend: `client/src/pages/hiring-planner.tsx`. Sidebar route: `/hiring-planner`.
-   **Fundraising Readiness Score**: Weighted scoring system (Runway 25%, Growth 25%, Unit Economics 20%, Market 15%, Narrative 15%) with radar chart, recommendations, raise window timeline, and AI-generated investment one-pager. Backend: `server/api/fundraising_readiness.py`. Frontend: `client/src/components/fundraising/` + Readiness tab in `/fundraising`.
-   **Smart Alerts Enhancement**: Automated metric monitoring (Burn Spike, MRR Drop, Churn Spike, Runway Warning/Caution, Growth Slowdown) with severity-based filtering, alert acknowledgment, custom rules, weekly AI briefings via email, and notification bell in sidebar. Backend: `server/api/smart_alerts.py` (data in `metadata_json["smart_alerts"]`). Frontend: enhanced `client/src/pages/alerts.tsx`.

## External Dependencies

-   **OpenAI**: Financial analysis, metrics extraction, vision tasks.
-   **Anthropic**: Complex reasoning, coding, strategy.
-   **Google Gemini**: General chat, high-volume tasks.
-   **Perplexity**: Real-time web search, market research, benchmark data.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.
-   **Twilio**: SMS/phone notifications.
-   **Google OAuth**: Social login.