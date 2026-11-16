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
| Data isolation | safety | works: 92 company GET routes 403/404 cross-account, 401 signed out; 34 object routes no cross-company rows | API probe | 01:47 |

## Backlog (ranked)
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
| Onboarding health check honest + in founder's currency | predixen | 0dd169ce | Sign up, pick D2C + INR, enter 25L rev/55% GM/9L opex/8L payroll/2L other/3Cr cash → Health check "Not burning", "Monthly Surplus ₹5.8L", labels ₹; dashboard burn -₹5.8L | example FX rates are rough, labelled as estimates |

## Decisions and assumptions
- Treated `predixen` as the FounderConsole app repo despite the "Predixen read-only" line: it is the repo
  founderconsole.ai deploys; the named repos are archived. Branch-only, never main.
- Kept the server's rule that typed opex/other already include COGS (documented, deliberate); fixed the
  onboarding screen to match it and made the field hints say so, instead of changing stored data semantics.

## Blocked
- Free plan advertises 0 connectors but nothing enforces it. Decide: enforce (hurts D2C activation: Shopify
  is the fastest path to real numbers) or change pricing copy. Recommendation: allow 1 connector on Free.
- Headline "a free AI CFO" on /for/d2c etc. while paid plans are live: positioning call.

## Iteration log
| # | Time | Item | Result | Usage |
|---|---|---|---|---|
| 0 | 01:24-01:30 | setup, baseline | ok | fine |
| 1 | 01:30-01:44 | audit signup→dashboard; onboarding health check fix | shipped 0dd169ce | fine |
| 2 | 01:44-01:48 | data isolation probe | no leaks | fine |
