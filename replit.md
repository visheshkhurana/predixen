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
12. **Admin Dashboard**: Centralized admin interface for super-admins
    - **User Management**: View, edit roles (owner/admin/analyst/viewer), suspend/activate users
    - **Company Management**: View all companies with metadata and statistics
    - **Billing Management**: Subscription tracking (plan, status, seats, MRR)
    - **Platform Metrics**: Aggregated KPIs, charts (users by role, companies by stage)
    - **Audit Logs**: Track admin actions for compliance
    - **RBAC**: Role-based access control on both frontend and backend

### Data Import Workflow
- **Excel/PDF Import**: Uses OpenAI to extract financial metrics from Termina/Tribe Capital reports
- **Editable Preview**: Extracted metrics shown in editable form for user verification before saving
- **Apply to Financials**: User must explicitly click "Apply to Financials" button to save extracted data
- **Validation**: Warnings shown for missing required fields (Revenue, Cash Balance)
- **Data Flow**: File upload → AI extraction → Preview with edit → Apply → Save to FinancialRecord → Run Truth Scan

### Feature Flags
- `FEATURE_INVESTOR_MODE`: When false (default), investor routes return 403 and UI hides investor navigation

### User Roles
- `owner`: Full platform access including admin dashboard
- `admin`: Full platform access including admin dashboard
- `analyst`: Standard platform access, no admin
- `viewer`: Standard platform access, no admin (default for new users)

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

## Recent UX/UI Improvements (January 2026)

### Overview Page
- Added tooltips to all metrics (runway, burn, growth, margin) with calculation formulas and good/bad ranges
- Added HoverCards to Quality of Growth Index and Data Confidence Score explaining how they're calculated

### Data Input
- Added inline validation (founding date cannot be in future, employee count must be positive)
- Added sample file format guides for PDF/Excel uploads
- Added real-time Net Burn and Runway calculations with color-coded runway warnings
- Added expense breakdown visualization bar chart

### Truth Scan
- Added BenchmarkBar component with visual quartile indicators and gradient backgrounds
- Added quartile status badges (Top Quartile, Above Median, Below Median, Bottom Quartile)
- Added PDF/CSV export functionality via ExportButton component
- Added collapsible explanations for composite scores with actionable improvement steps

### Templates
- Added expected impact metadata (runway change, burn change, risk level) on template cards
- Added confirmation modal before applying templates
- Added category icons and grouping

### Scenario Builder
- Added Skip Tutorial button with localStorage preference saving (`predixen_scenario_tutorial_dismissed`)
- Added quick-create baseline scenario option when no scenarios exist
- Added disabled tabs with lock icons until scenarios are run (with toast notifications)

### Decision Recommendations
- Added expandable details section (time horizon, dependencies, risk factors)
- Added change highlighting on regeneration (New/Updated badges)
- Added decision status tracking (Adopted/Deferred/Rejected) persisted to localStorage

### Copilot
- Converted to chat interface with auto-scroll and conversation history
- Fixed example prompts to show full text and auto-trigger responses on click
- Added data provenance badges showing which data sources (Truth Scan, Simulation, Scenario, Benchmark) were used

### Alerts & Monitoring
- Added Health Dashboard tab with traffic light indicators (green/amber/red)
- Added sparkline trends for metrics with historical data
- Added threshold configuration modal for custom alert rules
- Added Unknown status explanation with CTAs to load data

### Integrations
- Added multi-step connection flow modals (benefits, OAuth simulation, credentials)
- Added sync status display (last sync time, record counts)
- Added Sync Now button with loading state
- Added new integration placeholders: NetSuite, Pipedrive, Zoho CRM (marked "Coming Soon")

### General
- Added robust loading skeletons across pages (alerts, owner-console, data-verification, templates)
- Added Help & Docs link in sidebar footer
- Improved responsiveness with flex-wrap and proper gap spacing

### LocalStorage Keys
- `predixen_scenario_tutorial_dismissed`: Tutorial preference for Scenario Builder
- `decision_statuses_{companyId}`: Decision status tracking per company
- `previous_recommendations_{companyId}`: Previous recommendations for change detection
