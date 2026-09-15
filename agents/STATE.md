# Team State — updated 16 Sep 2026 ~00:44 GST by Release Manager

## Staffing (ORG-22 · Phase 1 · 9 agents)
**Active:** Chief of Staff · Reviewer · Release Manager · Analytics · Conversion Eng · SEO & AI Search · Reliability · QA Engineer · Finance Watcher  
**Phase 2 parked (do not spawn):** Product Lead · Engineering Lead · Growth Lead · App Engineer · Modeling & AI · Connectors · Lifecycle · User Research · Data Trust  
**Phase 3 parked:** Content · Partnerships · Paid Acquisition · Support  

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11 | lead_captured: 0 (never seen)
(Source: HANDOVER week of 13 Sep — Analytics must refresh **after** PostHog connector)
GitHub tip: `cb04e17d` (#14 deploy-landed) after `#15` `295aedb5`. #16 ai-cfo SEO awaiting Gate 1. P0 auth Vishesh-held.
**Auth locks CLOSED (evidence):** `/api/events` GET+POST → 401; `/admin/ai-governance` → 401; GET `/api/feedback` → 401; company forecasting → 401.
**OPEN CRITICAL (CoS curl 16 Sep 00:32 GST; still live after #12 docs/SEO):** GET `/api/notifications/email-stats` → **200**, 98 rows, keys include `to`; GET `/api/integrations/available` → **200**; GET `/api/integrations/companies/1/status` → **200**; GET `/api/templates/` → **200**; POST `/api/templates/companies/1/apply/1` → **404** (not 401). “Created scenario 55” **not re-proven** this pass — do not treat as verified write.

## Org map (phase 1)
| Role | Agent | Status | Push to main? |
| Chief of Staff | Chief of Staff | active (records) | no |
| Reviewer (Gate 1) | Reviewer | active | no |
| Release Manager (Gate 2) | Release Manager | active | YES — only |
| Analytics | Analytics | active / blocked PostHog | no |
| Conversion Eng (ex Product) | Conversion Eng | active | no |
| SEO & AI Search (ex Growth) | SEO & AI Search | active | no |
| Reliability | Reliability | active | no |
| QA Engineer | QA Engineer | active (new) | no |
| Finance Watcher | Finance Watcher | active (new, read-only) | no |

Coordination: this file + HANDOVER.md + ORG-22.md. Rooms: FounderConsole Phase 1 + Core/Ops.

## In flight
| Agent | Item | Files claimed | PR | Status |
| SEO & AI Search | Re-audit post #12 | — | — | **#12 live**; re-audit next |
| Reliability | Deploy-landed monitor | server/services/deploy_landed.py | [#14](https://github.com/visheshkhurana/predixen/pull/14) | in review (control must 404) |
| QA Engineer | Dispatch-only CI | .github/workflows/pr-checks.yml | [#13](https://github.com/visheshkhurana/predixen/pull/13) | Gate 1 PASS; with RM; still dispatch-only |
| Reviewer | Remaining reachable-route sweep | — | — | P0 trio **human-hold** |
| Analytics | devices≈sessions; lead_captured; signup_completed | — | — | **blocked** PostHog |
| Conversion Eng | Rage-click replays → one change | — | — | blocked on replay connector |
| Finance Watcher | Spend register | records | — | $ **UNKNOWN** |
| Chief of Staff | DECISIONS.md + AUTONOMY.md follow-up | agents/ | later | stubs on shared box |
| Connectors | Rank use→activation; fix top /connectors failure | server/api/connectors.py, server/connectors/tally.py | [#18](https://github.com/visheshkhurana/predixen/pull/18) | claimed — Tally first-sync only |
| — | P0 auth lock trio | templates/integrations/notifications | none | **frozen** — Vishesh held |

## Blocked
| Item | Blocked on | Since |
| P0 auth lock trio | **Vishesh held** | 16 Sep |
| Analytics identity + replay | PostHog connector | 15 Sep |
| QA CI auto-run | Vishesh Actions minutes | 16 Sep |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
| Deploy-landed monitor (hash+body, control must fail) | `#14` `cb04e17d` | files on main; pytest below | reliability |
| CoS STATE/HANDOVER fold after #12 | `#15` `295aedb5` | on main | records |
| SSR cross-links + contact enrich + /ai-cfo sitemap | `#12` `9d559d17` | RM Googlebot 20:39Z pasteable above | SEO pack |
| Phase 1 ORG-22 / CHARTER / STATE | `#11` `d4b3bcb1` | on origin/main; `git show HEAD:agents/ORG-22.md` | org records |
(see prior rows through #9/#10 — tip `9c706b55`)


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
CoS recheck 00:40 GST Googlebot: sitemap loc=36 ai-cfo=1 privacy=0 terms=0; contact meta_len=143; same href pattern. Match. Git tip now `23520ef3`.
```


### Pasteable evidence — #14/#15 (2026-09-16)
```
#15 tip 295aedb5: HANDOVER+STATE on main
#14 tip cb04e17d: server/services/deploy_landed.py + test_deploy_landed.py wired from main.py
suite on #14 branch: tsc=82, auth-critical PASS, prerender ALL PASS
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
