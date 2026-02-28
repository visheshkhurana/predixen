# FounderConsole

## Overview
FounderConsole is an AI-powered financial intelligence platform for startups, designed to enhance survival and growth while mitigating risk and dilution. It provides investor-grade diligence, probabilistic simulations, and ranked decision recommendations to support financial planning, helping startups understand financial health, predict outcomes, and make strategic decisions. The platform aims to revolutionize how startups manage their finances and interact with investors.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform uses a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design. Key architectural components include data ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is achieved using FastAPI and PostgreSQL, while UI/UX focuses on data visualization and interactive components built with Tailwind CSS and shadcn/ui. Data integrity is enforced via Zod, Pydantic, and Alembic, with security based on JWT authentication and RBAC.

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
1.  **Data Management**: Supports CSV upload, manual entry, AI-powered extraction, and multi-currency handling.
2.  **Truth Scan**: A multi-stage data validation layer ensuring data quality.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, asynchronous execution, custom event modeling, sensitivity analysis, and scenario versioning. Includes automatic counter-move simulations and Monte Carlo P10/P50/P90.
4.  **Optimization & Recommendations**: Features constrained multi-objective optimization and an automated recommendations engine.
5.  **AI Copilot System**: A Multi-Agent Fund Flow Copilot with a Router/Orchestrator Agent directing queries to specialized agents. Uses a Company Knowledge Base (CKB) for context, provides structured responses, and integrates multi-LLM for task-specific model selection.
6.  **Real-Time Simulation Copilot**: AI guidance integrated into the simulation workflow, offering context-aware prompts and narrative summaries.
7.  **Fundraising OS**: Module for cap table management, dilution calculations, fundraising round tracking, and an Investor Room. Features full equity management with shareholder registry, equity issuance, share transfers, option grants, transaction audit log, 409A valuation tracking, dilution scenario modeling, and ownership visualization.
8.  **Forecasting & Alerts**: Utilizes Holt-Winters exponential smoothing and linear regression for forecasting, and Z-score anomaly detection, threshold monitoring, and runway warnings for alerts.
9.  **Data Connectors**: Framework for payroll & ERP connectors and 37 production data connectors across financial and operational categories.
10. **Enhanced AI Interaction**: Includes a Copilot Trust Module for data veracity, natural conversational AI, and web research capabilities for market benchmarks.
11. **Consultant-Grade Copilot Persona**: System prompts are upgraded to provide structured, data-backed recommendations with a strategic persona.
12. **Simulation Experience Upgrade**: Features Before/After Delta Cards, Payback Clock Widget, Risk Alert Banner, data-driven recommendations (GO/CONDITIONAL/NO-GO), second-order effects detection, and confidence scoring.
13. **AI Decision Summary**: Provides a 1-2 sentence recommendation, Decision Score, verdict, and supporting bullet points, with burn-increase verdict overrides.
14. **Narrative Strategic Briefing**: Transforms the Decisions page into a 5-section strategic briefing: Executive Summary, Key Metrics Overview, Risk Assessment, Recommended Actions, and Upcoming Milestones.
15. **User Roles**: Platform Admin and Company Level Roles (`owner`, `admin`, `analyst`, `viewer`).
16. **Phased Startup**: Critical routes (auth, billing, onboarding) register quickly, with other modules loading in the background.

17. **Simulator Edge Case Guardrails**: Comprehensive input validation on both frontend (Zod) and backend (Pydantic). Hiring plan: count 0-500, monthly cost 0-$1M, max 20 roles. Scenario inputs: growth -30% to +50%, pricing -50% to +100%, burn reduction -100% to +80%, fundraise $0-$100M within months 1-24. Runtime: baseline revenue/cash floored at 0, negative costs floored at 0, revenue never goes negative in Monte Carlo loop. Simulation iterations bounded 100-10,000.
18. **Onboarding Wizard**: 3-step wizard (Welcome → Connect Data → First Insight) with visual progress bar, localStorage completion tracking (`founderConsoleOnboardingComplete`), and "Recommended" badge on manual entry. Step 3 shows computed metrics (runway, burn, health) and Run Simulation CTA.
19. **AI Copilot Disclaimers**: Amber disclaimer banner ("AI insights are informational only"), collapsible Sources section after each response showing citations/data sources used, and "Based on data as of [date]" footer on each response.
20. **Enhanced Empty States**: Dashboard shows ghost metric cards with descriptive helper text when no data exists, tooltips on N/A values explaining what's needed. Scenarios page has descriptive empty state with CTA. Cap Table and Fundraising pages have existing comprehensive empty states.
21. **Password Reset Flow**: Full forgot-password modal on auth page → email with reset link via Resend → `/reset-password?token=xxx` page to set new password. Uses `PasswordResetToken` model with 1-hour expiry. Forgot-password endpoint rate-limited under AUTH_PATHS (5/min).
22. **Email Verification on Signup**: New users get `is_email_verified=false`, auto-sent verification email on register. Dashboard shows amber banner with "Resend Verification" button. `/verify-email?token=xxx` page verifies and updates Zustand store. Uses `EmailVerificationToken` model with 24-hour expiry. OAuth users default to verified.
23. **Integrations Coming Soon Separation**: Active connectors shown first, then "Upcoming Integrations" section with "In Development" badge and "Request Access" button (shows toast confirmation). Filtered by `comingSoon` property.
24. **Simulation API Rate Limiting**: Monte Carlo simulation endpoints (`/api/simulations`, `/api/scenarios/*/simulate`) rate-limited to 10 req/min per IP. Returns 429 with `Retry-After` header. Configurable via `RATE_LIMIT_SIMULATION` env var.

## External Dependencies

-   **OpenAI**: For financial analysis, metrics extraction, and vision tasks.
-   **Anthropic**: For complex reasoning, coding, and strategy.
-   **Google Gemini**: For general chat and high-volume tasks.
-   **Perplexity**: For real-time web search, market research, and benchmark data in the copilot.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.
-   **Twilio**: SMS/phone notifications.
-   **Google OAuth**: Social login (GitHub OAuth removed for launch).