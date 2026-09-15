# Team State — updated 16 Sep 2026 ~03:41 GST by Chief of Staff (User Research write-up)

## Staffing (ORG-22 · Phase 1+2 · 18 agents)
**Active (18):** Phase 1 — Chief of Staff · Reviewer · Release Manager · Analytics · Conversion Eng · SEO & AI Search · Reliability · QA Engineer · Finance Watcher. Phase 2 — Product Lead · Engineering Lead · Growth Lead · App Engineer · Modeling & AI · Connectors · Lifecycle · User Research · Data Trust.
**Phase 2 start:** Vishesh **OVERRIDE** 16 Sep 00:42 GST (Bot). Metric gate **not met** — `lead_captured` still 0, identity/signup unverified. Log in DECISIONS.md. Do **not** treat the tripwire as satisfied.
**Phase 3 parked (do not spawn):** Content · Partnerships · Paid Acquisition · Support.

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11 | lead_captured: 0 (**taxonomy miss** — Conversion Eng 90d: events=0 persons=0, project 522965, 16 Sep ~03:39 GST)
Funnel 30d (Conversion Eng, project 522965): calculator_used 11 · signup_view 22 · cta_click 16 · signup_start 3. `$rageclick` 60d: **4 sessions / 9 events** — walkthrough folded (pasteable). **0 `$rageclick` since Sep 15 clearable deploy.**
(Source: Conversion Eng PostHog proof 16 Sep; prior week-of-13 HANDOVER devices/sessions until Analytics refresh)
GitHub tip: `48156d54` (`#20` OVERRIDE on main). `#16` **live**. `#14` control still **200 HTML** (must 404). P0 **held by Vishesh**. Bundle `index-eWXmctMP.js`. Open product PRs (not auth): `#17` ADRs · `#18` Tally sync · `#19` NOT_AVAILABLE · `#21` sample first-run · `#22` FAQ E9. Stale `#1`/`#2`/`#3` ignore unless Vishesh says.
**Auth locks CLOSED (evidence):** `/api/events` GET+POST → 401; `/admin/ai-governance` → 401; GET `/api/feedback` → 401; company forecasting → 401.
**OPEN CRITICAL (CoS curl 16 Sep 00:32 GST; still live after #12/#13):** GET `/api/notifications/email-stats` → **200**, 98 rows, keys include `to`; GET `/api/integrations/available` → **200**; GET `/api/integrations/companies/1/status` → **200**; GET `/api/templates/` → **200**; POST `/api/templates/companies/1/apply/1` → **404** (not 401). “Created scenario 55” **not re-proven** this pass — do not treat as verified write.

## Org map (phase 1+2)
| Role | Agent | Pod / gate | Autonomy | Push to main? |
| Chief of Staff | Chief of Staff | Exec | autonomous (records only) | no |
| Product Lead | Product Lead | Exec | within policy | no |
| Engineering Lead | Engineering Lead | Exec | within policy | no |
| Growth Lead | Growth Lead | Exec | within policy | no |
| Finance Watcher | Finance Watcher | Exec | read-only | no |
| Reviewer (Gate 1) | Reviewer | Gates | autonomous | no |
| Data Trust (Gate) | Data Trust | Gates | within policy | no |
| Release Manager (Gate 2) | Release Manager | Gates | autonomous | YES — only |
| Conversion Eng | Conversion Eng | Build | autonomous | no |
| App Engineer | App Engineer | Build | autonomous | no |
| Modeling & AI | Modeling & AI | Build | autonomous | no |
| Connectors | Connectors | Build | autonomous | no |
| QA Engineer | QA Engineer | Build | autonomous | no |
| Reliability | Reliability | Build | autonomous | no |
| Analytics | Analytics | Growth | autonomous (522965 readable; identity PR open) | no |
| SEO & AI Search | SEO & AI Search | Growth | within policy | no |
| Lifecycle | Lifecycle | Growth | within policy | no |
| User Research | User Research | Customer | autonomous | no |

Coordination: this file + HANDOVER.md + ORG-22.md + DECISIONS.md + AUTONOMY.md. Rooms: FounderConsole Exec · Build · Growth · Gates (Phase 1 rooms remain). Monday 09:00 GST council: CoS chairs Product / Engineering / Growth Leads + Finance Watcher.

## In flight
| Agent | Item | Files claimed | PR | Status |
| Product Lead | Define “activated founder” + rank first 3–5 bets | agents/specs/ | — | starting (within policy) |
| Engineering Lead | Three ADRs accept/kill at Monday council | docs/adr/ | [#17](https://github.com/visheshkhurana/predixen/pull/17) | **Proposed** — Gate 1→2 when ready. Monday accept/kill. |
| Growth Lead | Monday: Lifecycle unsubscribe/cap drafts (E2 remainder **closed live**) | agents/GROWTH-BACKLOG.md | — | E1/E3 folded. Ads off. PostHog is a blocker not a bet. |
| App Engineer | Sample first-run + AskAIButton restore; note onboarding number-input rage | App.tsx / sample_data / onboarding | [#21](https://github.com/visheshkhurana/predixen/pull/21) | #21 open Gate 1→2. Conversion Eng: Sep 8 `/onboarding` rage on manual financial Number inputs (same snap pattern as calc); visitor still completed to `/overview`. Consider clearable string-state on onboarding start — **not** a second calc PR. |
| Modeling & AI | Fabrication→NOT_AVAILABLE guard | server/copilot/trust.py, api/copilot.py, evals | [#19](https://github.com/visheshkhurana/predixen/pull/19) | Gate 1 **PASS**; waiting **Data Trust** (LLM output path) before RM. **No** prompt/routing until merge. |
| Connectors | Tally period flows for monthly P&L (not unbounded closing) | server/truth/truth_scan.py | [#18](https://github.com/visheshkhurana/predixen/pull/18) | open — Gate 1→2 when ready |
| Lifecycle | Lead nurture within templates/caps | server/email | — | starting (within policy) |
| User Research | Rage-click write-up **done** | [agents/research/rage-click-writeup-2026-09-16.md](research/rage-click-writeup-2026-09-16.md) | this PR | Four sessions / nine events. Themes: runway calc under gclid (2/5), post-OAuth onboarding (1/3), survival-sim embed CTA labeled (1/1). Not claiming `lead_captured`. P0: Conversion Eng watch sessions 1–2 before funnel change. Aug 19 TTL ~18 Sep. |
| Data Trust | Gate PRs that touch creds/PII/LLM/auth | — | — | starting; P0 trio **not** theirs to lock |
| SEO & AI Search | E9 `/faq` free-tool SSR links | server/seo-prerender.ts | [#22](https://github.com/visheshkhurana/predixen/pull/22) | open (Bot: draft). `/features` already linked. Do not reopen #16. |
| Reliability | Deploy-landed monitor live control | server/services/deploy_landed.py | `#14` `cb04e17d` | **code on main; control FAILED live** — `/assets/index-DEPLOYMONITOR-CONTROL-MISS.js` → **200 text/html** (must be 404) |
| QA Engineer | CI auto-run on every PR | .github/workflows/pr-checks.yml | #13 shipped dispatch-only | follow-up needs Vishesh Actions minutes |
| Reviewer | Remaining reachable-route sweep | — | — | P0 trio **human-hold** |
| Analytics | devices≈sessions; server-side `lead_captured`; signup_completed | — | — | Conversion Eng proved project **522965** readable. Own identity refresh still needed. **Owner of server-side `lead_captured` PR** (Conversion Eng agrees; holding client survival-sim). |
| Conversion Eng | Rage walkthrough done; next PR after `lead_captured` proof | none locked | — | Calc `#cash`/`#revenue`/`#expenses`/`#growth` Number("") snap — clearable shipped Sep 15; **0 rage since**. Survival-sim rage on **Embed runway widget** (post Download) = strongest remaining. Onboarding same number-input pattern (visitor reached `/overview`). No second clearable PR. Survival-sim email **held** until Analytics taxonomy proof; then one PR (embed CTA or email). Aug 19 calc TTL ~3d (expires ~18 Sep). |
| Finance Watcher | Spend register | records | — | $ **UNKNOWN** (Railway/LLM connectors not connected). Flags recurring infra / Railway plan / vendor switch. |
| Chief of Staff | Monday council prep + Type 1 batch + research docs PR | agents/DECISIONS.md · agents/research/ | this PR | `#20` shipped `48156d54`. Research write-up landing in this PR. |
| — | P0 auth lock trio | templates/integrations/notifications | none | **frozen** — Vishesh held |

## Blocked
| Item | Blocked on | Since |
| P0 auth lock trio | **Vishesh held** | 16 Sep |
| Analytics identity + `lead_captured` taxonomy | Server-side event PR + identity merge (project 522965 **is** readable — Conversion Eng proof) | 15 Sep |
| QA CI auto-run | Vishesh Actions minutes (#13 is dispatch-only) | 16 Sep |
| Phase 3 spawn | 4 weeks WoW activated-founder growth + pricing decision | standing |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
| Phase 2 OVERRIDE docs (STATE/CHARTER/DECISIONS/AUTONOMY/HANDOVER) | `#20` `48156d54` | on origin/main; `git show 48156d54:agents/DECISIONS.md` has OVERRIDE row | org records |
| `/ai-cfo` free-tool SSR links + WebApplication JSON-LD | `#16` `34ce49e7` | CoS Googlebot 00:47 GST: hrefs=runway/survival/default-alive/auth; ld WebApplication=1; health uptime 57.7s | E2 live |
| CoS STATE/HANDOVER fold after #12 | `#15` `295aedb5` | **on main but still Phase 1 nine / Phase 2 parked** — override not in this commit | records incomplete |
| Dispatch-only RM check suite | `#13` `3c2f1094` (+ docs `77410c22`) | `pr-checks.yml` `on: workflow_dispatch` only — **not** auto on PR | QA CI scaffold |
| SEO SSR cross-links + contact + `/ai-cfo` sitemap | `#12` `9d559d17` | CoS Googlebot 00:40 GST pasteable below | SEO pack |
| Phase 1 ORG-22 / CHARTER / STATE | `#11` `d4b3bcb1` | on origin/main | org records (Phase 2 override **not** in this commit) |
(see prior rows through #9/#10)

### Pasteable evidence — #12 SSR cross-links (2026-09-15T20:39:55Z Googlebot)
```
sitemap ai-cfo=1
/ hrefs=6 chars=3264
/pricing hrefs=5 chars=1088
/tools/runway-calculator hrefs=4 chars=2086
/default-alive hrefs=4 chars=1895
/about hrefs=6 chars=1573
/contact hrefs=9 chars=1195 meta=143
health uptime≈94.3s; tip `9d559d17`; bundle index-eWXmctMP.js
CoS recheck 00:40 GST Googlebot: sitemap loc=36 ai-cfo=1 privacy=0 terms=0; contact meta_len=143; same href pattern. Match.
```

### Pasteable evidence — #13 CI workflow (2026-09-16)
```
on main: .github/workflows/pr-checks.yml + scripts/tsc-error-budget.sh
trigger: workflow_dispatch only (no pull_request/push/schedule)
tip: 3c2f1094; docs 77410c22
```

### Pasteable evidence — SEO re-audit post #12 (SEO & AI Search, 00:42 GST Googlebot)
```
Verdict PASS vs #12/#9 claims. sitemap loc=36 ai-cfo=1 privacy=0 terms=0.
/ hrefs=6 chars=3264; /pricing 5/1088; runway 4/2086; default-alive 4/1895; about 6/1573; contact 9/1195 meta=143.
Remaining after #16 live: /faq only /contact. `/features` survival omission closed live (hrefs=/auth /tools/runway-calculator /default-alive /survival-simulator).
Artifact: content-drafts/seo-audit-post-pr12.md
```

### Pasteable evidence — #14 control + #16 live (CoS 16 Sep 00:45 GST)
```
git tip 34ce49e7  (#16) ; #14 cb04e17d ; #15 295aedb5
GET /ai-cfo Googlebot → ssr=1 hrefs=[] ld_n=0 WebApplication=0  (twice; health uptime 8.1s then 6.8s — Railway restarting)
GET /assets/index-DEPLOYMONITOR-CONTROL-MISS.js → 200 text/html charset=utf-8 len=4761  (MUST be 404)
GET /assets/index-eWXmctMP.js → 200 application/javascript
GET /assets/runway-calculator-dxpJG9rN.js → 200, lead_captured substring present
origin/main agents/DECISIONS.md — missing; CHARTER still “Phase 2 starts when metric gate”
```

### Pasteable evidence — #16 LIVE (CoS 16 Sep 00:47 GST Googlebot)
```
/ai-cfo hrefs=['/tools/runway-calculator', '/survival-simulator', '/default-alive', '/auth'] ld_n=1 WebApplication=1
health uptime_seconds=57.7 routers_loaded=true
prior 00:45 GST 0-link probe was mid-restart (uptime 6.8–8.1s) — not a kill
#14 control still 200 text/html
```

## Corrections — things we believed that were false
| Believed | Actually | Found by | Cost |
| Pending §3 uncommitted forever | Shipped `4ef45867` 15 Sep | Bot/RM | month of dead tools |
| Prefix fix alone is safe | `/api/events` public until #6 | Audit 15 Sep | live ID leak window |
| Auth locks closed everything | templates/integrations/notifications still open | Reviewer 16 Sep | live PII + unauth catalogs |
| email-stats is private | GET `/api/notifications/email-stats` **200**, 98 emails, field `to` present | CoS curl 00:32 GST | live recipient leak |
| `/api/integrations/*` locked | GET available **200**; GET companies/1/status **200** | CoS curl 00:32 GST | stranger sees catalog + company 1 |
| templates apply not reachable | GET `/api/templates/` **200**; POST apply/1 → **404 not 401** | CoS curl 00:32 GST | path runs unauth; write-to-scenario-55 **unverified** |
| Bundle hash must change for backend/SSR | Auth/SSR can land with same `index-*.js` | Bot 15 Sep | wrong deploy signal |
| Phase 2 waits on metric gate | Vishesh OVERRIDE 16 Sep started Phase 2 with gate unmet | Bot | tripwire bypassed; do not spawn Phase 3 the same way |
| #15 would flip Phase 2 live on GitHub | `#15` was still Phase 1 parked; **fixed by `#20` `48156d54`** | CoS / RM | GitHub now matches override |
| #16 merge = live `/ai-cfo` links | 00:45 GST 0 hrefs was mid-restart (uptime ~7s); **live at 00:47 GST** uptime 57.7s | CoS curl | wait for uptime before citing deploy |
| `/features` still omits `/survival-simulator` after #16 | live Googlebot `/features` hrefs include runway, default-alive, survival | CoS curl 00:47 GST | false next-gap |
| #14 control must 404 | fake asset returns **200 HTML** (SPA) | CoS curl 00:45 GST | monitor would go control-failed / green-blind |

### Pasteable evidence — Conversion Eng PostHog (project 522965, 16 Sep ~03:39 GST)
```
lead_captured 90d: events=0 persons=0 (taxonomy miss). Agree Analytics server-side PR; holding survival-sim capture.

$rageclick 60d → 4 sessions / 9 events:
1. 01a08122… /onboarding 8 Sep — 3 rage · https://us.posthog.com/project/522965/replay/01a08122-0d38-7eab-9dc6-7625e18e89ee
2. 01a06c9b… /tools/runway-calculator 4 Sep (gclid) — 3 rage · https://us.posthog.com/project/522965/replay/01a06c9b-febd-7426-9c7d-0451f46ee435
3. 01a0316e… /survival-simulator 24 Aug (chatgpt.com) — 1 rage on "Embed the runway widget on your site" · https://us.posthog.com/project/522965/replay/01a0316e-ea67-71b1-9b64-b9929db94189
4. 01a01a87… /tools/runway-calculator 19 Aug (gclid) — 2 rage · TTL~3d · https://us.posthog.com/project/522965/replay/01a01a87-a5b1-7fa5-bdd3-d03b91bf441b

Funnel 30d: calculator_used 11, signup_view 22, cta_click 16, signup_start 3.
```

### Pasteable evidence — Conversion Eng rage walkthrough (16 Sep ~03:40 GST)
```
Calculator (Aug 19 + Sep 4): all rage on inputs #cash #revenue #expenses #growth
  (change+click bursts = old Number("") snap). Clearable string-state shipped Sep 15 Section 3;
  0 $rageclick since that deploy. No second clearable PR.

Survival-sim (Aug 24): rage on "Embed the runway widget on your site" after Download image —
  strongest remaining conversion-owned friction.

Onboarding (Sep 8): same number-input rage on manual financial entry; visitor completed to /overview.
  Note for App Eng / onboarding start.

Aug 19 calc recording TTL ~3d (expires ~18 Sep).

Still held: survival-sim one-field email until Analytics proves lead_captured in taxonomy.
After proof: one PR — likely survival-sim embed CTA (or email capture if that still ranks first).
```

### Pasteable evidence — User Research rage write-up (16 Sep ~03:45 GST)
```
Project 522965 · event=$rageclick · last 60d → 9 events / 4 sessions
Paths: /onboarding×3, /tools/runway-calculator×5, /survival-simulator×1
Only labeled element: "Embed the runway widget on your site" (session 3)
Recording metadata fetched via query-session-recordings-list for all 4 IDs
lead_captured: do not claim (Conversion Eng 0/0 90d)
Artifact: agents/research/rage-click-writeup-2026-09-16.md
```
