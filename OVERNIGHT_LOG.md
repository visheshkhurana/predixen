# OVERNIGHT_LOG — FounderConsole

## Session header
- Date: 2026-11-17 (Asia/Dubai). Start 01:24. Stop by 08:00.
- Repo: visheshkhurana/predixen (the live FounderConsole app + marketing). Worktree `~/Fund-Flow-overnight`,
  branch `overnight/2026-11-17` from `origin/main` 4d744787. Named repos founderconsole / founderconsole-landing
  are ARCHIVED and stale; not used. predixen-intelligence-os untouched.
- Run: local Postgres DB `fc_overnight`; launcher `scratchpad/fc-dev.sh` (PORT 5050, FASTAPI 8051,
  CREATE_SCHEMA/RUN_MIGRATIONS/SEED_* true, APP_BASE_URL=localhost so health probes don't hit prod,
  no OpenAI/Razorpay/Resend keys). `npm ci` in the worktree (symlinked node_modules breaks Vite fs allow-list).
- Tests: `.venv/bin/python -m pytest server/tests`; TS: `npx tsx [--test] server/tests/<name>.test.ts`
  (CI list in .github/workflows/pr-checks.yml); types: `npx tsc --noEmit`.
- Baseline: pytest all green except 2 `test_lead_proxy_rate_limit` tests (spawn express; fail on main locally,
  pass in CI). tsc: 2 pre-existing errors in server/storage.ts.
- Test accounts: local only, values in scratchpad `overnight-test-accounts.env` (not in repo).

## Feature inventory
| Feature | Founder job | Status | Evidence | Checked |
|---|---|---|---|---|
| Landing + industry picker | understand fit | works; copy contradicts pricing | /for/d2c, live GET | 01:31 |
| Email signup | get in | works; server errors shown raw ("Request failed (422)") | .test email → 422 toast | 01:33 |
| Onboarding step 1 (company) | set up | works; D2C prefilled; USD default outside India TZ | new acct | 01:35 |
| Onboarding manual entry + Health Check | first value | was wrong ($ labels, burn ≠ dashboard, profitable → "add data"); FIXED 0dd169ce | 2 accounts | 01:41 |
| Onboarding step 4 sim preview | learn | hard-coded P10/P50/P90 unlabelled; FIXED (labelled) | | 01:41 |
| Dashboard /overview | see business | loads; burn agrees; SaaS framing, "AI Estimated" on typed burn, invented CAC/LTV, D2C told 70% GM target | | 01:42 |
| Plan limit at 402 | paid conversion | was generic error; FIXED 8bee2c44 (upgrade dialog → /billing) | paid-mode local instance :5070 | 01:56 |
| Billing page | pay | loads, ₹3,000 Starter; offers 30-day Scale trial (see Blocked) | :5070 | 01:56 |
| Profit per order | D2C core action | works; CM1/2/3, MER, CAC, RTO math checked by hand; empty after onboarding (no prefill) | acct B Oct inputs | 01:57 |
| Account deletion / export | leaving | no self-serve deletion (privacy page says 'request'); financial CSV export exists | openapi | 01:52 |
| Data isolation | safety | works: 92 company GET routes 403/404 cross-account, 401 signed out; 34 object routes no cross-company rows | API probe | 01:47 |

## Backlog (ranked)
In progress (subagents): copilot fallback honesty when AI is down; CAC from D2C months + board export/realtime without invented unit economics.
Next: Profit page prefill from onboarding revenue; KPI tooltip GM targets per industry; outage copy; MRR/ARR labels for non-subscription businesses.

| Rank | Item | Type | I | C | E | Score | Why |
|---|---|---|---|---|---|---|---|
| 1 | Dashboard numbers/labels honest for a new D2C company (typed ≠ "AI Estimated", no invented CAC/LTV, D2C GM target, broken copy) | bug | 5 | 4 | 3 | 6.7 | first screen after onboarding; trust |
| 2 | "Free during public beta" copy vs ₹3,000 live pricing | gap | 4 | 5 | 2 | 10* | landing promise vs paywall (override 4) |
| 3 | Raw "Request failed (422)" on signup/API validation errors | polish | 3 | 5 | 1 | 15 | signup blocker clarity |
| 4 | Onboarding "Connect apps" copy D2C-aware + real count | polish | 3 | 5 | 1 | 15 | D2C founders look for Shopify |
| 5 | Dubai/UAE browser → AED default | polish | 2 | 5 | 1 | 10 | UAE pricing |
| 6 | Onboarding stepper clipped at 1200px | polish | 2 | 5 | 1 | 10 | looks broken |
| 7 | Signup page ignores ?industry | polish | 2 | 4 | 2 | 4 | message match |

## In progress
(see iteration log)

## Shipped
| Item | Repo | Commit | How to test | Watch |
|---|---|---|---|---|
| Signup/form validation errors readable | predixen | 9d629512 | sign up with x@brand.test → 'Please use a real email address…' | |
| Onboarding stepper fits; AED default for UAE; D2C connect copy | predixen | cd7a20c5 | onboarding at 1200px and 375px; Dubai TZ → AED | |
| Dashboard honest: no invented CAC/LTV, surplus as surplus, D2C margin target | predixen | f5b039e5 | /overview as profitable D2C | board export follow-up in progress |
| Public pages: 'Free plan · No credit card' not 'free during public beta' | predixen | 80ec1b0c | curl / /for/d2c /signup /llms.txt | /faq payments-off copy still says beta (gated) |
| Dashboard profit-per-order card for goods businesses | predixen | cc4abd30 | /overview D2C with/without /profit months | |
| Signup panel D2C-aware | predixen | 4c297c8d | /signup?industry=d2c | |
| Admin billing banner reflects payments | predixen | 410d91b7 | admin /admin/billing | not browser-verified |
| Dashboard header/segment tabs wrap on phone | predixen | a1be27c2 | /overview at 375px | |
| Upgrade dialog at plan limit | predixen | 8bee2c44 | needs payments on: 4th sim on Free → dialog → See plans → /billing | PostHog plan_limit_shown / upgrade_click |
| Onboarding health check honest + in founder's currency | predixen | 0dd169ce | Sign up, pick D2C + INR, enter 25L rev/55% GM/9L opex/8L payroll/2L other/3Cr cash → Health check "Not burning", "Monthly Surplus ₹5.8L", labels ₹; dashboard burn -₹5.8L | example FX rates are rough, labelled as estimates |

## Decisions and assumptions
- Treated `predixen` as the FounderConsole app repo despite the "Predixen read-only" line: it is the repo
  founderconsole.ai deploys; the named repos are archived. Branch-only, never main.
- Kept the server's rule that typed opex/other already include COGS (documented, deliberate); fixed the
  onboarding screen to match it and made the field hints say so, instead of changing stored data semantics.

## Blocked
- /billing offers 'Try all features free for 30 days — Scale plan, no card' while marketing dropped the trial; a Free user at the limit can trial instead of paying. Decide: keep trial (then say so on pricing) or hide it. Recommendation: keep a 14-day Starter trial, not Scale.
- No self-serve account deletion (privacy page promises deletion on request). Recommendation: add a 'Delete account' request button next session (irreversible, needs care).
- Free plan advertises 0 connectors but nothing enforces it. Decide: enforce (hurts D2C activation: Shopify
  is the fastest path to real numbers) or change pricing copy. Recommendation: allow 1 connector on Free.
- Headline "a free AI CFO" on /for/d2c etc. while paid plans are live: positioning call.

## Iteration log
| # | Time | Item | Result | Usage |
|---|---|---|---|---|
| 0 | 01:24-01:30 | setup, baseline | ok | fine |
| 1 | 01:30-01:44 | audit signup→dashboard; onboarding health check fix | shipped 0dd169ce | fine |
| 2 | 01:44-01:48 | data isolation probe | no leaks | fine |
| 3 | 01:48-01:52 | 422 messages, stepper/AED/connect copy; delegated dashboard honesty + beta copy | shipped 9d629512, cd7a20c5 | 2 subagents |
| 5 | 01:58-02:05 | reviewed+verified dashboard & copy subagents; committed | f5b039e5, 80ec1b0c; full pytest 1590 pass/2 known; build ok; 55 CI TS steps pass; draft PR #267 for CI | |
| 6 | 02:05-02:13 | D2C profit card, signup D2C panel, admin banner, mobile overview; delegated copilot-fallback + unit-economics-from-D2C | shipped cc4abd30 4c297c8d 410d91b7 a1be27c2 | 2 subagents |
| 4 | 01:52-01:58 | plan-limit upgrade dialog; audit billing, profit, leaving | shipped 8bee2c44 | fine |
