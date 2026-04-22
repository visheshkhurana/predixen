# FounderConsole — UX Wireframe & Redesign Brief

**For:** UX engineer preparing a full redesign
**Source:** reverse-engineered from `client/src/**` as of 2026-04-22
**Scope:** every page, every layout shell, every design token

> **How to use this document.** Section 2 is the sitemap. Section 3 is the design system (color, type, motion). Section 4 describes the three layout shells. Section 5 inventories every page with its purpose, sections, data, and states. Section 6 is the component library. The appendix has raw token tables.

---

## 1. Product context

**FounderConsole** is an AI-powered financial intelligence platform for early-stage startup founders. Tagline: *"Flight Simulator for Founders."*

**Primary users:** founders and operators at pre-seed to Series B companies.

**What the product does:**
- Ingests company data from 38 connectors (Stripe, QuickBooks, Gusto, Mercury, Brex, etc.)
- Builds a continuously-updated "Digital Twin" of the company's financials
- Runs Monte Carlo simulations (P10/P50/P90 runway, 24-month projections)
- Routes strategic questions to a multi-agent AI Copilot that reads the company's data
- Ranks recommended decisions with survival-weighted scoring
- Generates fundraising artifacts (cap table, dilution waterfalls, investor room)

**Two public free tools** (top-of-funnel): Survival Simulator, Runway Calculator.

**Tech shape that constrains the UI:**
- React 18 + TypeScript + Vite, Wouter routing (no Next.js — so no file-based routing)
- shadcn/ui + Tailwind
- Framer Motion + GSAP ScrollTrigger for reveals/parallax
- Recharts for all charts
- 57 page components, 73 FastAPI routers behind `/api/*`
- Paywall is currently OFF (`PaywallGate` is a passthrough)

---

## 2. Information architecture

### 2.1 Route map

```
PUBLIC (MarketingLayout)
├── /                         Landing
├── /features                 Marketing features
├── /pricing                  Plan comparison
├── /about                    Company
├── /blog                     Blog index
├── /faq                      FAQ
├── /contact                  Contact form
├── /demo                     Demo request (routes to DemoRedirect)
├── /survival-simulator       Free public tool #1
├── /tools/runway-calculator  Free public tool #2
├── /privacy                  Legal
└── /terms                    Legal

AUTH (no layout shell — centered card on gradient bg)
├── /auth                     Login + Register (tabbed)
├── /auth/callback            OAuth return
├── /reset-password           Token-based reset
└── /verify-email             Token confirmation

ONBOARDING (minimal shell)
├── /onboarding               5-step wizard
└── /demo-redirect            Demo signup flow

AUTHENTICATED (AppSidebar shell)
├── /overview                 Dashboard home
├── /truth-scan               Data verification engine
├── /data-input               Manual data entry
├── /data-verification        Anomaly review
├── /integrations             Connected sources list
├── /connector-marketplace    Add-connector catalog
├── /add-data-source          Connector config wizard
├── /scenarios                Scenario list
├── /scenarios/:id            Scenario detail
├── /simulate                 Legacy v1 simulator
├── /simulate-workspace       Interactive workspace
├── /simulate-v2              Advanced simulator
├── /simulate-v2/shared/:token  Read-only shared sim
├── /survival/:simId          Sim result deep link
├── /decisions                Decision queue
├── /copilot                  AI chat
├── /journal                  Founder log
├── /goals                    OKR tracking
├── /alerts                   Alert inbox
├── /templates                Saved scenario/doc templates
├── /ai-graphics              Image generator
├── /doc-generator            One-pager / board deck builder
├── /cap-table                Equity ledger
├── /fundraising              Pipeline + round modeling
├── /investor-room            Shared data room
├── /kpi-board                KPI dashboard
├── /hiring-planner           Headcount + cost plan
├── /digital-twin             Live company model
├── /intelligence-graph       Entity graph view
├── /messaging                Inbox-like communications
├── /dashboards               Custom dashboards list
├── /dashboard-builder        Dashboard editor
├── /metric-catalog           Metric definitions
├── /suggested-metrics        AI-suggested metrics
├── /docs                     Internal docs/help
├── /settings                 Account / team / notifications
├── /billing                  Plans + invoices
└── /qa                       Internal QA harness

ADMIN (AdminLayout shell, owner role only)
├── /admin                    Admin dashboard
├── /admin/users              User management
├── /admin/companies          Company management
├── /admin/billing            Billing overview
├── /admin/metrics            Platform metrics
├── /admin/login-history      Auth audit
├── /admin/activity           Activity log
├── /admin/invites            Invitation management
├── /admin/email-templates    Email template editor
├── /admin/email-tracking     Email send logs
├── /admin/login              Admin auth
├── /admin/llm-audit          LLM call audit
├── /admin/evals              AI evaluation harness
├── /admin/ai-governance      AI rules/limits
├── /admin/team               Admin team members
├── /admin/system-tools       Debug tools + AI Learning tab
├── /admin/lead-gen           Lead-gen overview
├── /admin/lead-gen/live      Live executions (n8n proxy)
├── /owner-console            Founder-only deep console
```

### 2.2 User journeys

1. **Acquisition.** Landing → Survival Simulator or Runway Calculator (unsigned) → Auth → Onboarding → Overview.
2. **First-time value.** Overview (empty state) → Integrations → Add connector → Truth Scan → Digital Twin populates → Overview shows real metrics.
3. **Daily use.** Overview → Alerts → open one → Decision detail → Approve/Reject → Copilot to ask follow-up.
4. **Board-prep.** Scenarios → run → Doc Generator → Board Deck → Investor Room share.
5. **Admin.** /admin/users, /admin/system-tools, /admin/lead-gen/live.

---

## 3. Design system

### 3.1 Color scheme — how it's built

The color system is **HSL triplets stored as CSS custom properties**, then consumed by Tailwind via `hsl(var(--token) / <alpha-value>)`. This gives us:
- Per-token alpha via Tailwind (e.g. `bg-primary/20`)
- Instant light/dark switch by toggling `.dark` class on `<html>` (managed by ThemeProvider, persisted to `localStorage`)
- No hardcoded hex anywhere in components — everything routes through tokens

The shape: **neutral blue-gray scale + single blue primary + 5-color chart palette + semantic destructive**. It's intentionally minimal. Dark mode is NOT a simple inversion — each token has two tuned HSL values.

#### Light mode tokens (`:root` in `client/src/index.css`)

| Token | HSL | Preview (light) | Notes |
|---|---|---|---|
| `--background` | `220 14% 96%` | #F4F5F7 | near-white, slight blue |
| `--foreground` | `220 14% 12%` | #1B1D22 | body text |
| `--border` | `220 13% 91%` | #E5E7EB | default border |
| `--card` | `220 14% 98%` | #F9FAFB | card surface (above bg) |
| `--card-foreground` | `220 14% 12%` | #1B1D22 | |
| `--card-border` | `220 13% 94%` | #EBEDF0 | |
| `--sidebar` | `220 14% 94%` | #EDEEF2 | sidebar bg (below card) |
| `--sidebar-foreground` | `220 14% 12%` | — | |
| `--sidebar-border` | `220 13% 89%` | #E0E2E7 | |
| `--sidebar-primary` | `217 91% 60%` | #3B82F6 | active nav item |
| `--sidebar-accent` | `220 14% 89%` | #DFE1E6 | hover state |
| `--popover` | `220 14% 92%` | #E8E9ED | dropdowns |
| `--primary` | `217 91% 60%` | #3B82F6 | brand blue, CTAs |
| `--primary-foreground` | `0 0% 100%` | #FFFFFF | |
| `--secondary` | `220 14% 88%` | #DDDFE4 | secondary buttons |
| `--muted` | `220 12% 90%` | #E2E4E8 | muted surfaces |
| `--muted-foreground` | `220 12% 35%` | #4F535B | caption text |
| `--accent` | `220 10% 92%` | #E7E8EB | accent surface |
| `--destructive` | `0 84% 60%` | #EF4444 | errors, delete |
| `--input` | `220 13% 75%` | #BABEC7 | input border |
| `--ring` | `217 91% 60%` | #3B82F6 | focus ring |
| `--chart-1` | `217 91% 45%` | #1F6FE5 | blue |
| `--chart-2` | `142 76% 36%` | #169E4D | green |
| `--chart-3` | `271 81% 56%` | #A03BE5 | purple |
| `--chart-4` | `24 95% 53%` | #F57611 | orange |
| `--chart-5` | `339 90% 51%` | #EB1F77 | magenta |

#### Dark mode tokens (`.dark`)

| Token | HSL | Preview (dark) | Notes |
|---|---|---|---|
| `--background` | `220 14% 8%` | #10131A | dark blue-black |
| `--foreground` | `220 14% 96%` | #F3F4F7 | off-white body |
| `--border` | `220 13% 16%` | #23272F | |
| `--card` | `220 14% 10%` | #16181F | card surface |
| `--sidebar` | `220 14% 12%` | #1A1D24 | sidebar bg |
| `--sidebar-primary` | `217 91% 60%` | #3B82F6 | same blue, high-saturation |
| `--sidebar-accent` | `220 14% 16%` | #23272F | hover |
| `--primary` | `217 91% 60%` | #3B82F6 | **same as light** |
| `--secondary` | `220 14% 18%` | #272B34 | |
| `--muted-foreground` | `220 12% 70%` | #A9AFBC | caption |
| `--destructive` | `0 84% 60%` | #EF4444 | same as light |
| `--chart-1` | `217 91% 65%` | #5E9BF9 | lighter blue |
| `--chart-2` | `142 76% 55%` | #35D272 | lighter green |
| `--chart-3` | `271 81% 70%` | #C487EB | lighter purple |
| `--chart-4` | `24 95% 65%` | #FB9E43 | lighter orange |
| `--chart-5` | `339 90% 65%` | #F16AA6 | lighter magenta |

#### Opacity / alpha utilities (custom)

| Token | Value | Used for |
|---|---|---|
| `--elevate-1` (light / dark) | `rgba(0,0,0,.03)` / `rgba(255,255,255,.04)` | hover layer |
| `--elevate-2` | `rgba(0,0,0,.08)` / `rgba(255,255,255,.09)` | active/pressed layer |
| `--button-outline` | `rgba(0,0,0,.10)` / `rgba(255,255,255,.10)` | default button border |
| `--badge-outline` | `rgba(0,0,0,.05)` / `rgba(255,255,255,.05)` | badge border |

#### Semantic color rules the app uses (observed)

- **Blue primary (`#3B82F6`)** — all primary CTAs, active nav, progress (growth), focus ring. Same hue in both modes.
- **Green (`#10B981` / `#35D272`)** — positive metrics, runway progress, success states.
- **Purple (`#8B5CF6` / chart-3)** — survival probability, "advanced" indicators, gradient accent on landing H1.
- **Orange (chart-4)** — warnings, hiring capacity, expense categories.
- **Magenta (chart-5)** — revenue, conversion metrics.
- **Red destructive (`#EF4444`)** — error states, destructive actions, critical alerts.

**Design-system takeaway for the redesign:** the token shape is good — keep the HSL+CSS-var pattern. The brand is under-expressed (blue is generic). Consider giving the primary a more distinctive hue (not `217°`) and locking chart colors to a more intentional palette (3 colors, not 5).

### 3.2 Typography

- **Sans (body + UI):** Inter, loaded from Google Fonts with italic + opsz + weights 100–900
- **Mono (numbers, code):** IBM Plex Mono, weights 400/500/600/700
- **Serif:** Georgia fallback (not actively used in the current design)

Type scale observed on landing hero: h1 = 72px, h2 = 30px, h3 = 16–18px (inconsistent — see `design-audit-founderconsole.md` F-009). Body = 16–18px. Caption = 12–14px.

**Recommendation for redesign:** pick a distinctive display typeface (e.g. Geist, Satoshi, Instrument Serif for accents). Inter is functional but reads as "default SaaS." Standardize h3 at one size across marketing and app.

### 3.3 Spacing

Tailwind default scale (4px base: `1 = 4px`, `2 = 8px`, `4 = 16px`, `6 = 24px`, `8 = 32px`, `12 = 48px`, `16 = 64px`).
Custom CSS variable `--spacing: 0.25rem` exists but isn't widely consumed.

**Section rhythm on marketing:** `py-20 md:py-32` (~80/128px vertical).
**Card internal padding:** `p-6 md:p-8` (24–32px).
**Grid gaps:** `gap-4` / `gap-6` (16/24px) standard, `gap-12` (48px) for major groupings.

### 3.4 Border radius

| Token | Value |
|---|---|
| `--radius` | `0.5rem` (8px) base |
| `rounded-sm` | 3px |
| `rounded-md` | 6px |
| `rounded-lg` | 9px |
| `rounded-xl` | 12px (Tailwind default) |
| `rounded-2xl` | 16px (used on hero glass card) |
| `rounded-full` | 9999px (badges, pills, CTAs) |

### 3.5 Shadow / elevation

Five shadow tiers defined as CSS vars (`--shadow-2xs` through `--shadow-2xl`), all using the same pattern: a 2px sharp drop + a softer blur. Dark mode uses lower-opacity shadows to avoid muddy overlap.

Plus a custom **elevate system** (`hover-elevate`, `active-elevate`, `toggle-elevate`) that applies a pseudo-element overlay rather than a box-shadow — allowing state layers to compound on top of borders. This is consistent across buttons, list items, and nav.

### 3.6 Glass / backdrop blur

Three glass tiers defined in `index.css`:

| Class | Background | Blur | Saturate | Border |
|---|---|---|---|---|
| `.glass-subtle` | card @ 0.6 | 12px | 1.5 | border @ 0.5 |
| `.glass-medium` | card @ 0.45 | 20px | 1.6 | border @ 0.4 |
| `.glass-strong` | card @ 0.3 | 32px | 1.8 | border @ 0.3 |
| `.glass-glow` | — | — | — | adds primary-colored outer + inset glow |

Used on hero stat cards, modals, sidebar panels. Automatically disabled under `prefers-reduced-motion: reduce`.

### 3.7 Motion

**Framer Motion primitives** (`components/ui/motion-primitives.tsx`):
- `FadeIn` — opacity 0→1 + y 20→0
- `NumberTicker` — animated count-up, respects `prefers-reduced-motion`
- `GlowEffect` — pulsing box-shadow

**Keyframes defined in `styles/simulate-design.css`:**
- `fc-fadeUpIn`, `fc-scaleFadeIn`, `fc-pulseBorder`
- `fc-shimmer` — diagonal shimmer for loaders/gradients
- `fc-drift1`, `fc-drift2`, `fc-drift3` — slow background blob drift
- `fc-float1`, `fc-float2`, `fc-float3`, `fc-twinkle` — particle animations (now unused after F-011)
- `fc-statusPulse`, `fc-pulseGlow`, `fc-rollUp`

**GSAP ScrollTrigger:** stats section on landing, hero parallax (`yPercent: 15, opacity: 0.6` scrubbed to scroll).

**Tailwind-animate:** accordion open/close, fade-in/out.

**tailwindcss-motion:** additional easing/duration utilities.

**Global rule:** every animation is disabled or reduced to `0.01ms` when the user has `prefers-reduced-motion: reduce`.

---

## 4. Layout shells

There are three shells. Every page uses exactly one.

### 4.1 MarketingLayout

Used by all public marketing routes + legal docs.

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (sticky, glass on scroll)                           │
│  ┌───────┐              ┌──────┬─────┬─────┬────┬───┐       │
│  │ Logo  │              │Feat. │Pric.│About│Blog│FAQ│       │
│  │       │              └──────┴─────┴─────┴────┴───┘       │
│  │                                     ┌─────┐ ┌──────┐     │
│  │                                     │Watch│ │Get   │     │
│  │                                     │Demo │ │Start │     │
│  └───────┘                              └─────┘ └──────┘     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MAIN CONTENT                                               │
│  (full-bleed or max-w-7xl centered, per page)               │
│  Floating decorative blobs in pointer-events-none layer     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                     │
│  Logo · Product · Company · Resources · Legal · Social      │
│  Newsletter signup                                          │
│  © 2026 FounderConsole                                      │
└─────────────────────────────────────────────────────────────┘
```

**Header items** (from `MarketingLayout.tsx`): Logo (left), nav links (Features, Pricing, About, Blog, FAQ, Survival Simulator), then right-side Watch Demo (outlined) + Get Started Free (filled). Mobile: hamburger → sheet drawer with same items.

**Decorative layer:** `MarketingBackground` — fixed, `pointer-events-none`, renders 3 soft drift blobs (green, purple, cyan) at low opacity behind everything. (Previously 18 particle dots, removed in F-011.)

### 4.2 App shell (AuthenticatedRoute + AppSidebar)

```
┌───────────────┬──────────────────────────────────────────────┐
│ SIDEBAR       │  HEADER (sticky)                             │
│ (collapsible) │  Breadcrumbs > Page title    Alerts Brief User│
│               ├──────────────────────────────────────────────┤
│ [Logo] FC     │                                              │
│ Intelligence  │                                              │
│ OS            │                                              │
│               │                                              │
│ ─────────     │                                              │
│ [Company ▾]   │                                              │
│ TechFlow      │                                              │
│               │                                              │
│ ─────────     │     MAIN CONTENT AREA                        │
│ ⭐ Ask AI     │     (page-specific)                          │
│   (Cmd+K)     │                                              │
│               │                                              │
│ ─────────     │                                              │
│ HEALTH 84/100 │                                              │
│ Confidence 92%│                                              │
│               │                                              │
│ ─────────     │                                              │
│ CORE          │                                              │
│ • Dashboard   │                                              │
│ • Simulate 3  │                                              │
│ • Decisions 2 │                                              │
│ • Alerts 5    │                                              │
│               │                                              │
│ FINANCE       │                                              │
│ • Cap Table   │                                              │
│ • Fundraising │                                              │
│ • Investors   │                                              │
│ • Hiring Plan │                                              │
│               │                                              │
│ INTELLIGENCE  │                                              │
│ • Digital Twin│                                              │
│ • KPI Board   │                                              │
│ • Health Check│                                              │
│               │                                              │
│ DATA          │                                              │
│ • Data Input  │                                              │
│ • Truth Scan  │                                              │
│ • Integrations│                                              │
│               │                                              │
│ ─────────     │                                              │
│ ⚙ Settings    │                                              │
│ 🌓 Theme      │                                              │
└───────────────┴──────────────────────────────────────────────┘

COPILOT DRAWER (Cmd+K, overlay from right) — 480–640px wide
```

**Sidebar exact items** (from `app-sidebar.tsx`):
- Logo + tagline block
- `CompanySwitcher` (dropdown with company list + "Add Company")
- `AskAIButton` (Cmd+K, pulsing sparkles icon)
- `HealthScoreCard` (score 0–100, confidence %, links to `/truth-scan` and `/data-input`)
- **Core group:** Dashboard (`/overview`), Simulate (`/simulate-workspace`, badge = unread scenarios), Decisions (`/decisions`, badge = pending), Alerts (`/alerts`, badge = unread)
- **Finance group:** Cap Table, Fundraising, Investor Room, Hiring Planner
- **Intelligence group:** Digital Twin, KPI Dashboards (`/dashboards`), Health Check (`/truth-scan`)
- **Data group:** Data Input
- **Integrations group:** Integrations
- `SettingsDrawer` trigger (opens right-side sheet with: Tools, Track, Account, Admin section, Support, Legal)
- `ThemeToggle` (sun/moon)

**Header items:**
- `Breadcrumbs` (auto-derived from route)
- Page title (h1-ish, medium weight)
- Alerts dropdown (bell icon with count badge, lists 3–5 recent alerts)
- Briefing button (opens `BriefingModal` with MRR, burn, runway, LTV:CAC, health)
- User menu avatar (Profile / Settings / Help / Sign Out)
- `ConfidenceBadge` (trust score % next to avatar)

**Mobile behavior:** sidebar becomes a sheet drawer triggered by hamburger. Header collapses title into truncated breadcrumb. Sticky bottom nav is not used — the sheet is the only nav affordance.

### 4.3 AdminLayout

Same header as app shell, different sidebar:

```
Admin sidebar groups:
- Users & Access: Users, Login History, Invitations, Activity
- Configuration: Companies, Team, System Tools, AI Governance
- Billing & Metrics: Billing, Metrics, LLM Audit
- Content: Email Templates, Email Tracking
- Intelligence: Evals
- Lead Gen: Dashboard, Leads, Campaigns, Templates, Settings, Live Executions
- Settings / Logout
```

Visual tone: same tokens as app, but reduced color — mostly gray with blue only on active items. Data-dense tables dominate.

### 4.4 Auth shell (no sidebar)

Centered card (max-w-md) on a full-screen subtle gradient background. Logo above card, legal links below. Used for `/auth`, `/reset-password`, `/verify-email`.

### 4.5 Onboarding shell

Minimal header with logo only + step indicator (1/5, 2/5…). No sidebar. Bottom-right "Skip for now" link. `ConfettiCannon` on final step.

---

## 5. Page wireframes

Format per page: **purpose · sections · data · key interactions · states**.

### 5.1 Public marketing

**Landing (`/`)**
- Purpose: convert visitors.
- Sections (top to bottom): Hero (badge, H1 with serif italic accent, subcopy, 2 CTAs, stat preview card) → logo cloud (connector chips) → 4-step "How it works" (icon-in-circle grid — flagged F-004) → 4-card Core Capabilities grid → Differentiators (Spreadsheet vs. FC table) → Stats strip (GSAP scrubbed) → Testimonials (2 quotes) → Pricing preview → FAQ accordion (8 items) → Final CTA.
- Data: none (static).
- States: none.
- Known issues (from audit): broken H1 space, "18 . 2" stat spacing (both fixed), generic section rhythm (F-003), fake-sounding testimonials (F-006).

**Pricing (`/pricing`)**
- Purpose: plan comparison, conversion.
- Sections: H1 + subtitle → 2–3 tier cards (Free Beta, Pro, Enterprise) with feature bullets + CTA → feature matrix table (features × plans with ✓/✗) → FAQ → contact-sales CTA.

**Features (`/marketing-features`)**
- Purpose: feature depth showcase.
- Sections: hero → category cards (Simulation, AI, Analytics, Data, Fundraising) → long-form feature blocks alternating image-left/image-right → use-case examples → integrations grid → final CTA.

**About / Blog / FAQ / Contact / Privacy / Terms** — standard marketing templates (see appendix for details).

**SurvivalSimulator (`/survival-simulator`)**
- Purpose: free lead-gen tool.
- Sections: hero explanation → input form (cash balance, monthly burn, monthly revenue, growth rate) → results panel (survival probability %, expected months, P10/P50/P90 runway, sensitivity chart) → "Save results / create account" CTA.
- Data: `POST /api/survival/simulate` (client-local also works).
- States: input form validation, results loading skeleton, no-result empty.

**RunwayCalculator (`/tools/runway-calculator`)** — simpler version: cash ÷ burn, single number output, line chart of declining balance, share URL.

### 5.2 Auth

**Auth (`/auth`)**
- Purpose: login or register.
- Layout: centered card, tab switcher (Login / Register). Fields: email + password (+ name/company on register). "Continue with Google" button above tabs. Forgot-password link.
- Data: `POST /api/auth/login`, `/api/auth/register`, `/api/auth/google`.
- States: field validation (zod), submit loading, server error banner at top of card, success → redirect to `/overview` or `/onboarding`.

**AuthCallback (`/auth/callback`)** — spinner + "Signing you in…", handles OAuth token exchange, redirects.

**ResetPassword (`/reset-password?token=…`)** — new password + confirm, validation, success screen.

**VerifyEmail (`/verify-email?token=…`)** — automatic verify on mount, success/error screen with CTA to `/overview` or request-new-link.

### 5.3 Onboarding

**Onboarding (`/onboarding`)** — 5-step wizard:
1. Company info (name, stage, industry, founded date)
2. Team size + monthly burn
3. Cash on hand + last raise
4. Connect first data source (skippable, links to `/connector-marketplace`)
5. Confirmation + confetti + CTA "Enter FounderConsole"

Layout: left = progress indicator with step titles, right = form for current step. Bottom = Back / Continue / Skip.

### 5.4 Core workspace

**Overview (`/overview`)** — the dashboard home.
```
Page header: "Good morning, [Name]" + date + briefing CTA
KPI strip (4–6 cards): MRR · Burn · Runway · Net New ARR · LTV:CAC · Health
Row 1 (2-col): Cash trajectory chart | Recent alerts list
Row 2 (2-col): Active scenarios summary | Pending decisions
Row 3: Digital Twin snapshot (health gauge + 3 risk indicators)
Row 4: Connected sources status (list with sync times)
```
- Data: `GET /api/metrics` (paginated wrapper — `{items, total, page, page_size}`), `/api/alerts`, `/api/scenarios/active`, `/api/decisions/pending`, `/api/digital-twin/snapshot`.
- States: if no company data → empty state with "Connect your first source" + inline connector picker. Loading → skeleton cards. Error → `PageErrorFallback`.

**TruthScan (`/truth-scan`)** — data verification engine.
- Sections: score gauge (0–100 confidence), data freshness indicators per source, anomaly list with "Review" action, reconciliation table (reported vs. computed), CTA to re-run scan.
- Data: `GET /api/datasets`, `POST /api/truth-scan/run`.

**DataInput (`/data-input`)** — manual entry forms for financials, categorized tabs (Revenue, Expenses, Headcount, Cash).

**DataVerification (`/data-verification`)** — anomaly review queue. Each row: anomaly description, severity badge, source, Accept/Reject/Ignore buttons.

**Integrations (`/integrations`)** — grid of connected sources. Each card: logo, status (connected/error/syncing), last sync time, manage button. "Add integration" CTA routes to `/connector-marketplace`.

**ConnectorMarketplace (`/connector-marketplace`)** — catalog of 38 connectors. Filters: category, status, popularity. Search. Each card: logo, name, 1-line description, "Connect" button.

**AddDataSource (`/add-data-source?type=…`)** — per-connector OAuth / API-key config wizard. 2–3 steps depending on connector.

### 5.5 Simulation

**Scenarios (`/scenarios`)** — scenario list.
- Table columns: name, created, owner, last-run, probability-of-survival, actions. Filter bar: status, owner, date range. Search. "+ New scenario" CTA (primary).

**ScenarioDetail (`/scenarios/:id`)** — tabbed results view.
- Header: name + description + owner + timestamps + action buttons (Duplicate, Share, Export, Delete).
- Tabs: Overview | Charts | Sensitivity | Comparison | Details.
- Overview: key metrics grid, probability gauge, narrative insights from Copilot.
- Charts: 4 Recharts plots (runway distribution with P10/P50/P90 bands, cash trajectory, burn over time, revenue projection).
- Sensitivity: tornado chart + one-way table + 2-way matrix.
- Comparison: scenario picker + side-by-side metric table.
- Details: full parameter dump, simulation metadata, raw CSV export.

**SimulateWorkspace (`/simulate-workspace`)** — interactive Monte Carlo builder.
- Left: scenario editor (variable sliders/inputs, save button, templates picker).
- Right: live preview panel (updates on save) with runway chart + key metrics.
- Top bar: scenario name, run status, Run button.

**SimulateV2 (`/simulate-v2`)** — advanced simulator (see raw report for full spec — similar to ScenarioDetail + editor).

**SharedScenario (`/simulate-v2/shared/:token`)** — read-only version of SimulateV2. Banner: "Shared with you by [name]. [Create account] to run your own."

**Survival (`/survival/:simId`)** — public-ish deep link to a single survival-simulator result.

### 5.6 Decisions & AI

**Decisions (`/decisions`)** — decision queue.
- Left panel: filter + list of decision cards (title, status badge, priority, due, impact). Sort by priority/date.
- Right panel (when card selected): full detail — description, AI recommendation with confidence score, impact analysis (revenue/runway/risk), related scenarios, Approve / Reject / Request Info / Defer buttons, discussion thread.
- States: empty ("No pending decisions"), loading skeleton, error fallback.

**Copilot (`/copilot`)** — full-screen AI chat.
- Layout: left rail = conversation history, recent prompts, bookmarks. Main = chat transcript (user messages left, AI right with avatar, source chips below each AI response, confidence badge). Bottom = input with Cmd+K hint, suggested-prompt chips.
- Data: `POST /api/copilot/chat` (streams), `GET /api/copilot/history`, `/api/copilot/suggested-prompts`.
- States: typing indicator (3 dots), streaming response, source citation expand/collapse, follow-up chips after response.

**Journal (`/journal`)** — timeline of founder-logged events. Each entry: date, category tag, text, optional attached metric. Add-entry form at top.

**Goals (`/goals`)** — OKR tracker. Grouped by quarter. Each goal: title, target, current value, progress bar, status.

**Alerts (`/alerts`)** — alert inbox. Filters: severity, category, status. Each row: severity icon, title, description, timestamp, actions (Dismiss, View Related, Snooze).

**Templates (`/templates`)** — saved scenario/doc templates. Grid + actions (Use, Edit, Delete).

**AIGraphics (`/ai-graphics`)** — image generator (gpt-image-1). Prompt input, style selector, size selector, results grid, download.

**DocGenerator (`/doc-generator`)** — document builder.
- Left: template picker (board deck, one-pager, investor update, etc.).
- Right: live preview + edit sidebar for sections. Bottom: Generate / Download PDF.

### 5.7 Financial

**CapTable (`/cap-table`)** — equity ledger.
- Sections: summary stats (fully diluted shares, pre/post-money, option pool %), stakeholder table (name, role, class, shares, %, vesting), add-stakeholder button, round simulator (new-round calculator with dilution preview), exit-waterfall chart.

**Fundraising (`/fundraising`)** — round modeling + investor pipeline.
- Tabs: Overview | Round Model | Pipeline | Investor Room.
- Pipeline = Kanban-style board (Prospect → Intro → Pitch → DD → Term Sheet → Closed). Each card: investor, check size, last touch.

**InvestorRoom (`/investor-room`)** — shareable data room.
- Document list with access controls. Visibility toggle per doc. Audit log showing who accessed what and when. Share link generator.

**KPIBoard (`/kpi-board`)** — financial KPI dashboard.
- Grid of KPI cards with trend sparkline + period toggle (7d / 30d / 90d / 1y). Drilldown on click.

**HiringPlanner (`/hiring-planner`)** — headcount planner.
- Timeline view (months horizontal, roles vertical). Each cell: role + salary. Add-hire drawer. Total cost projection at bottom. Scenario save.

**DigitalTwin (`/digital-twin`)** — live model view.
- Center: animated graph of entities (revenue sources → cash → expenses → burn). Side panel: metric panel with real-time values, last-update timestamp, confidence indicators.

**IntelligenceGraph (`/intelligence-graph`)** — entity graph explorer. Force-directed graph of customers, products, cohorts, metrics with filters and detail panel on node-click.

**Messaging (`/messaging`)** — internal/external communications inbox (unified with activity emails).

### 5.8 Dashboards & analytics

**Dashboards (`/dashboards`)** — list of custom dashboards. Grid with thumbnails. "New dashboard" CTA.

**DashboardBuilder (`/dashboard-builder/:id?`)** — drag-and-drop builder.
- Left: widget palette (metric card, line chart, bar, pie, table, text block).
- Center: canvas grid with resizable tiles.
- Right: selected-widget config panel (data source, query, formatting).
- Top bar: dashboard name, save, preview.

**MetricCatalog (`/metric-catalog`)** — all metric definitions. Table: name, formula, source, description, last-computed value. Search + filter.

**SuggestedMetrics (`/suggested-metrics`)** — AI-suggested metrics for your company. Card-based. Each card: metric name, why it matters, sample value, "Add to dashboard" button.

**Docs (`/docs`)** — internal help docs. Sidebar TOC, main content, search.

### 5.9 Account

**Settings (`/settings`)** — tabs: Profile | Team | Notifications | Integrations | Security | Danger Zone.
**Billing (`/billing`)** — plan card (current), usage stats, invoice history table, "Upgrade / Downgrade" actions.
**QA (`/qa`)** — internal QA harness (unlikely to need redesign).

### 5.10 Admin (condensed — all follow similar patterns)

Every admin page = page header + filter bar + data table + row-level actions. Columns vary by page.
- Users: email, role, company, last-login, status.
- Companies: name, owner, plan, users, last-activity.
- Billing: subscription, MRR, next-charge, plan changes.
- Metrics: platform KPIs (DAU, MAU, simulations run, API calls).
- LoginHistory: user, IP, UA, timestamp, success/fail.
- Activity: audit trail of all writes.
- Invites: pending invitations with resend/revoke.
- EmailTemplates: template list + rich-text editor.
- EmailTracking: sends with open/click rates.
- LLMAudit: every LLM call (user, prompt hash, model, tokens, cost).
- Evals: eval set list, run button, pass-rate table.
- AIGovernance: per-agent permissions + daily limits.
- Team: admin team members.
- SystemTools: debug tabs including AI Learning (user ratings feed), feature flags, cache busters.
- LeadGen (`/admin/lead-gen`): dashboard, leads table, campaigns, templates, settings, Live Executions (live feed from n8n).

---

## 6. Reusable components (design-library inventory)

**Navigation:** `CompanySwitcher`, `Breadcrumbs`, `AppSidebar`, `AdminSidebar`, `MarketingLayout` header, `SettingsDrawer`.

**Data display:** `MetricCard` (label, value, trend arrow, sparkline), `StatCard` (stat + progress bar), `GlassCard` (glass-medium wrapper), `DataTable` (sortable, paginated, selectable rows), `KPIDashboard` (metric-card grid).

**Forms:** `FormInput`, `FormSelect`, `FormCheckbox`, `FormTextarea`, `CurrencyInput`, `PercentInput`, `DateRangePicker`, `SubmitButton`. All wrap React Hook Form + Zod. Errors shown inline below field.

**Modals/drawers:** `Dialog` (centered), `Sheet` (right or bottom drawer), `BriefingModal`, `ShareModal`, `ConfirmDialog`, `CopilotDrawer`.

**Feedback:** `Alert` (severity-colored banner), `Toast` (`useToast` hook), `ProgressBar`, `Spinner`, `Skeleton`. Empty states: icon + message + primary action.

**AI / Copilot:** `ChatMessage`, `ChatInput`, `SuggestedPrompts` (chip row), `SourceCitation` (chip with hover-preview), `ConfidenceBadge`, `AskAIButton`.

**Charts (Recharts):** `LineChart`, `BarChart`, `PieChart`, `TornadoChart`, `DistributionChart` (P10/P50/P90 bands), `Sparkline`, `RunwayChart`.

**Motion primitives (`components/ui/motion-primitives.tsx`):** `FadeIn`, `NumberTicker`, `GlowEffect`, `ShimmerText`, `BlurIn` (available).

**Route wrappers:** `AuthenticatedRoute`, `GatedRoute` (feature flag), `AdminRoute`, `ErrorBoundary`, `PageErrorFallback`, `BackendStatusBanner`, `TrialBanner`, `PaywallGate` (currently passthrough).

**Testing convention:** every interactive element has `data-testid` prefixed `button-*`, `input-*`, `link-*`, `text-*`, `card-*`, `badge-*`.

---

## 7. State patterns

**Client state (Zustand `founderStore`):** `user`, `currentCompany`, `companyList`, `theme`, `copilotOpen`, `settingsDrawerOpen`, `alerts`, pending toasts.

**Server state (TanStack Query):** one query key per endpoint, e.g. `['/api/metrics', companyId]`. Default `staleTime` short, refetch on window focus.

**Auth:** JWT access token (1h) + refresh token (rotated). Stored in httpOnly cookies. `useFounderStore(s => s.user)` checks auth state.

**Paywall:** currently disabled. `GatedRoute` wraps feature routes but `PaywallGate.tsx` is passthrough.

**Company context:** almost all queries are scoped by `currentCompany.id`. Switching company via `CompanySwitcher` triggers cache invalidation.

---

## 8. Empty / loading / error patterns (observed)

| State | Pattern |
|---|---|
| Loading (list) | `Skeleton` shaped like the row (not a spinner) |
| Loading (detail) | Skeleton card stack |
| Empty (first-time) | Icon + H3 message + 1-line description + primary CTA |
| Empty (filtered) | Icon + "No results for these filters" + "Clear filters" link |
| Error (page) | `PageErrorFallback` — apologetic message + "Retry" button + support link |
| Error (inline) | `Alert` destructive variant with specific message |
| Toast (success) | auto-dismiss 3s, bottom-right |
| Toast (error) | persistent until dismiss, bottom-right |

---

## 9. Responsive behavior

**Breakpoints (Tailwind defaults):**
- `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280 · `2xl` 1536

**Rules observed:**
- Sidebar collapses to `Sheet` drawer below `md`.
- Marketing grids: 1 col mobile → 2 col `md` → 3/4 col `lg`.
- Tables: `.mobile-table-scroll` utility adds horizontal scroll below `md` with 500px min-width.
- Dashboard widgets stack below `lg`.
- Print: `.no-print` utility hides chrome; body becomes white/black.

**No dedicated mobile nav bar** — sheet drawer is the only pattern. Consider adding one in the redesign for thumb-reachable primary actions on the core workspace pages.

---

## 10. Redesign recommendations (priority stack)

From the April 2026 design audit (separate doc `design-audit-founderconsole.md`) + this inventory:

**Must-fix in redesign:**
1. Give the brand a distinctive color (blue primary is generic).
2. Pick a display typeface (Inter body is fine, but the display tier needs identity).
3. Break the "hero → 4-step grid → 4-card grid → testimonials → pricing → FAQ" section rhythm on marketing.
4. Unify H3 size across marketing and app.
5. Standardize one accent color per KPI instead of the current 4-color rainbow.
6. Add a mobile bottom nav for core workspace pages.
7. Replace fake-looking testimonials with real ones or remove the section.

**Keep:**
- HSL-var token system (excellent for the redesign).
- Glass tiers (subtle/medium/strong) — a real differentiator if used sparingly.
- The 3-blob marketing background (post-dot-removal) — tasteful.
- Elevate system (hover/active pseudo-layers) — sophisticated and compound-able.
- AppSidebar information architecture (Core / Finance / Intelligence / Data / Integrations grouping is sound).

**Open questions for the UX engineer:**
- Should Digital Twin become the primary landing surface of the authenticated app (not `/overview`)?
- Should `/simulate`, `/simulate-workspace`, `/simulate-v2` collapse to a single simulator surface? (Currently 3 generations coexist.)
- Sidebar is deep (15+ items). Should some move to a command palette only?
- Is dark mode the default presumed experience or light? (CSS implies light default; product reads dark-first.)

---

## Appendix A — full token table

See `client/src/index.css` lines 8–167 for the authoritative source. Every token has a light + dark value. Consume via `hsl(var(--token) / <alpha-value>)` in Tailwind classes like `bg-primary/20`, `text-foreground/80`.

## Appendix B — font loading

See `client/index.html` line 76:
```
fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap
```
Add any new display face to this line and wire it to `tailwind.config.ts` `fontFamily`.

## Appendix C — key files for the UX engineer to reference

| Purpose | Path |
|---|---|
| Product context | `HANDOVER.md` |
| Route map | `client/src/App.tsx` |
| Design tokens | `client/src/index.css` |
| Tailwind config | `tailwind.config.ts` |
| Marketing shell | `client/src/components/marketing/MarketingLayout.tsx` |
| App sidebar | `client/src/components/app-sidebar.tsx` |
| Motion primitives | `client/src/components/ui/motion-primitives.tsx` |
| Keyframe library | `client/src/styles/simulate-design.css` |
| Current audit findings | `design-audit-20260422/design-audit-founderconsole.md` |
