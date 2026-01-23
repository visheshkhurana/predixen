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
    -   **Two-Stage PDF Extraction**: Text extraction with pdfplumber + GPT-4o analysis, with automatic fallback to OpenAI Vision for scanned/image-based PDFs.
    -   **Vision Fallback**: PDF pages converted to images and analyzed by GPT-4o vision when text extraction fails or produces insufficient content.
2.  **Truth Scan**: Computes 24 financial metrics, benchmarks against industry data, and assigns confidence scores.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections.
    -   **Distribution-Aware Simulation**: Supports fixed, normal, lognormal, uniform, triangular, and discrete probability distributions for event impacts.
    -   **Configurable Iterations**: 100 to 10,000 iterations with configurable confidence intervals (P10/P25/P50/P75/P90).
    -   **Async Job Execution**: Background job processing with progress tracking via `/api/simulations/run` and `/api/simulations/jobs/{id}`.
    -   **Regime-aware Simulation**: Base, Downturn, and Breakout regimes with correlated driver sampling.
    -   **Custom Events**: 12 event types with probability-weighted impacts on revenue, costs, growth, churn, margin, headcount, and cash.
    -   **Event Conditions**: Conditional event triggering based on metric thresholds.
4.  **Sensitivity Analysis**: Tornado chart data generation via `/api/simulations/sensitivity`.
    -   **Parameter Sweeps**: Analyze impact of varying parameters on runway.
    -   **Ranked Drivers**: Top drivers sorted by impact magnitude.
    -   **Visual Insights**: TornadoChart and SensitivityPanel UI components.
5.  **Scenario Versioning**: Full version control for scenarios via `/api/simulations/versions`.
    -   **Version History**: Create, list, and restore scenario versions.
    -   **Diff View**: Compare changes between versions (inputs, events, tags).
    -   **Rollback**: Restore to any previous version with audit trail.
6.  **Decision Scoring**: Weighted composite score for ranked recommendations (survival, growth, downside risk, dilution, complexity).
7.  **Decision Engine**: Generates and ranks top 3 deterministic action recommendations.
8.  **Multi-Agent Fund Flow Copilot V2+**: Production-ready AI system with specialized agents and enhanced features.
    -   **Router/Orchestrator Agent**: Analyzes incoming queries and routes to appropriate specialist agents.
    -   **CFO Agent**: Financial analysis, metrics extraction, FX conversion (INR, EUR, GBP, CAD, AUD, JPY, CNY), and runway optimization.
    -   **Market Agent**: Competitor analysis, ICP definition, target customer segmentation, and industry benchmarks (SaaS, Fintech, Marketplace, E-commerce, AgTech).
    -   **Strategy Agent**: Business strategy, GTM planning, vertical expansion, and 30/60/90 day execution plans.
    -   **Company Knowledge Base (CKB)**: Persistent context storage per company in `metadata_json` column, maintains: overview, financials, market, strategy, ICP, competitors, risks, decisions_made.
    -   **API Endpoints**: `/companies/{company_id}/chat` for chat, `/companies/{company_id}/ckb` for CKB management.
    -   **Structured Responses**: Each agent returns findings, assumptions, risks, next_questions, and confidence levels.
    -   **Truth-First Citations**: Source tracking from PDFs and web sources with highlighted claims.
    -   **Data Health Scoring**: 0-100 score with grades A-F based on data completeness (P&L, cash, unit economics) and consistency.
    -   **Operating Cadence**: Workstreams API for weekly metrics, monthly board memos, quarterly strategy reviews with configurable KPIs.
    -   **Automated Alerts**: Rule-based alerts for runway <9mo, revenue decline >10%, CAC spike >15%.
    -   **Driver-Based Forecasting**: Templates for SaaS, marketplace, and services models with 12-month projections.
9.  **Copilot V6: Fundraising OS**: Comprehensive fundraising management module.
    -   **Cap Table Management**: Database models for cap tables with common shares, preferred shares, option pools, and convertible notes.
    -   **Cap Table Engine**: Pure Python functions for dilution calculations including `compute_fully_diluted`, `apply_equity_round`, `apply_safe_or_note`, `compute_ownership_summary`, and `simulate_round_scenarios`.
    -   **Fundraising Rounds**: Track rounds with name, target raise, pre/post-money valuations, instrument type (equity/SAFE/note), and option pool refresh.
    -   **Dilution Simulator**: Model the impact of fundraising rounds on ownership with multi-scenario comparison.
    -   **Investor Room**: Automated generation of investor materials including markdown investor memo, stage-aware data room checklist (Legal, Finance, Team, Product, GTM categories), KPI snapshots from latest financials, and mode-specific FAQ (VC/Growth PE/Strategic).
    -   **Investor Pipeline**: Track investors through stages (cold, warm, active, term_sheet, closed) with contact info and notes.
    -   **Database Models**: `company_cap_tables`, `fundraising_rounds`, `round_terms`, `investors`, `investor_pipeline` tables.
    -   **API Endpoints**: `/companies/{id}/cap-tables`, `/companies/{id}/fundraising/rounds`, `/companies/{id}/fundraising/simulate`, `/companies/{id}/investor-room/generate`.
10. **Forecasting**: Holt-Winters exponential smoothing, linear regression.
11. **Alerts**: Z-score anomaly detection, threshold monitoring, runway warnings.
12. **Admin Dashboard**: Centralized management for users, companies, billing, platform metrics, and audit logs with RBAC.
13. **Payroll & ERP Connector Framework**: Extensible connector system for syncing financial data from Indian payroll and ERP providers.
    -   **BaseConnector**: Abstract base class for all connectors with authentication, data fetching, and normalization methods.
    -   **ConnectorRegistry**: Decorator-based registration and discovery of connector implementations.
    -   **Supported Providers**: RazorpayX Payroll, GreytHR, Keka HR, Zoho Books, Tally ERP (with additional providers coming soon).
    -   **Data Types**: EmployeeRecord, PayrollRunRecord, LedgerEntry, InvoiceRecord with normalization to internal FinancialRecord schema.
    -   **Authentication**: Supports API_KEY, OAUTH2, BASIC, and CUSTOM auth types.
    -   **API Endpoints**: `/connectors/providers`, `/connectors/companies/{id}/connect`, `/connectors/companies/{id}/sync/{provider}`, `/connectors/companies/{id}/sync-history`.
    -   **UI Integration**: Integrations page with dedicated Payroll and ERP tabs showing provider cards, connection dialogs, and sync status.
14. **Feature Notification System**: Automated email notifications for platform changes and updates.
    -   **Resend Integration**: Uses Resend API for reliable email delivery.
    -   **Recipients**: nikita@predixen.ai, vysheshk@gmail.com, and nikita.luther@gmail.com receive all feature notifications.
    -   **Professional Templates**: HTML email templates with branding, change lists, and deployment timestamps.
    -   **API Endpoint**: `POST /notifications/feature` to trigger feature update notifications.
    -   **Notification Types**: Feature updates, bug fixes, enhancements, and deployments.
    -   **IMPORTANT**: After completing any development task, ALWAYS send a notification email to both recipients summarizing the changes made. Use the notification endpoint with feature_name, description, changes array, category, and author fields.

### User Roles
**Platform Level:**
- **Platform Admin**: Only the user whose email matches `ADMIN_MASTER_EMAIL` env variable can access the Admin dashboard. This is the application owner, not a database role.

**Company Level (within the platform):**
- `owner`: Company owner with full access to their company's data.
- `admin`: Company admin with management access.
- `analyst`: Standard platform access.
- `viewer`: Read-only standard platform access.

**Security Note**: The Admin section in the sidebar is restricted to the platform owner only (checked via `is_platform_admin` flag from authentication). Regular users, even with 'owner' or 'admin' company roles, cannot see or access the admin dashboard.

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
-   **Resend**: Email delivery service for feature notifications and platform updates.