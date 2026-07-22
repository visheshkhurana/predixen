# FounderConsole — Project Handover Document

**Date:** June 14, 2026
**Live URL:** https://founderconsole.ai
**Repository:** github.com/visheshkhurana/predixen
**Platform:** Built and hosted on Replit (deployed via Replit Deployments)

> **Audience:** any new engineer, AI coding agent, or acquirer who needs full context to run, maintain, or migrate this platform.

---

## 1. What This Product Is

FounderConsole is an AI-powered financial intelligence platform for startup founders — "a flight simulator for founders." It provides:

- **Investor-grade financial diligence** — automated validation of a startup's financial data (Truth Scan)
- **Probabilistic runway simulation** — Monte Carlo engine (1,000+ paths, P10/P50/P90 outcomes)
- **AI decision recommendations** — ranked, scored action lists for founders
- **Full fundraising workflow** — cap table, dilution math, investor database (854 investors), outreach sequences, readiness scoring
- **Multi-agent AI simulations** — LLM-powered "Flight Simulator" with 7 agent personas
- **Free public growth tools** — Survival Simulator, 8 industry runway calculators, embeddable widget

The platform is currently **fully free** — a 4-tier paywall (Free $0 / Starter $29 / Growth $49 / Scale $99 per month with 30-day trial) is built and infrastructure-ready but intentionally paused. Stripe is NOT yet connected.

---

## 2. Tech Stack

### Frontend (`client/` — ~11 MB source)
| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript, Vite |
| Routing | Wouter |
| State | Zustand + TanStack React Query v5 |
| UI | Tailwind CSS + shadcn/ui, dark mode default, glassmorphism design system |
| Charts | Recharts |
| Animation | Framer Motion + GSAP ScrollTrigger + tailwindcss-motion |
| Forms | React Hook Form + Zod |

### Backend (`server/` — ~14 MB source)
| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11) on port 8001 |
| Proxy/SSR | Express (Node) on port 5000 — proxies `/api/*` to FastAPI, serves SPA, SEO prerender |
| Database | PostgreSQL (116 tables), SQLAlchemy ORM + Alembic migrations |
| Auth | JWT with refresh token rotation; Google OAuth social login |
| Cache/Queue | Redis (optional — graceful fallback to `_NullRedis` if unavailable) |
| Workers | Unified background worker (ThreadPoolExecutor) on Redis queues: SIMULATION, CONNECTOR_SYNC, AI_AGENT, NOTIFICATION |
| Realtime | WebSockets (company-scoped) + SSE streaming for agent simulations |

### Key Python dependencies
fastapi, sqlalchemy, alembic, pydantic v2, numpy/pandas/scipy (simulation math), openai, resend, twilio, redis, pdfplumber/pdf2image (document ingestion), passlib/bcrypt/python-jose (auth). Full list in `pyproject.toml`.

---

## 3. External Services & Required Secrets

Set these environment variables in any new hosting environment. **Values live in the Replit Secrets pane — export them before migrating.**

| Secret | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `RESEND_API_KEY` | Transactional + campaign email (Resend) |
| `PERPLEXITY_API_KEY` | Real-time web search / market research |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | SMS notifications |
| `SLACK_SIGNUP_WEBHOOK_URL` | Slack notification on new signups |
| `VITE_POSTHOG_KEY` | PostHog analytics (frontend) |
| OpenAI / Anthropic / Gemini / OpenRouter | Provided via Replit AI Integrations — **you need your own API keys off-Replit** (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`) |
| `ADMIN_MASTER_EMAIL` | Email address granted platform-admin access |
| `APP_BASE_URL` | Base URL used in emails (defaults to https://founderconsole.ai) |

**Verified email sending domains (Resend):** founderconsole.ai, runora.xyz, runoraai.com.

**Multi-LLM routing:** the platform routes tasks by type — OpenAI (financial analysis, vision, gpt-image-1 graphics), Anthropic (complex reasoning), Gemini (high-volume chat), Perplexity (web research), OpenRouter/Grok (news/trends). Agent Simulation v2 uses OpenAI gpt-4o-mini.

---

## 4. How to Run It

```bash
# Install
npm install
pip install -e .        # pyproject.toml is the source of truth

# Run (dev) — single command starts both servers
npm run dev
# → Express on :5000 (public entry point), FastAPI on :8001 (internal)

# Database migrations
alembic upgrade head
```

- The public entry point is **Express on port 5000**. It proxies `/api/*` to FastAPI, injects SEO meta tags server-side (`server/seo-prerender.ts`), and serves the Vite-built SPA.
- Do NOT add a Vite proxy — the Express layer already handles it.
- Redis is optional; the app runs without it (jobs run inline).

---

## 5. Feature Map (What's Built)

### Core financial engine
- **Truth Scan** — multi-stage data validation; its output (`TruthScan.outputs_json.metrics`) is the **single source of truth** for all metrics platform-wide
- **Simulation Console** (`/simulate`) — 5 tabs: Scenarios, Stress Tests, What-If, History, Flight Simulator
- **Enhanced Monte Carlo** — 24-month projections, custom events, sensitivity analysis, scenario versioning, counter-move simulations
- **Agent Simulation Engine v2** (`server/services/simulation/`) — 7 LLM agents (Founder, 2 Investors, Customer, Team, Market, Competitor) with personas + per-agent memory, SSE streaming at `POST /api/simulation/v2/run`
- **Decision Engine** — survival-weighted scoring (survival 35%, downside 25%, upside 20%, optionality 10%, reversibility 10%)
- **Forecasting & Alerts** — Holt-Winters, linear regression, Z-score anomaly detection, threshold monitoring

### Data
- CSV upload, manual entry, AI extraction from documents (PDF), multi-currency
- **38 production data connectors** (QuickBooks, Stripe, Gusto, Shopify, WooCommerce, etc.) with ecommerce-specific analytics (COD/RTO split, AOV, shipping cost, refund rates)
- Event Ledger (append-only event sourcing), Digital Twin (live company health score), Data Confidence Engine, Intelligence Graph v2

### Fundraising OS
- Cap table + dilution + exit waterfall, fundraising round tracking
- Investor Room (shareable), 854-investor database, outreach sequences
- Fundraising Readiness Score with radar chart + AI-generated one-pager

### AI layer
- **Fund Flow Copilot** — multi-agent router/orchestrator, company knowledge base, context-aware follow-ups, closed learning loop (user feedback → prompt injection via `learning_context.py`)
- **Document Generator** — financial models, investor memos, KPI reports, board decks (PDF)
- **AI Graphics Studio** — gpt-image-1 image generation
- AI Governance (per-agent permissions, daily limits), Founder Autopilot (daily risk briefings), Simulation Accuracy Tracker (predictions vs actuals with auto-calibration)
- Cross-company learning: privacy-first anonymized benchmarking

### Growth features (June 2026)
- **Shareable Survival Simulator** (`/survival-simulator`, public) — free tool with auto-generated OG social cards (1200×630 PNG, `server/api/survival_og_card.py`), shared results at `/survival/:simId` with server-injected og:image
- **Programmatic SEO** — 8 industry runway calculators at `/runway/{saas,ecommerce,fintech,marketplace,ai,hardware,biotech,devtools}` with unique copy, benchmarks, JSON-LD; all in sitemap
- **Embeddable widget** at `/embed/survival` (framing headers relaxed ONLY for `/embed/*`; copy-paste iframe snippet in the simulator share panel)
- **7-day onboarding email drip** — 6 steps (welcome d0, truth scan d1, simulator d2, copilot d4, fundraising d5, feedback d7), idempotent claim-before-send with max 3 retries, 10-minute background scheduler (`server/email/onboarding_sequence.py`)
- **Growth dashboard** at `/admin/growth` (signup funnel, time-series, weekly cohort retention, top pages)
- **Activity email triggers** — auto-emails on simulation complete / document generated / decisions created

### Admin (`/admin/*`, gated by `require_platform_admin`)
Users, companies, activity, metrics, billing, email templates + tracking, lead-gen suite (campaigns/leads/templates/settings), LLM audit, AI governance, login history, evals, system tools (6 tabs incl. AI Learning), growth dashboard.

---

## 6. Critical Data-Flow Rules (Do Not Break)

1. **Truth Scan is the single source of truth.** All features read metrics from `TruthScan.outputs_json.metrics`. Keys: `net_burn` (not `monthly_burn`), `runway_p50` (not `runway_months`), `headcount`, `is_profitable`, `runway_sustainable`.
2. **`/api/metrics` is paginated:** `{items, total, page, page_size}`.
3. **Simulation engines expect raw percentages** (5 = 5%). They divide by 100 internally — never pre-divide.
4. **Simulation guardrails:** growth capped 50%/mo, MRR cap $100M, customers cap 1M, LLM impact deltas clamped ±30%. Deterministic fallbacks when LLM unavailable.
5. **Decision scores are capped by survival:** <50% survival → max 4.5/10; <70% → max 6.5/10. Revenue decline (ARR ratio <0.7) applies 15% penalty.
6. **Stress tests project 60 months** (not 24) so distressed companies hit zero within the window.
7. **Email drip idempotency:** `onboarding_email_log` uses claim-before-send with max 3 attempts. Table auto-created at startup via `ensure_table()`.
8. **Security headers:** `X-Frame-Options: DENY` + `frame-ancestors 'none'` everywhere EXCEPT `/embed/*` paths — enforced in BOTH Express (`server/index.ts`) and FastAPI (`server/middleware/security_headers.py`). Keep both in sync.
9. **NLP term aliases:** `intent_parser.py` maps 65+ financial abbreviations (ARR, MRR, LTV, CAC, EBITDA, AOV, RTO...) to canonical keys; `ingest.py` maps 37+ canonical fields with synonyms for CSV/document extraction.

---

## 7. Repository Layout

```
client/                  React SPA
  src/pages/             ~60 route pages (incl. admin/ subdir)
  src/components/ui/     shadcn + motion primitives + glass cards + sim-* components
  src/data/              blog posts, runway industry profiles
  public/sitemap.xml     includes 8 /runway/* SEO pages
server/
  index.ts               Express entry (port 5000): proxy, security headers, SSR meta
  seo-prerender.ts       Per-route meta/OG/JSON-LD injection
  main.py                FastAPI entry (port 8001), deferred startup, schedulers
  api/                   FastAPI routers (auth, admin_*, survival_og_card, ...)
  core/                  db, plans, subscription, config
  email/                 service.py, onboarding_sequence.py, activity_triggers.py,
                         send_update_v*.py (39 historical campaign scripts)
  services/simulation/   Agent Simulation Engine v2
  simulation_agents/     Agent Simulation Engine v1
  middleware/            security headers, paywall middleware
shared/                  Shared TypeScript schema
alembic/                 DB migrations
replit.md                Living architecture doc (keep updated)
```

---

## 8. Email Campaign System

- One-off updates are sent via versioned scripts: `python server/email/send_update_vNN.py` (latest: v39, June 2026).
- Pattern: per-recipient personalization, plain-text + HTML versions, open-tracking pixel via `/email-tracking/analytics`, UTM params, 2-second delay between sends.
- Senders used: `arjun@founderconsole.ai`, `arjun@runora.xyz` (both verified in Resend).
- Email open/click analytics visible at `/admin/email-tracking`.
- Automated flows: onboarding drip (6 emails / 7 days) + activity triggers (simulation/document/decision completion emails).

---

## 9. Current State & Known Items

- **Paywall:** built but disabled — re-enable via `PaywallMiddleware` + `server/core/plans.py`; Stripe integration is the missing piece before charging.
- **Security:** June 2026 CVE sweep fixed protobufjs, mako, python-multipart, urllib3. 2 high-severity npm advisories remain (transitive).
- **Proposed next task:** upgrade AI models from gpt-4o family to gpt-5.
- **Onboarding drip is live** — new signups get the welcome email immediately, then 5 more over 7 days.
- **SEO:** sitemap.xml, per-route meta/OG/JSON-LD prerender, 8 programmatic industry pages, blog with 15+ articles.

---

## 10. Migration Checklist (Leaving Replit)

1. `git clone` the repo (or push latest from Replit to GitHub — repo already connected).
2. Provision PostgreSQL; migrate data (`pg_dump` from Replit DB → restore), then `alembic upgrade head`.
3. Provision Redis (optional but recommended for production job queues).
4. Copy all secrets (Section 3) into the new environment. **Obtain your own OpenAI/Anthropic/Gemini/OpenRouter keys** — Replit-managed AI integration credentials will NOT work off-platform.
5. Build: `npm run build`; run Express via `npm start` and FastAPI via `uvicorn server.main:app --port 8001`.
6. Point DNS for founderconsole.ai at the new host; TLS required (emails, OAuth callbacks, and OG cards all assume https://founderconsole.ai).
7. Update Google OAuth authorized redirect URIs if the domain changes.
8. Verify end-to-end: signup → welcome email, `/survival-simulator` + share card, `/simulate` Flight Simulator (needs OpenAI key), `/admin/growth` (needs `ADMIN_MASTER_EMAIL`), a data connector sync.
