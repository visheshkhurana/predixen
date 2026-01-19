# Predixen Intelligence OS

## Overview
Predixen Intelligence OS is an AI-powered financial intelligence platform for startups. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to guide startups through financial planning. The platform's core functionality revolves around a flow of Truth (data validation and benchmarking), Simulation (probabilistic forecasting), Decision (actionable recommendations), and Copilot (AI-assisted guidance). Its primary purpose is to help startups understand their financial health, predict future outcomes, and make informed strategic decisions to maximize survival and growth while minimizing downside risk and dilution.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform is built on a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations. Key architectural decisions include:
- **Modular Design**: Separation of concerns with distinct modules for ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities.
- **Scalability**: FastAPI and PostgreSQL provide a robust and scalable backend.
- **User Experience**: Intuitive UI/UX with a focus on data visualization, interactive components, and actionable insights. Tailwind CSS and shadcn/ui are used for consistent styling and component design.
- **Data Integrity**: Strong data validation using Zod and Pydantic, along with Alembic for database migrations.
- **Security**: JWT-based authentication and role-based access control (RBAC) ensure secure access and operations.

### Frontend Architecture
- **Frameworks**: React 18 with TypeScript, Wouter for routing, Zustand for state management, TanStack React Query for server state.
- **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui (built on Radix UI), Recharts for advanced data visualization (survival curves, distributions).
- **Forms**: React Hook Form with Zod validation.
- **Build Tool**: Vite.
- **Key UI Components**:
    - **Executive Summary**: Best scenario analysis, runway, key recommendations.
    - **RiskGauge/TrafficLight**: Visual risk indicators.
    - **ProjectionChart**: Interactive month-by-month projections with milestones, benchmarks, and brush zoom.
    - **DrillDownChart**: Zoom/pan capability, metric switching, benchmark overlays.
    - **ScenarioCard**: Interactive expandable cards with mini-charts.
    - **GlossaryModal**: Definitions of financial terms.

### Backend Architecture
- **Framework**: FastAPI (Python 3.11).
- **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
- **Authentication**: JWT-based with bcrypt.
- **Validation**: Pydantic models.
- **Asynchronous Tasks**: FastAPI BackgroundTasks.

### Key Features and Technical Implementations
1.  **Ingestion**: CSV upload, manual baseline, and AI-powered extraction from Excel/PDF using OpenAI.
2.  **Truth Scan**: Computes 24 financial metrics, benchmarks against industry data, and assigns confidence scores.
3.  **Simulation Engine**: Monte Carlo simulations with 24-month projections.
    -   **Regime-aware Simulation**: Base, Downturn, and Breakout regimes with correlated driver sampling (growth_rate, churn_rate, gross_margin, CAC, DSO, conversion_rate) using Cholesky decomposition.
    -   **Scenario Events**: Supports 8 event types (e.g., pricing change, fundraise) with configurable probabilities and timing.
    -   **Decision Scoring**: Weighted composite score for ranked recommendations (survival, growth, downside risk, dilution, complexity).
    -   **Sensitivity Analysis**: "What Must Be True" driver impact analysis for target runway.
4.  **Decision Engine**: Generates and ranks top 3 deterministic action recommendations.
5.  **Copilot**: Multi-agent router with context pack grounding for AI assistance.
6.  **Forecasting**: Holt-Winters exponential smoothing, linear regression.
7.  **Alerts**: Z-score anomaly detection, threshold monitoring, runway warnings.
8.  **Admin Dashboard**: Centralized management for users, companies, billing, platform metrics, and audit logs with RBAC.

### User Roles
- `owner`, `admin`: Full platform access including admin dashboard.
- `analyst`: Standard platform access.
- `viewer`: Read-only standard platform access.

### Project Structure (High-Level)
- `client/`: React frontend (components, pages, state management, API hooks).
- `server/`: FastAPI backend (main app, core services, database models, API routes, specific engines for truth, simulate, decision, copilot).
- `shared/`: Shared types.

## External Dependencies

-   **OpenAI**: Used for AI extraction of financial metrics from Excel/PDF documents.
-   **PostgreSQL**: Primary relational database for all application data.
-   **QuickBooks/Xero**: Planned integrations for accounting data synchronization.
-   **Salesforce/HubSpot**: Planned integrations for CRM data synchronization.
-   **Google Fonts**: Inter (primary font), IBM Plex Mono (for financial figures).