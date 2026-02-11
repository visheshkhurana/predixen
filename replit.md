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