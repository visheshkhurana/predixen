# Predixen Intelligence OS

## Overview

Predixen Intelligence OS is an AI-powered financial intelligence platform for startups that merges investor-grade diligence (Truth Scan + benchmarks + data validation) with probabilistic simulation and ranked decision recommendations. The platform follows the flow: Truth → Simulation → Decision → Copilot.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight React router)
- **State Management**: Zustand for global state, TanStack React Query for server state
- **Styling**: Tailwind CSS with dark mode default
- **UI Components**: shadcn/ui component library built on Radix UI primitives
- **Charts**: Recharts for data visualization (survival curves, bands, distributions)
- **Forms**: React Hook Form with Zod validation
- **Build Tool**: Vite with hot module replacement

### Backend Architecture
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic for database migrations
- **Auth**: JWT-based authentication with bcrypt password hashing
- **Validation**: Pydantic models for request/response validation
- **Jobs**: FastAPI BackgroundTasks for async operations

### Key Modules
1. **Ingestion**: CSV upload + manual baseline fallback + Excel/PDF AI extraction
2. **Truth Scan**: 24 metrics computation, benchmarking, confidence scoring
3. **Simulation**: Monte Carlo engine with 24-month projections
   - **Enhanced Engine**: Regime-aware simulation (Base, Downturn, Breakout) with correlated driver sampling
   - **Correlated Drivers**: growth_rate, churn_rate, gross_margin, CAC, DSO, conversion_rate using Cholesky decomposition
   - **Scenario Events**: 8 event types (pricing_change, cost_cut, hiring_freeze, hiring_plan, fundraise, marketing_spend_change, churn_initiative, expansion_revenue)
   - **Decision Scoring**: Weighted composite (survival 30%, growth 25%, downside risk 20%, dilution 15%, complexity 10%)
   - **Sensitivity Analysis**: "What Must Be True" driver impact analysis for target runway
4. **Decision Engine**: Deterministic action library, scoring, top 3 recommendations
5. **Copilot**: Multi-agent router with context pack grounding
6. **Forecasting**: Holt-Winters exponential smoothing, linear regression, trend detection
7. **Alerts**: Z-score anomaly detection, threshold monitoring, runway warnings, covenant checks
8. **Integrations**: Framework for QuickBooks/Xero (accounting) and Salesforce/HubSpot (CRM)
9. **Scenario Templates**: 7 pre-built templates (Baseline, Conservative Cut, Aggressive Growth, etc.)
10. **Enhanced UX Components**:
    - **ExecutiveSummary**: Best scenario analysis, runway range display, key recommendations
    - **RiskGauge/TrafficLight**: Visual risk indicators with color-coded survival probability
    - **ScenarioCard**: Interactive expandable cards with mini-charts and assumptions
    - **DrillDownChart**: Zoom/pan capability, metric switching (cash/revenue/burn/runway), benchmark overlays
    - **StackedBurnRevenueChart**: Revenue vs burn visualization with break-even detection
    - **GlossaryModal**: 13 financial term definitions with search and category filtering
    - **ProjectionChart**: Month-by-month interactive visualization with toggleable series (cash/burn/revenue/runway/headcount), custom tooltips, milestone markers (funding events, break-even, runway exhaustion), benchmark overlays, and brush zoom
    - **ProjectionSummary**: Key statistics panel showing peak/lowest cash, total revenue, average burn/revenue, break-even detection, runway at key intervals (3, 6, 12 months, end)
11. **Recommendations Engine**: POST /companies/{id}/recommendations - prioritized action recommendations based on runway gaps and survival rate vs benchmarks

### Data Import Workflow
- **Excel/PDF Import**: Uses OpenAI to extract financial metrics from Termina/Tribe Capital reports
- **Editable Preview**: Extracted metrics shown in editable form for user verification before saving
- **Apply to Financials**: User must explicitly click "Apply to Financials" button to save extracted data
- **Validation**: Warnings shown for missing required fields (Revenue, Cash Balance)
- **Data Flow**: File upload → AI extraction → Preview with edit → Apply → Save to FinancialRecord → Run Truth Scan

### Feature Flags
- `FEATURE_INVESTOR_MODE`: When false (default), investor routes return 403 and UI hides investor navigation

### Project Structure
\`\`\`
├── client/src/          # React frontend
│   ├── components/      # UI components
│   ├── pages/           # Route pages
│   ├── store/           # Zustand stores
│   ├── api/             # API hooks and client
│   └── lib/             # Utilities
├── server/              # FastAPI backend
│   ├── main.py          # FastAPI app entry
│   ├── core/            # Config, DB, security
│   ├── models/          # SQLAlchemy models
│   ├── api/             # API route handlers
│   ├── ingest/          # CSV parsing
│   ├── truth/           # Truth scan engine
│   ├── simulate/        # Monte Carlo simulation
│   ├── decision/        # Decision engine
│   ├── copilot/         # Context pack + router
│   └── seed/            # Benchmark seeding
└── shared/              # Shared types
\`\`\`

## Database Schema

### Core Tables
- users (id, email, password_hash, created_at)
- companies (id, user_id, name, website, industry, stage, currency, created_at)
- datasets (id, company_id, type, file_name, row_count, created_at)
- financial_records, transaction_records, customer_records

### Analytics Tables
- benchmarks (seeded with SaaS industry benchmarks)
- truth_scans (outputs_json stores computed metrics)
- scenarios, simulation_runs (Monte Carlo outputs)
- decisions (recommended_actions_json)
- chat_sessions, chat_messages

## API Endpoints

### Auth
- POST /auth/register
- POST /auth/login

### Companies
- POST/GET /companies
- GET /companies/{id}

### Datasets
- POST /companies/{id}/datasets/upload
- POST /companies/{id}/datasets/manual_baseline

### Truth Scan
- POST /companies/{id}/truth/run
- GET /companies/{id}/truth/latest

### Simulation
- POST /companies/{id}/scenarios
- POST /scenarios/{id}/simulate
- GET /scenarios/{id}/simulation/latest
- POST /companies/{id}/simulate-enhanced (regime-aware single scenario)
- POST /companies/{id}/simulate-scenarios-enhanced (multi-scenario with ranking)
- POST /companies/{id}/sensitivity-analysis (driver impact analysis)
- GET /scenarios/{scenario_id}/timeseries (month-by-month projection data with funding events)

### Decisions
- POST /simulation/{run_id}/decisions/generate
- GET /companies/{id}/decisions/latest

### Copilot
- GET /companies/{id}/context
- POST /companies/{id}/simulate
- POST /companies/{id}/decision/compare

### Forecasting
- POST /forecasting/companies/{id}/forecast
- POST /forecasting/trend/analyze

### Alerts
- GET /alerts/companies/{id}/alerts
- POST /alerts/companies/{id}/analyze

### Integrations
- GET /integrations/available
- POST /integrations/companies/{id}/{type}/connect
- POST /integrations/companies/{id}/{type}/sync

### Templates
- GET /templates/
- GET /templates/{id}
- POST /templates/companies/{id}/apply/{template_id}
- POST /templates/companies/{id}/bulk-apply

## Running the Application

Development server runs on port 5000:
- Frontend: Vite dev server with proxy to backend
- Backend: FastAPI with uvicorn

## Fonts
- Google Fonts: Inter (primary), IBM Plex Mono (financial figures)
