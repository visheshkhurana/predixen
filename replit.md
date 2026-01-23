# Predixen Intelligence OS

## Overview
Predixen Intelligence OS is an AI-powered financial intelligence platform for startups. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to guide startups through financial planning. The platform helps startups understand their financial health, predict future outcomes, and make informed strategic decisions to maximize survival and growth while minimizing downside risk and dilution.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The platform is built on a modern full-stack architecture with React/TypeScript for the frontend and FastAPI/Python for the backend. It emphasizes data-driven insights, probabilistic modeling, and AI-powered recommendations through a modular design for ingestion, truth scanning, simulation, decision-making, and AI copilot functionalities. Scalability is ensured with FastAPI and PostgreSQL. UI/UX focuses on data visualization and interactive components, using Tailwind CSS and shadcn/ui. Data integrity is maintained with Zod, Pydantic, and Alembic, while security relies on JWT-based authentication and RBAC.

### Frontend Architecture
-   **Frameworks**: React 18 with TypeScript, Wouter for routing, Zustand for state management, TanStack React Query for server state.
-   **UI/UX**: Tailwind CSS (dark mode default), shadcn/ui, Recharts for data visualization.
-   **Forms**: React Hook Form with Zod validation.
-   **Build Tool**: Vite.

### Backend Architecture
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations.
-   **Authentication**: JWT-based.
-   **Validation**: Pydantic models.

### Key Features and Technical Implementations
1.  **Data Ingestion**: Supports CSV upload, manual baseline entry, and AI-powered extraction from Excel/PDFs using OpenAI, with a two-stage PDF extraction process including Vision fallback for scanned documents.
2.  **Truth Scan**: Computes 24 financial metrics, benchmarks against industry data, and assigns confidence scores.
3.  **Simulation Engine**: Enhanced Monte Carlo simulations with 24-month projections, supporting various probability distributions, configurable iterations, and asynchronous job execution. It includes regime-aware simulations (Base, Downturn, Breakout) and custom event modeling with conditional triggering.
4.  **Sensitivity Analysis**: Generates data for tornado charts by performing One-At-a-Time (OAT) perturbation to identify key drivers impacting runway.
5.  **Scenario Versioning**: Provides full version control for scenarios, including macro-economic modifiers (optimistic, neutral, pessimistic, stagflation, boom) and API endpoints for managing presets.
6.  **Constrained Multi-Objective Optimization**: An advanced optimizer that handles constraints on key financial metrics (e.g., runway, survival, cash) and uses a weighted composite score for multi-objective decision-making.
7.  **Automated Recommendations Engine**: Generates health-based recommendations (e.g., reduce burn, fundraise) based on predefined thresholds for financial health indicators like runway and survival probability. It also includes version history, diff views, and rollback capabilities for scenarios.
8.  **Multi-Agent Fund Flow Copilot V2+**: A production-ready AI system featuring a Router/Orchestrator Agent that routes queries to specialized agents (CFO, Market, Strategy). It maintains a Company Knowledge Base (CKB) for persistent context, provides structured responses with truth-first citations, and includes data health scoring, operating cadence management, and automated alerts. The copilot now uses multi-LLM integration with task-specific model selection:
    - CFO Agent: GPT-4o for financial analysis (best at structured data)
    - Market Agent: Claude Sonnet for market research (balanced reasoning)
    - Strategy Agent: Claude Sonnet for strategic planning
    - Router Agent: Gemini Flash for orchestration and response synthesis
9.  **Copilot V6: Fundraising OS**: A comprehensive fundraising module with cap table management (common, preferred shares, option pools, convertible notes), a cap table engine for dilution calculations, fundraising round tracking, and a dilution simulator. It also includes an Investor Room for generating investor materials and managing an investor pipeline.
10. **Forecasting**: Utilizes Holt-Winters exponential smoothing and linear regression.
11. **Alerts**: Implements Z-score anomaly detection, threshold monitoring, and runway warnings.
12. **Admin Dashboard**: Centralized management for users, companies, billing, and platform metrics with RBAC, accessible only by the platform admin.
13. **Payroll & ERP Connector Framework**: An extensible system for syncing financial data from Indian payroll and ERP providers (e.g., RazorpayX Payroll, GreytHR, Zoho Books, Tally ERP) with a `BaseConnector` and `ConnectorRegistry` for various authentication types and data normalization.
14. **Feature Notification System**: Automated email notifications for platform changes and updates, delivered via Resend, with predefined recipients and professional HTML templates.
15. **Multi-LLM Router**: Unified interface for intelligent task-based model selection across multiple AI providers (OpenAI GPT-4o, Anthropic Claude, Google Gemini). It features intelligent task routing to optimal models, graceful fallback mechanisms, feature-aware routing for specific requests (e.g., JSON mode), PII redaction, and audit logging.

### User Roles
-   **Platform Admin**: Application owner with access to the Admin dashboard.
-   **Company Level Roles**: `owner`, `admin`, `analyst`, `viewer` with varying access levels to company data.

## External Dependencies

-   **OpenAI**: GPT-4o for financial analysis, metrics extraction, vision tasks (via Replit AI Integrations).
-   **Anthropic**: Claude Opus/Sonnet/Haiku for complex reasoning, coding, strategy (via Replit AI Integrations).
-   **Google Gemini**: Gemini 2.5/3 Flash/Pro for general chat, high-volume tasks (via Replit AI Integrations).
-   **PostgreSQL**: Primary relational database.
-   **Google Fonts**: Inter, IBM Plex Mono.
-   **Resend**: Email delivery service.