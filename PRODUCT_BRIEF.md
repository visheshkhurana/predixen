# FounderConsole — product brief (overnight 2026-11-17)

**Repo note.** The brief named `visheshkhurana/founderconsole` and `-landing`. Both are archived
(last push Mar/Apr 2026) and are not what founderconsole.ai runs. The live app *and* its marketing
pages are served from `visheshkhurana/predixen` (Express + Vite React + FastAPI + Postgres, deployed
on Railway). Work tonight is on branch `overnight/2026-11-17` of that repo only. Stack is not
Supabase/Vercel: auth and isolation are enforced in the FastAPI layer (no RLS).

## Promise
"Know which orders actually make you money." An AI CFO for founders: runway, burn, contribution
margin (CM1/CM2/CM3 for D2C), Monte Carlo "what if" simulations, an AI copilot, investor tools.
Homepage asks "What kind of business do you run?" and personalises (`/for/d2c`, saas, …).

## Who
Primary market (owner, 2026-11-04): **Indian D2C brands**, then SaaS/early-stage, then UAE/US.
Small team, impatient, numbers in ₹ lakh/crore, thinks in CM2, RTO, COD, ad spend.

## Core action and first value
Create company → enter (or upload/connect) monthly numbers → **Health Check: burn, runway,
health score for *their* company** → dashboard. First value = the Health Check / dashboard showing
correct numbers for their own business, in their currency, in one sitting.

## Money
Free plan (3 simulations, 10 copilot messages/month). Starter ₹3,000/mo India, $39 US, AED 149 UAE
via Razorpay, live since 2026-11-15. Currency follows the company currency.

## Landing vs product mismatches found
1. Homepage, /for/* pages, llms.txt and JSON-LD say **"Free during public beta"** / "a free AI CFO"
   while /pricing and the same homepage say ₹3,000/month. Live site confirmed by GET.
2. Pricing lists Free = **0 connectors**; the app does not enforce it (free users can connect).
3. Onboarding "Connect apps" pitches Stripe/QuickBooks/Gusto "and 20+" to D2C founders; the app has
   38 connectors incl. Shopify, Shiprocket, Razorpay, Meta Ads, Tally, Zoho CRM.
4. Signup page ignores `?industry=d2c` and sells Monte Carlo to everyone.
