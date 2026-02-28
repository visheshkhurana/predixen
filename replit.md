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

## External Dependencies

-   **OpenAI**: For financial analysis, metrics extraction, and vision tasks.
-   **Anthropic**: For complex reasoning, coding, and strategy.
-   **Google Gemini**: For general chat and high-volume tasks.
-   **Perplexity**: For real-time web search, market research, and benchmark data in the copilot.
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.
-   **Twilio**: SMS/phone notifications.
-   **Google OAuth**: Social login.
-   **GitHub OAuth**: Social login.