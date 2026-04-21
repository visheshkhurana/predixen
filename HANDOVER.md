# FounderConsole — Engineering Handover

> **Audience:** any AI coding agent (Claude, Cursor, Codex, etc.) or new engineer who needs full context to ship features against this codebase via GitHub PRs.
>
> **Last updated:** April 2026 (post launch-prep cleanup, paywall disabled, lead-gen Live Executions merged).

---

## 1. What this product is

**FounderConsole** is an AI-powered financial intelligence platform for early-stage startups. Tagline: "Flight Simulator for Founders."

It replaces the founder's spreadsheet with:
- **Monte Carlo simulations** (P10/P50/P90 runway, 24-month projections, sensitivity analysis)
- **A multi-agent AI Copilot** that reads the company's data and answers strategic questions
- **A "Digital Twin"** continuously updated representation of the company (health score, risk indicators)
- **Fundraising OS** (cap table, dilution, exit waterfalls, investor room)
- **38 data connectors** (QuickBooks, Stripe, Gusto, Shopify, etc.)
- **Decision engine** that ranks recommended actions
- **Free public tools** (Survival Simulator, Runway Calculator) for top-of-funnel

**Live URLs:** https://founderconsole.ai (production), GitHub `https://github.com/visheshkhurana/predixen`

---

## 2. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Fast HMR, simple build |
| Routing | Wouter | Lightweight, no boilerplate |
| State | Zustand + TanStack React Query v5 | Minimal global state, server state cached |
| Forms | React Hook Form + Zod | Validated forms |
| UI | Tailwind CSS + shadcn/ui | Accessible primitives, consistent design |
| Charts | Recharts | Composable, fits React |
| Animation | Framer Motion + GSAP + tailwindcss-motion | Page/scroll/entrance |
| SEO | react-helmet-async (`SEOHead.tsx`) | Per-page meta + JSON-LD |
| Backend | FastAPI (Python 3.11) | Async, OpenAPI free |
| ORM | SQLAlchemy + Alembic | Standard Python |
| DB | PostgreSQL | Relational, JSON columns where needed |
| Auth | JWT + refresh-token rotation, Google OAuth | Stateless API, social login |
| Background | ThreadPoolExecutor worker reading Redis queues | No Celery needed |
| Cache/queue | Redis (optional, fallback to `_NullRedis`) | Graceful degradation |
| Realtime | WebSockets (`server/index.ts`) | Company-scoped channels |
| Email | Resend | Transactional + activity emails |
| SMS | Twilio | Notification channel |
| LLMs | OpenAI, Anthropic, Gemini, Perplexity, OpenRouter (Grok) | Task-type routing |
| Analytics | PostHog | Pageviews + custom events |
| Hosting | Replit Deployments | One-click publish, autoscale |
| CI / VCS | GitHub `visheshkhurana/predixen` | PR-based workflow |

---

## 3. Top-level architecture

```
┌────────────────────────────────────────────────────────────────┐
│                          BROWSER                               │
│  React app (Vite-built static bundle) + Wouter routing         │
└────────────────────┬───────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  Express server  (server/index.ts)  — port 5000 in prod        │
│   • Serves the built client                                    │
│   • Vite middleware in dev                                     │
│   • WebSocket server on /ws                                    │
│   • Proxies /api/* to FastAPI on localhost:8001                │
└────────────────────┬───────────────────────────────────────────┘
                     │ /api/*
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI app  (server/main.py)  — uvicorn on port 8001         │
│   • 537 routes registered (lazy-loaded after startup)          │
│   • Routers in server/api/*.py (73 files)                      │
│   • Services in server/services/*.py                           │
│   • Connectors in server/connectors/*.py                       │
│   • Auth, RBAC, paywall middleware (paywall currently OFF)     │
└────────┬───────────────────────────────────┬────────────────────┘
         │                                   │
         ▼                                   ▼
┌──────────────────────────┐       ┌────────────────────────────┐
│ PostgreSQL  (DATABASE_URL)│       │ Redis (optional)           │
│  SQLAlchemy ORM           │       │  cache, queues, pub/sub    │
└──────────────────────────┘       └────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Background worker (server/workers/simulation_worker.py)        │
│  Polls Redis queues: SIMULATION, CONNECTOR_SYNC,               │
│  AI_AGENT, NOTIFICATION                                        │
└────────────────────────────────────────────────────────────────┘
```

Two long-running processes: **Express (Node)** and **FastAPI (Python)**, plus the **simulation worker**. Express is the public face and proxies API traffic. The Replit workflow `Start application` runs `npm run dev`, which starts Express, which spawns FastAPI as a child process.

---

## 4. Repository layout

```
.
├── client/
│   ├── public/            # llms.txt, robots.txt, sitemap.xml, og-image.png
│   └── src/
│       ├── api/           # API client (api/client.ts) + per-feature wrappers
│       ├── components/    # shadcn/ui under ui/, custom under root
│       │   └── ui/        # motion-primitives, glass-card, sim-* components
│       ├── hooks/         # use-toast, use-subscription, etc.
│       ├── lib/           # seo.ts, queryClient.ts, utils
│       ├── pages/         # 57 page components
│       │   └── admin/     # admin/* including admin/lead-gen/*
│       ├── styles/        # simulate-design.css (fc-* animations)
│       ├── App.tsx        # Wouter routes + GatedRoute wrappers
│       └── main.tsx
├── server/
│   ├── index.ts           # Express + WebSocket + FastAPI spawner
│   ├── main.py            # FastAPI app + middleware + startup tasks
│   ├── api/               # 73 routers, registered in main.py
│   ├── services/          # business logic (digital_twin, simulation, etc.)
│   ├── connectors/        # 38 connector implementations
│   ├── core/              # config, db, auth, encryption, plans, subscription
│   ├── copilot/           # multi-agent Copilot system
│   ├── simulation/        # Monte Carlo + sensitivity engines
│   ├── simulation_agents/ # Agent Simulation v1
│   ├── services/simulation/ # Agent Simulation v2 (LLM-powered)
│   ├── seed/              # demo data seeding
│   ├── email/             # Resend templates + activity_triggers
│   ├── workers/           # simulation_worker
│   └── models/            # SQLAlchemy models
├── shared/                # shared TS types if any
├── scripts/               # build, launch_gate, migrations
├── attached_assets/       # uploaded files
├── .local/                # Replit agent skills + tasks (do not commit secrets)
├── replit.md              # canonical project memory (READ THIS)
├── HANDOVER.md            # this file
├── package.json           # npm scripts: dev, build, start, db:push, check
├── tsconfig.json
├── vite.config.ts         # do not modify unless absolutely necessary
└── tailwind.config.ts
```

`replit.md` is the **canonical project memory**. Read it before starting any task — it captures every architectural decision, data-flow gotcha, and feature inventory.

---

## 5. Data model & critical data-flow rules

These are landmines. If you violate one, things will silently break.

### Single source of truth
- **`TruthScan.outputs_json.metrics`** is the canonical source for all financial metrics. Board Deck, Copilot, Health Check, Decisions all read from it.
- Truth Scan stores `net_burn` (not `monthly_burn`), `runway_p50` (not `runway_months`), `headcount`, `is_profitable`, `runway_sustainable`.

### API conventions
- `GET /api/metrics` returns `{items: [...], total, page, page_size}` — handle the paginated wrapper.
- All authenticated routes expect `Authorization: Bearer <jwt>`.
- Webhooks expect HMAC headers (e.g., `/api/webhooks/lead-gen/ingest` requires HMAC signed with `LEAD_GEN_WEBHOOK_SECRET`).

### Simulation engines
- `simulation_engine.py` and `enhanced_monte_carlo.py` expect `baseline_growth_rate` and `gross_margin` as **raw percentages** (e.g., `5` for 5%, `70` for 70%). They divide by 100 internally. **Never pre-divide.**
- Guardrails in `engine.py`: growth_rate capped 50%/mo, MRR hard cap $100M, customers cap 1M, `cash += MRR - burn` (no disconnect). LLM impact deltas clamped to ±30%. Agent personas use deterministic fallbacks when LLM unavailable.
- `enhanced_monte_carlo.py` uses `max_cap=240` months. Profitable simulations compute proportional runway from growth trajectories instead of flat caps.
- `sensitivityAnalysis.ts` projects up to 60 months (not 24) so stressed companies actually run out of cash within the window.

### Decision scoring
- `enhanced_engine.py` survival-weighted: survival 35%, downside 25%, upside 20%, optionality 10%, reversibility 10%.
- Hard caps: survival <50% → max 4.5/10, <70% → max 6.5/10. Revenue decline (ARR ratio <0.7) applies 15% penalty.

### Fallbacks
- `digital_twin.py` falls back to TruthScan metrics (cash_balance, net_burn, revenue) when CompanyState has zero/missing values.
- `fundraising_readiness.py` computes runway from cash/burn when `runway_months` is missing or zero.

### NLP
- `intent_parser.py` has `FINANCIAL_TERM_ALIASES` mapping 65+ industry abbreviations (ARR, MRR, ARPU, LTV, CAC, NRR, GMV, EBITDA, COGS, AOV, COD, RTO, etc.) → canonical keys.
- `ingest.py` `field_mapping` covers 37+ canonical fields with extensive synonym lists for CSV/document extraction.

---

## 6. Key features and where they live

| Feature | Frontend | Backend |
|---|---|---|
| Auth (login/signup/Google OAuth) | `pages/auth.tsx`, `auth-callback.tsx` | `api/auth.py` |
| Dashboard | `pages/dashboard.tsx` | `api/dashboards.py`, `api/dashboard_kpis.py` |
| Truth Scan | `pages/truth-scan.tsx`, `data-verification.tsx` | `api/datasets.py`, `services/truth_scan.py` |
| Simulation Console | `pages/scenarios.tsx`, plus Flight Simulator tab in `simulate.tsx` | `api/advanced_simulation.py`, `api/agent_simulation.py`, `services/simulation/` |
| Copilot | `pages/copilot.tsx` | `api/copilot.py`, `copilot/` |
| Cap Table | `pages/cap-table.tsx` | `api/cap_table.py` |
| Fundraising | `pages/fundraising.tsx` | `api/fundraising.py` |
| Hiring Planner | `pages/hiring-planner.tsx` | `api/hiring.py` |
| Digital Twin | `pages/digital-twin.tsx` | `api/digital_twin.py`, `services/digital_twin.py` |
| Decisions | `pages/decisions.tsx` | `api/decisions.py`, `decision/` |
| Doc Generator | `pages/doc-generator.tsx` | `api/doc_generator.py` |
| AI Graphics | `pages/ai-graphics.tsx` | `api/ai_graphics.py` (gpt-image-1) |
| Connectors | `pages/integrations.tsx`, `connector-marketplace.tsx`, `add-data-source.tsx` | `api/connectors.py`, `connectors/*.py` |
| Survival Simulator (public) | `pages/survival-simulator.tsx` | `api/survival.py` |
| Runway Calculator (public) | `pages/runway-calculator.tsx` | client-side only |
| Billing | `pages/billing.tsx` | `api/billing.py`, `core/plans.py`, `core/subscription.py` |
| Admin | `pages/admin/*` | `api/admin.py` + admin-only deps |
| Lead-gen (admin) | `pages/admin/lead-gen/*` | `api/lead_gen.py` |
| Lead-gen Live Executions | `pages/admin/lead-gen/live.tsx` | `GET /api/admin/lead-gen/executions` (proxies n8n) |

### Cross-cutting systems
- **Multi-LLM router** (`copilot/llm_router.py`): picks OpenAI/Anthropic/Gemini/Perplexity/Grok by task type.
- **Event Ledger** (`api/events.py` + `events/` table): append-only event sourcing.
- **Feature Flags** (`core/feature_flags.py`): runtime toggles, per-company/user overrides.
- **AI Governance** (`copilot/ai_governance.py`): per-agent permission + daily limits + human-approval flags.
- **Data Confidence Engine** (`services/data_confidence.py`): freshness/diversity/consistency scoring.
- **Founder Autopilot** (`services/founder_autopilot.py`): daily risk detection + briefing.
- **Activity Email Triggers** (`email/activity_triggers.py`): auto-emails on simulation/doc/decision completion.
- **AI Learning Loop** (`copilot/feedback_analyzer.py` + `learning_context.py`): user ratings → aggregated → injected into Copilot prompt. Admin UI in System Tools "AI Learning" tab.

---

## 7. Authentication & users

- JWT access tokens (1h expiry) + refresh tokens (rotated on use).
- Roles: `owner`, `admin`, `member`, `viewer`. Admin pages require `owner`.
- Google OAuth supported (`oauth_provider='google'`).
- **Paywall is currently disabled** — `PaywallMiddleware` is commented out in `server/main.py`, and `client/src/components/PaywallGate.tsx` is a passthrough. Plan tiers preserved in `server/core/plans.py`. To re-enable: revert `PaywallGate.tsx` (commit `60e89bef` is the original) and uncomment `app.add_middleware(PaywallMiddleware)`.

### Demo / test accounts (production)
| Email | Password | Role | Notes |
|---|---|---|---|
| `demo@founderconsole.ai` | `demo123` | owner | Demo company "TechFlow Analytics" pre-loaded |
| `owner@predixen.ai` | (founder's) | owner | Real owner |
| `vysheshk@gmail.com` | Google OAuth | viewer | Founder's personal Google login |

7 real users total. All test accounts have been purged.

---

## 8. Local development

### Prerequisites
- Node 20+, Python 3.11, PostgreSQL (Replit provides this automatically via `DATABASE_URL`)
- Redis is **optional** — the app gracefully falls back to `_NullRedis`

### Run
```bash
npm install
npm run dev          # starts Express + FastAPI + simulation worker
```
Express serves on **port 5000** (or 5001 if 5000 is busy), FastAPI internally on **8001**, Vite HMR on **5173**.

### Other scripts
```bash
npm run build        # production bundle
npm run start        # run production bundle
npm run check        # tsc typecheck
npm run db:push      # drizzle-kit push (only if Drizzle schema changed)
npm run launch:gate  # pre-launch sanity script
```

### Python dev quirks
- The Python venv lives in `.pythonlibs` (managed by Replit). Use `python3 -m pip install <pkg>` only via the package management tooling (do not edit `pyproject.toml` by hand if you can avoid it).
- DB migrations: SQL migrations are run automatically at startup by `server/core/migrations.py`. Add new tables there or in `server/models/` and let SQLAlchemy create them via the migration runner.

---

## 9. Environment variables / secrets

Required:
- `DATABASE_URL` — Postgres connection string
- `SECRET_KEY` — JWT signing + credential encryption (one key, used by `server/core/encryption.py` as a fallback)
- `LEAD_GEN_WEBHOOK_SECRET` — HMAC for n8n → predixen webhook

Optional but recommended:
- `RESEND_API_KEY` — email
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` — SMS
- `SLACK_SIGNUP_WEBHOOK_URL` — Slack ping on every new signup
- `PERPLEXITY_API_KEY` — direct (also via integrations)
- `VITE_POSTHOG_KEY` — analytics
- `VITE_SENTRY_DSN` — frontend error tracking (currently unset, Sentry is disabled)

LLM keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`) are managed via Replit's AI integrations, **not** raw env vars. They're injected at runtime through the integration layer.

**Never commit secrets** to the repo. Use Replit Secrets panel.

---

## 10. Deployment

- Replit Deployments. Pushes to `main` trigger an auto-build, but **publishing is manual** via the Replit workspace's Publish action.
- The publish process: builds the client bundle (`npm run build`), bundles the server, deploys to a `.replit.app` domain, then routes to `founderconsole.ai` via custom domain.
- Health check: `GET /api/health` → `{status:"healthy", database:"connected", ready:true}`.
- After every merge into `main`, publish from Replit (or ask the user to). The remote runs the same `npm run dev`-style startup.

---

## 11. GitHub workflow (for AI agents)

The repo lives at `https://github.com/visheshkhurana/predixen`. Branch model:
- `main` is protected-ish (the founder pushes directly when needed but prefers PRs).
- Feature branches: `feat/<short-name>` or `claude/<feature>` (whatever the agent prefers).
- Open a PR against `main` with a clear description.
- The Replit environment is connected via a GitHub integration — when an agent pushes to `main`, the workspace can `git pull` and re-publish.

### Recommended PR workflow for an external agent (e.g., Claude on a fresh checkout)
1. Clone the repo, install dependencies (`npm install`).
2. Read `replit.md` and this `HANDOVER.md`.
3. Run `npm run check` to confirm a clean baseline.
4. Create a feature branch: `git checkout -b feat/<thing>`.
5. Implement the change. Touch as few files as possible. Mirror the existing patterns:
   - Backend route → `server/api/<feature>.py`, register it in `server/main.py`'s router list.
   - Frontend page → `client/src/pages/<page>.tsx`, register in `client/src/App.tsx`.
   - API client wrapper → `client/src/lib/api/<feature>.ts` (or under `client/src/api/client.ts`).
   - Reuse `SEOHead` for any new public page.
   - Use `useSEO` or `<SEOHead>` to set title/description/JSON-LD.
6. Add `data-testid` attributes to every new interactive element (`button-*`, `input-*`, `link-*`, `text-*`).
7. Run typecheck (`npm run check`) and lint locally.
8. Commit with conventional message (`feat: …`, `fix: …`).
9. Push, open PR. Include a screenshot or steps-to-test.
10. After merge to `main`, ask the founder to "Publish" to push to production.

### Forbidden
- **Don't edit `package.json` scripts** without asking.
- **Don't modify `vite.config.ts` or `server/vite.ts`** unless absolutely required.
- **Don't change primary key column types** (serial ↔ varchar) — breaks migrations.
- **Don't commit `.env` or any secret** — use Replit Secrets.
- **Don't disable typescript checks** to make a build pass.
- **Don't remove pages or features** without the founder's explicit OK. The product is feature-rich on purpose.

---

## 12. Testing strategy

- No automated CI runs yet. Pre-launch QA was done with an AI QA agent (see the QA prompt in chat history).
- Manual smoke tests after every deploy:
  - `GET /` → 200
  - `GET /api/health` → 200 + `database:"connected"`
  - Login as `demo@founderconsole.ai` / `demo123` → can reach `/dashboard`
  - `/admin/lead-gen` → Overview loads (no infinite skeleton — that bug is fixed)
- Unit tests live in `server/tests/` (pytest). Run with `pytest server/tests/`. Coverage is partial.

---

## 13. Known quirks / acceptable noise

| Symptom | Cause | Action |
|---|---|---|
| `[Sentry] No DSN configured` warning in console | Sentry is intentionally off | ignore |
| Vite HMR WebSocket connect failure in Replit preview | Replit proxy quirk in dev | ignore |
| `Redis unavailable` log line at startup | Redis is optional | ignore |
| `chrome-extension://hoklmmgfnpapgjgcpechhaamimifchmp/frame_ant.js` errors in console | User's browser extension | ignore |
| `/connectors/catalog` (no `/api/` prefix) returns 500 | Legacy un-prefixed route | ignore — UI uses `/api/connectors/catalog` which returns 200 |
| Express starts on 5001 instead of 5000 | Port 5000 was occupied at start | benign |
| Demo seed prints "Could not remove duplicate company id=2..9, has references" | Old duplicate demo companies that have FK refs from financial_records etc. | benign — they're hidden in UI |

---

## 14. How to add a new feature (worked example)

**Goal:** add a "Burn Multiple" widget to the dashboard.

1. **Read `replit.md`** — confirm there's no existing burn-multiple feature. Confirm the formula: `burn_multiple = net_burn / net_new_arr` (industry standard).
2. **Backend:**
   - Add a method `compute_burn_multiple(company_id)` in `server/services/kpi_calculations.py`.
   - Expose it as a route in `server/api/dashboard_kpis.py`: `GET /api/dashboard/burn-multiple?company_id=X` returning `{value: 1.4, classification: "good"}`.
   - Register the router (it's already registered if you added to existing file).
3. **Frontend:**
   - Add `burnMultipleApi` in `client/src/lib/api/dashboards.ts` (or wherever similar wrappers live).
   - Create `client/src/components/dashboard/BurnMultipleCard.tsx` reusing the existing `GlassCard` and `NumberTicker` motion primitives.
   - Add `data-testid="text-burn-multiple"` and `data-testid="card-burn-multiple"`.
   - Import and render on `pages/dashboard.tsx` in the metric grid.
4. **Use TanStack Query** with `queryKey: ['/api/dashboard/burn-multiple', companyId]`.
5. **Update `replit.md`** — add the feature under "Key Features".
6. **Commit, PR, ask the founder to publish.**

If the feature is bigger (new page + new tables), additionally:
- Add the model in `server/models/` and migration in `server/core/migrations.py`.
- Add the new page to `client/src/App.tsx` routes.
- Add a sidebar entry in `client/src/components/app-sidebar.tsx` if it's user-facing.

---

## 15. Useful one-liners

```bash
# Local API smoke
curl -s http://localhost:5000/api/health | jq
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"demo@founderconsole.ai","password":"demo123"}'

# List all FastAPI routes
curl -s http://localhost:8001/openapi.json | jq -r '.paths | keys[]'

# DB shell
psql "$DATABASE_URL"

# Tail FastAPI logs only
tail -f /tmp/logs/Start_application_*.log | grep -E "fastapi|ERROR"
```

---

## 16. Where to ask for help

- `replit.md` for canonical project memory and gotchas.
- This file (`HANDOVER.md`) for onboarding context.
- Inline docstrings in `server/api/*.py` and `server/services/*.py`.
- The founder: Vishesh Khurana (`vysheshk@gmail.com`).

---

**TL;DR for an AI agent picking this up:**
1. Read `replit.md` first.
2. Read this file second.
3. Branch off `main`, mirror existing patterns, keep PRs small and focused.
4. Add `data-testid`s. Use SEOHead for new public pages. Don't pre-divide percentages going into simulation engines. Don't change primary-key types.
5. After merging to `main`, ping the founder to publish.
