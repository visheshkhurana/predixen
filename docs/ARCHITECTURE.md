# FounderConsole Architecture

## System Overview

FounderConsole is an AI-powered financial intelligence platform for startups. It uses a layered architecture with React/TypeScript frontend, FastAPI/Python backend, PostgreSQL database, and optional Redis caching/queue layer.

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  React 18 · TypeScript · Wouter · Zustand · TanStack    │
│  Tailwind CSS · shadcn/ui · Recharts                     │
├─────────────────────────────────────────────────────────┤
│                Express Proxy (port 5000)                  │
│  Static files · API proxy → FastAPI · WebSocket bridge   │
├─────────────────────────────────────────────────────────┤
│                  FastAPI Backend (port 8001)              │
│  Auth · REST API · WebSocket · Background tasks          │
├──────────┬──────────┬──────────┬────────────────────────┤
│  Redis   │ Postgres │ Workers  │  AI Services            │
│  Cache   │ Database │ Queue    │  OpenAI · Anthropic     │
│  PubSub  │ ORM      │ Jobs     │  Gemini · Perplexity    │
└──────────┴──────────┴──────────┴────────────────────────┘
```

## Folder Structure

```
founderconsole/
├── client/                      # Frontend application
│   └── src/
│       ├── components/          # Reusable UI components
│       │   ├── app-sidebar.tsx  # Main navigation (5 core modules)
│       │   ├── ui/              # shadcn/ui primitives
│       │   └── ...
│       ├── pages/               # Route-level page components
│       ├── store/               # Zustand state management
│       ├── hooks/               # Custom React hooks
│       └── lib/                 # Utilities (queryClient, cn, etc.)
│
├── server/                      # Backend application
│   ├── main.py                  # FastAPI app factory, startup
│   ├── config.py                # Environment configuration
│   │
│   ├── core/                    # Infrastructure layer
│   │   ├── db.py                # SQLAlchemy engine & session
│   │   ├── redis_client.py      # Redis connection (graceful fallback)
│   │   ├── cache.py             # Cache get/set/delete + key builder
│   │   ├── job_queue.py         # Redis-backed job queue (4 queues)
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── migrations.py        # Runtime schema migrations
│   │
│   ├── api/                     # REST API route handlers
│   │   ├── auth.py              # JWT auth, login, register, OAuth
│   │   ├── companies.py         # Company CRUD
│   │   ├── dashboard_kpis.py    # KPI aggregation (cached)
│   │   ├── simulations.py       # Monte Carlo simulation API
│   │   ├── scenarios.py         # Scenario management
│   │   ├── decisions.py         # Decision tracking
│   │   ├── digital_twin.py      # Digital Twin API
│   │   ├── intelligence_graph.py# Intelligence Graph API
│   │   ├── fundraising.py       # Cap table, rounds, investors
│   │   ├── connectors.py        # Data connector management
│   │   └── ...                  # 20+ additional API modules
│   │
│   ├── copilot/                 # AI Copilot system
│   │   ├── agents/
│   │   │   ├── router.py        # Multi-agent router (parallel dispatch)
│   │   │   ├── cfo_agent.py     # Financial analysis specialist
│   │   │   ├── market_agent.py  # Market research specialist
│   │   │   ├── strategy_agent.py# Strategic planning specialist
│   │   │   └── ops_agent.py     # Operations specialist
│   │   ├── ckb.py               # Company Knowledge Base
│   │   └── prompts/             # System prompts
│   │
│   ├── services/                # Business logic layer
│   │   ├── digital_twin.py      # Digital Twin state (cached)
│   │   ├── simulation_engine.py # Monte Carlo simulation core
│   │   ├── forecasting.py       # Holt-Winters, regression
│   │   ├── optimization.py      # Multi-objective optimizer
│   │   ├── recommendations.py   # Automated recommendations
│   │   ├── intelligence_graph.py# Graph analytics
│   │   └── truth_scan.py        # Data quality validation
│   │
│   ├── workers/                 # Background job processors
│   │   ├── worker_runner.py     # Unified worker with ThreadPool
│   │   ├── simulation_worker.py # Simulation job handler
│   │   └── handlers/            # Queue-specific handlers
│   │       ├── simulation_handler.py
│   │       ├── connector_handler.py
│   │       └── forecast_handler.py
│   │
│   ├── realtime/                # WebSocket layer
│   │   ├── websocket_manager.py # Company-scoped WS connections
│   │   └── routes.py            # WS endpoint registration
│   │
│   ├── infrastructure/          # Cross-cutting concerns
│   │   └── pubsub.py            # Redis pub/sub messaging
│   │
│   ├── connectors/              # Data source connectors (37)
│   │   ├── registry.py          # Connector registry
│   │   ├── stripe_connector.py
│   │   ├── quickbooks_connector.py
│   │   └── ...
│   │
│   ├── middleware/               # HTTP middleware
│   │   ├── rate_limiter.py      # Tiered rate limiting
│   │   └── auth.py              # JWT verification
│   │
│   ├── seed/                    # Database seeding
│   │   ├── seed_demo.py         # Demo company data
│   │   ├── seed_twin_intelligence.py  # Twin + graph data
│   │   └── seed_benchmarks.py   # Industry benchmarks
│   │
│   └── schemas/                 # Pydantic schemas
│       └── canonical.py         # Shared request/response models
│
├── scripts/                     # Operations scripts
│   ├── db_backup.py             # PostgreSQL backup (gzip)
│   └── db_restore.py            # Backup restore utility
│
└── docs/                        # Documentation
    └── ARCHITECTURE.md          # This file
```

## Core Infrastructure

### Redis Layer (`server/core/`)

Redis provides three capabilities, all with graceful fallback when unavailable:

1. **Cache** (`cache.py`): Key-value caching with TTL. Keys follow `fc:<prefix>:<id>` pattern.
   - Dashboard KPIs: 180s TTL
   - Digital Twin state: 120s TTL
   - Auto-invalidated on data mutations

2. **Job Queue** (`job_queue.py`): Four named queues for background processing:
   - `SIMULATION` — Monte Carlo simulation jobs
   - `CONNECTOR_SYNC` — Data connector sync jobs
   - `AI_AGENT` — AI processing jobs
   - `NOTIFICATION` — Email/SMS notification jobs

3. **Pub/Sub** (`infrastructure/pubsub.py`): Real-time event broadcasting for WebSocket layer.

### Database (PostgreSQL)

- SQLAlchemy ORM with 30+ models
- Runtime migrations in `server/core/migrations.py` (no Alembic dependency)
- Connection pooling: size=10, max_overflow=20

### Authentication

- JWT-based with refresh token rotation
- Cookie-based session (`credentials: include` on frontend)
- Google OAuth support
- Role-based access control (Platform Admin, Company Owner, Member, Viewer)

## AI Architecture

### Multi-Agent Copilot

The Router Agent receives user queries and dispatches to specialist agents **in parallel** using `asyncio.gather`:

```
User Query → Router Agent
                ├──→ CFO Agent (financial analysis)      ─┐
                ├──→ Market Agent (market research)       ─┤ parallel
                ├──→ Strategy Agent (strategic planning)  ─┤ execution
                └──→ Operations Agent (execution plans)   ─┘
                          ↓
                  Merged Response → User
```

### Multi-LLM Routing

Tasks are routed to optimal LLMs:
- **OpenAI GPT-4o**: Financial analysis, metrics extraction, vision
- **Anthropic Claude**: Complex reasoning, strategy, code generation
- **Google Gemini**: General chat, high-volume tasks
- **Perplexity**: Real-time web search, market benchmarks
- **OpenRouter/Grok**: News, trends, current events

## Navigation Architecture

### Sidebar (5 Core Modules)

| Module      | Route        | Description                        |
|-------------|-------------|------------------------------------|
| Dashboard   | `/`         | KPI overview, health score         |
| Simulate    | `/scenarios`| Monte Carlo simulations, scenarios |
| Decisions   | `/decisions`| Decision tracking & recommendations|
| AI Copilot  | `/copilot`  | Multi-agent AI assistant           |
| Data        | `/data`     | Data input & management            |

### Settings Drawer (accessed via gear icon)

Organized into groups: Data & Integrations, Metrics & Reports, Finance, Track, Admin (role-gated), Support.

## Real-time Layer

WebSocket connections are scoped by company. The manager tracks active connections per company and broadcasts events (simulation complete, data sync, alerts).

```
Client ←→ Express WS Bridge ←→ FastAPI WebSocket Manager
                                      ↕
                              Redis Pub/Sub (when available)
```

## Background Workers

The unified worker runner (`worker_runner.py`) uses ThreadPoolExecutor to process jobs from Redis queues:

- Polls queues at configurable intervals
- Handles job lifecycle: dequeue → process → complete/fail
- Falls back to DB polling when Redis is unavailable
- Concurrent execution with configurable thread pool size

## Data Flow

```
Data Sources → Connectors → Truth Scan → Financial Records
                                              ↓
                                    Company State (Digital Twin)
                                              ↓
                              ┌───────────────┼───────────────┐
                              ↓               ↓               ↓
                        Simulations      Forecasting     AI Copilot
                              ↓               ↓               ↓
                        Scenarios        Alerts          Recommendations
                              ↓               ↓               ↓
                              └───────────────┼───────────────┘
                                              ↓
                                     Dashboard KPIs
```

## Deployment

- **Dev**: Express proxy (port 5000) → Vite dev server + FastAPI (port 8001)
- **Prod**: Express serves static build + proxies API to FastAPI
- Health endpoint: `GET /health` returns DB, Redis, and system status
- Simulation worker runs as separate process
