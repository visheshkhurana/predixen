# FounderConsole — Product

> Paste this into a Google Doc titled **"KB — Product"** and point the `Knowledge Base` Google Docs Tool node at its doc ID.

## What it is

FounderConsole is a financial intelligence platform for startup founders. It takes your company's actual numbers — cash, burn, MRR, growth rate, hiring plan — and runs thousands of Monte Carlo simulations to show you:

- **Runway** — how many months of cash you have at current burn
- **P50 / P90 survival probability** — the odds your company survives N months given realistic growth variance
- **Dilution modeling** — what your cap table looks like after your next round at different valuations and round sizes
- **Scenario comparisons** — "what if we hire 3 more engineers?", "what if growth stalls for 3 months?", "what if we push the raise by 6 months?"

The tagline: **"The Flight Simulator for Founders"** — because most founders plan on spreadsheets that give point estimates. FounderConsole gives probabilities.

## Who it's for

Primary ICP:
- Startup founders (solo, co-founders, CEOs)
- Stage: pre-seed → Series B
- Size: 1–50 employees
- Sectors: SaaS, fintech, AI, B2B tech — anything where runway + dilution matter

Secondary:
- Fractional CFOs working with multiple portfolio companies
- VCs doing bottom-up diligence on prospective investments (hence "investor-grade diligence")

Not for:
- Companies with >200 employees (they have real finance teams)
- Agencies / services businesses (different financial model)
- Solo consultants (no burn to model)

## Core features

### Free tier
- **Survival Simulator** — enter cash/burn/MRR, get runway + P50/P90 survival probability
- **Basic runway modeling** — straight-line projection
- No signup required to try

### Pro ($29/mo)
- Scenario saves — keep multiple what-ifs named and compared
- **Cap table modeling** — model founder/employee/investor ownership over multiple rounds
- **Dilution preview** — show post-round cap table at different valuations
- Export to PDF / Excel
- Historical scenarios — see how your projections have changed over time

### Team ($99/mo)
- Everything in Pro, plus:
- Multi-user access (founders + finance team + advisor)
- **Investor-ready PDF reports** — formatted for data rooms
- Custom branding
- API access (beta)
- Priority support from Vishesh directly

## Integrations

Today:
- Manual data entry (web form)
- CSV import for historical financials
- Google Drive export

Roadmap:
- QuickBooks sync (Q2 2026)
- Stripe MRR sync (Q2 2026)
- Xero sync (Q3 2026)
- Slack alerts on survival probability drops (Q3 2026)

## Data + security

- Data is encrypted at rest (AES-256) and in transit (TLS 1.3)
- Hosted on AWS, US-East region
- **You own your data.** Export anytime, delete anytime.
- We never sell data to third parties.
- SOC 2 Type II in progress (target: Q4 2026).
- The free Survival Simulator runs entirely in your browser — your numbers never touch our servers.

## How it works technically

- Monte Carlo engine written in Python (FastAPI backend)
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL for user data
- Simulations run 10,000 trials per scenario with configurable variance on revenue growth, burn, and timing

## Competitors / differentiation

- **Excel / Google Sheets** — point estimates, no probabilistic modeling. You can build this yourself in 40 hours. We do it in 5 minutes and it stays up to date.
- **Carta Launch / Pulley** — great for cap tables, not for runway modeling.
- **Fathom / Causal** — powerful but geared at larger companies with finance teams. We're built for solo founders.
- **Runway.com** — closest competitor. They're enterprise-focused; we're founder-focused with a free tier.

## Getting started

Free (no signup): founderconsole.ai/simulator
Watch demo: founderconsole.ai/demo
Book a call: founderconsole.ai/book (or email vishesh@founderconsole.ai)
