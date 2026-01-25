# Predixen Intelligence OS

## Overview

Predixen Intelligence OS is an AI-powered financial intelligence platform designed for startups. It provides investor-grade diligence, probabilistic simulation, and ranked decision recommendations to help founders make data-driven financial decisions.

The platform enables startups to:
- Upload and extract financial data from PDFs, Excel files, and CSVs
- Run Monte Carlo simulations with configurable parameters
- Receive AI-powered strategic recommendations from specialized agents
- Manage cap tables and fundraising scenarios
- Monitor financial health with automated alerts and benchmarking

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript, bundled with Vite
- **Routing**: Wouter for client-side navigation
- **State Management**: Zustand for local state, TanStack React Query for server state
- **UI Components**: shadcn/ui built on Radix UI primitives with Tailwind CSS
- **Styling**: Dark mode default with electric teal accents, Inter font family
- **Forms**: React Hook Form with Zod validation
- **Charts**: Recharts for data visualization

### Backend Architecture
- **Gateway Server**: Express (Node.js) serves the frontend and proxies `/api` requests to FastAPI
- **API Server**: FastAPI (Python) handles all business logic
- **Process Management**: Node spawns uvicorn as a child process with graceful shutdown handling (SIGTERM/SIGINT/SIGHUP) and automatic restart with exponential backoff (max 5 attempts)
- **Validation**: Pydantic models for request/response validation
- **Authentication**: JWT-based authentication

### Database
- **Database**: PostgreSQL
- **ORM**: Drizzle ORM with schema defined in `shared/schema.ts`
- **Migrations**: Drizzle Kit for schema migrations (output to `./migrations`)

### Multi-Agent AI System
The platform uses a multi-agent architecture with specialized AI agents:
- **Router/Orchestrator Agent**: Gemini Flash for query routing and response synthesis
- **CFO Agent**: GPT-4o for financial analysis and structured data processing
- **Market Agent**: Claude Sonnet for market research and competitor analysis
- **Strategy Agent**: Claude Sonnet for strategic planning and recommendations

### Key Technical Features
- **Data Ingestion**: Supports CSV, Excel, and PDF uploads with AI-powered extraction (includes Vision fallback for scanned documents)
- **Monte Carlo Simulation**: 24-month projections with configurable iterations and multiple probability distributions
- **Sensitivity Analysis**: One-At-a-Time (OAT) perturbation for tornado charts
- **Scenario Versioning**: Full version control with macro-economic modifiers (optimistic, neutral, pessimistic, stagflation, boom)
- **Automated Recommendations**: Health-based recommendations triggered by financial metric thresholds

### Production Configuration
- **CORS**: Environment-driven origins via `CORS_ORIGINS` (defaults to localhost in dev, empty in prod)
- **Database Initialization**: Schema creation, migrations, and seeding controlled by environment variables (`CREATE_SCHEMA`, `RUN_MIGRATIONS`, `SEED_BENCHMARKS`, `SEED_DEMO_DATA`) - default true in dev, false in prod
- **Health Endpoints**: `/health` on both Node gateway and FastAPI for monitoring

## External Dependencies

### AI/ML Services
- **OpenAI**: GPT-4o for CFO agent and document extraction
- **Anthropic**: Claude Sonnet for Market and Strategy agents
- **Google Generative AI**: Gemini Flash for router/orchestrator agent

### Database
- **PostgreSQL**: Primary data store (requires `DATABASE_URL` environment variable)

### Frontend Libraries
- **Radix UI**: Headless UI component primitives
- **TanStack React Query**: Server state management
- **Recharts**: Data visualization
- **date-fns**: Date manipulation

### Development Tools
- **Vite**: Frontend build tool with HMR
- **Drizzle Kit**: Database migrations
- **tsx**: TypeScript execution for Node.js
- **Tailwind CSS**: Utility-first CSS framework