# Morning report: FounderConsole overnight, 2026-11-17

## 1. Summary
A new Indian D2C founder now goes from the D2C landing page to a dashboard with correct numbers, in rupees, in one sitting (about 2–3 minutes of typing). Before tonight:
- onboarding labelled amounts in $;
- onboarding's burn figure disagreed with the dashboard;
- the dashboard showed invented CAC/LTV and called typed numbers "AI Estimated";
- the AI copilot quoted those invented numbers back as fact.

Paid conversion has an upgrade path at the moment of need: a Free founder who hits the limit now gets an upgrade dialog instead of an error. The public site no longer promises "free during public beta" while charging ₹3,000/month.

All work is on branch `overnight/2026-11-17`: 21 shipped commits, 1 reverted pair, CI green. Draft PR #267 exists for CI only. Nothing is merged or deployed.

## 2. Needs action from you first
1. **Repo mismatch.**
   - The brief named `founderconsole` and `founderconsole-landing`. Both are **archived** (last push Mar/Apr 2026) and are not what founderconsole.ai runs.
   - I worked in **`visheshkhurana/predixen`**, which serves the live app and its marketing pages, on a branch only. `predixen-intelligence-os` was not touched.
   - The brief also expected Supabase/Vercel. The real stack is Express + FastAPI + Postgres on Railway, so isolation lives in the API, not in row-level security.
2. **Review and merge PR #267** (`gh pr ready 267`, then merge). Merge order relative to your other open PRs:
   - PR #258 (benchmarks web search) makes the live-benchmark path work, which the benchmark-honesty change relies on. Merge it first or alongside.
   - PR #265 (Excel label column) touches `excel_extractor.py`, but in different lines from #267, so it should merge cleanly.
3. **Pricing decisions**: see section 7.
4. **Check your environment.** Your shell exports live Gemini, OpenRouter, xAI, Mistral, DeepSeek, OpenAI and Anthropic keys.
   - My first local launcher cleared only the OpenAI and Anthropic keys.
   - The surviving server logs show **no successful outbound model call**: only 25 Anthropic requests, all rejected (401) because that key was cleared.
   - The logs from the first ~40 minutes were overwritten on restart, so this can't be fully proven. If you see tiny overnight usage on Gemini or OpenRouter, that is the cause.
   - The launcher now clears all of them.
5. **Clean-up (optional).** The local test DB is `fc_overnight` (drop it with `dropdb fc_overnight`) and the worktree is `~/Fund-Flow-overnight`. Test-account passwords are only in the session scratchpad.

## 3. Shipped (branch `overnight/2026-11-17`; each verified in a local run unless noted)
| # | Change | Why it matters to a founder | Commit | Test it in under a minute |
|---|---|---|---|---|
| 1 | Onboarding health check: real burn (server COGS rule), labels in the chosen currency, a profitable company sees "Not burning" instead of "add data" | The first number a founder sees was wrong or contradicted the dashboard | 0dd169ce | Sign up, pick D2C + INR, enter ₹25L revenue / 55% GM / ₹9L opex / ₹8L payroll / ₹2L other / ₹3Cr cash. Expect ₹ labels, "Monthly Surplus ₹5.8L", and the dashboard agreeing. |
| 2 | Readable validation errors | Signup used to show "Request failed (422)" | 9d629512 | Sign up with `x@brand.test`. Expect "Please use a real email address…". |
| 3 | Onboarding step bar fits; AED default for UAE time; D2C-relevant "Connect apps" copy | Clipped UI; UAE founders would be billed in USD | cd7a20c5 | Open onboarding at 1200px and 375px. |
| 4 | **Upgrade dialog at plan limit** (402 → "See plans" → /billing), plus PostHog `plan_limit_shown` / `upgrade_click` | The paid-conversion moment used to be a dead end | 8bee2c44 (+e0b7b339 for the simulate workspace) | Needs payments on: use up 3 sims on Free, run a 4th. |
| 5 | Dashboard: no invented CAC/LTV/LTV:CAC; a surplus is shown as a surplus; D2C margin target 50%+ | It showed ₹20K CAC and 14.3x LTV:CAC from nothing | f5b039e5 | D2C account /overview: CAC "N/A · needs marketing spend…". |
| 6 | Public pages: "Free plan · No credit card required" instead of "free during public beta" | The live homepage said free and ₹3,000 at once | 80ec1b0c | `curl /for/d2c` gives no "public beta". |
| 7 | Profit-per-order card on the dashboard for goods businesses | The D2C core screen used to be sidebar-only | cc4abd30 | D2C /overview, with and without /profit data. |
| 8 | Signup panel speaks D2C when arriving from /for/d2c | Message match from the landing page | 4c297c8d | Open /signup?industry=d2c. |
| 9 | Admin billing banner reflects payments being live | Said "Free beta, no billing" | 410d91b7 | /admin/billing (not browser-verified: no local admin login). |
| 10 | Dashboard header and tabs wrap on a phone | Clipped at 375px | a1be27c2 | /overview at 375px. |
| 11 | **Copilot is honest when the AI is down**: notice, low confidence, UNVERIFIED | It used to return a canned "Confidence: HIGH, VERIFIED" answer | aa1833af | /copilot with no AI key: red "AI assistant unavailable" alert. |
| 12 | CAC from the founder's own D2C month; board deck and realtime feed stop quoting invented unit economics | Investor exports used to carry made-up numbers | 26231159 | D2C account with October /profit data: CAC ₹417 "Computed". |
| 13 | Board deck in the company's currency; real burn instead of $0 | An INR deck said "MRR $2,500,000", "Net burn $0" | 4b011cf2 | test_board_export_currency.py |
| 14 | "Monthly Revenue" / "Annual Run-Rate" for D2C instead of MRR/ARR | SaaS jargon for a D2C brand | 7e9a6e3f | D2C /overview |
| 15 | Benchmark card says when it is showing generic SaaS defaults | It graded 55% D2C margin against a "70% industry report" | 8f865c43 | D2C /overview with no live benchmark search |
| 16 | Copilot decision questions answered by the model (grounded in simulations) instead of only a canned plan | The headline AI feature didn't answer the question | bf05985d | **Only tested with a fake router**: watch the first real answers |
| 17 | Fixes from the independent review: payback no longer built on an invented customer book; unknown burn ≠ "break-even"; partial-failure confidence; AI-budget notice; draft kept on 402; currency icon | Wrong numbers in edge cases | e0b7b339 | see the commit |
| 18 | Unreadable uploads give a plain next step instead of a library traceback | Raw errors on import | 7e463d93 | Upload a non-Excel file as .xlsx |
| 19 | AI copilot context never gets invented CAC/LTV/customers; unknowns are spelled out | The model could tell a founder "your CAC is ₹20K" | 795add1b | test_copilot_unit_economics.py |
| 20 | Copilot context in the company's currency; surplus wording | The model was primed with "$2,500,000" for ₹25L | af1381a7 | same |
| 21 | Timestamps: "1 minute ago", not "about 4 hours ago" | Data looked stale to everyone east of UTC | 49b68611 | Finish onboarding and look at the card footers |

## 4. Founder journey scorecard (new D2C founder, local run)
| Stage | Before | After |
|---|---|---|
| Landing | Promise clear; "free during beta" contradicted ₹3,000 pricing | Consistent: free plan + paid pricing |
| Signup | Generic SaaS pitch; raw 422 errors | D2C pitch from /for/d2c; readable errors |
| Onboarding | $ labels for an INR company; burn ≠ dashboard; profitable shown as "add data"; unlabelled fake P10/P50/P90 | ₹ labels; same numbers as the dashboard; honest profitable state; example output labelled |
| First value | Wrong or contradictory numbers | Correct burn, runway and health in 16s automated (about 2–3 min typed) |
| Core workspace | Invented CAC/LTV, "AI Estimated" on typed data, SaaS labels, 70% margin target, "4 hours ago" | Real or N/A values, Computed badges, D2C labels, Profit card, correct timestamps |
| Payment | A limit hit was a dead end | Upgrade dialog leads to /billing (₹3,000 Starter) |
| Return | Weekly digest and briefing already exist | Unchanged |

## 5. Security and data isolation
- **Checked:**
  - 92 company-keyed GET routes, requested as a second founder: all 403/404.
  - 34 object-id routes: no other company's rows.
  - The same routes signed out: 401/429.
  - Password reset doesn't reveal whether an account exists.
  - Logout invalidates the session.
  - Inviting into another founder's company is refused (403).
  - No live keys in client code.
  - The independent review confirmed the new D2C queries are scoped to the authorized company.
- **Found:** no leak.
- **Not covered:** cross-account *write* routes beyond invites, and connector OAuth callbacks.
- **Also noticed:** the app's health probes call production by default (`APP_BASE_URL` defaults to founderconsole.ai) even from a local run. They are read-only GETs.

## 6. Landing versus product
- **Fixed:** "Free during public beta" vs ₹3,000 live pricing (static pages; the /faq answer is gated and switches when payments are on).
- **Still open:**
  - "a free AI CFO" headlines while paid plans are live. This is positioning, so it's your call.
  - Pricing says Free = 0 connectors, but nothing enforces it.
  - "Role-based access control" appears on the signup page, yet teammates can't use a shared company (section 7).
  - The connector count says 36; it becomes 37 when PR #266 (Razorpay connector) merges.

## 7. Blocked (your decision)
1. **Team access (reverted tonight).**
   - What happened: I mounted Settings → Team. The invite → join loop works, and the invitee becomes an editor. But company routes only check `Company.user_id`, so the teammate's company list is empty and most company routes return 403/404.
   - Decision needed: whether to build membership-aware access, which is security-sensitive and touches about 100 routes.
   - Recommendation: yes, in one dedicated PR with a cross-account test sweep. The invite API, acceptance flow, hooks and `TeamWorkspace` component are already built.
   - Also: the invite API should return the join link when email fails (I tested this, then reverted it with the tab), and Resend never actually emails.
2. **30-day Scale trial on /billing.** Marketing dropped the trial, but the billing page still offers it, and a Free user at the limit can trial instead of paying. Recommendation: keep a shorter Starter trial, or hide it.
3. **Free = "0 connectors" isn't enforced.** Recommendation: allow 1 connector on Free (Shopify is the fastest route to real D2C numbers) and update the copy.
4. **Copilot quota on failed answers.** A Free user's message counts against the 10/month even when the AI was unavailable. Recommendation: don't count it.
5. **No self-serve account deletion.** The privacy page says deletion is by request. Recommendation: add a "request deletion" button.
6. **What "Opex" means in onboarding.** The server treats typed opex/other as already including COGS (documented and deliberate). I clarified the hint text rather than changing what is stored. Confirm that's the semantics you want.

## 8. Decisions made without you
- Treated `predixen` as the FounderConsole repo (see 2.1).
- For copy that must be true whether payments are on or off, used "Free plan · No credit card required". Headlines were left untouched.
- Hid the static SaaS margin benchmark from goods businesses instead of inventing D2C benchmark numbers.
- Old truth scans without an `_estimated_metrics` list have their unit economics treated as invented. Every version of the scan computes them from assumptions, and scans refresh daily.
- Each subagent's work was reviewed and checked by me in the running app or API before committing. An independent reviewer read the whole branch; no blockers were found and all should-fix items were fixed.

## 9. Reverted or failed
- **Settings → Team (3281ca66, reverted in 0da7ac59).** It worked as UI, but the end-to-end check showed invited teammates can't access the company. Lesson: the backend needs membership-aware access first (section 7.1).
- **No live AI answer for the decision-route change.** The local free model returned empty content, so it is verified only with a fake router.

## 10. Next session (ranked)
1. **Membership-aware company access + Team tab**: unlocks co-founder use; the UI is already built.
2. **Merge #255–#258, #265, #266, #267**, then check a real copilot answer and a real benchmark search in production.
3. **Prefill /profit from onboarding and connectors** (Shopify/Shiprocket/Razorpay) so D2C founders reach CM2 without retyping.
4. **Sweep other screens for naive-UTC date parsing** and leftover truth-scan CAC readers (workstreams, intelligence graph, data health, calibration).
5. **Enforce or relabel plan limits** (connectors, trial) per your section 7 decisions.
- **Predixen connection:** the copilot's decision answers now run on the simulation engine's levers. Running Monte Carlo on the D2C contribution-margin inputs (RTO, CAC, ad spend) would be the natural next step.

## 11. Numbers
- **Session:** 01:24 to ~03:55 Asia/Dubai, stopped early. The remaining backlog is either your decision (section 7) or low value, which is the brief's stop condition.
- **Shipped:** 21 changes, 1 reverted. 11 developer subagents (7 builders, 1 independent reviewer, plus re-checks), each verified by me.
- **Python tests:** before, 1590 passed / 2 known local failures; after, **1646 passed** / the same 2. **TS CI steps:** 52 → **57** passing. Type-check 0 errors; build passes; PR #267 CI green.
- **Time lost to throttling:** none.
