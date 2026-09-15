# Team State — updated 16 Sep 2026 ~00:33 GST by Chief of Staff

## Staffing (ORG-22 · Phase 1 · 9 agents)
**Active:** Chief of Staff · Reviewer · Release Manager · Analytics · Conversion Eng · SEO & AI Search · Reliability · QA Engineer · Finance Watcher  
**Phase 2 parked (do not spawn):** Product Lead · Engineering Lead · Growth Lead · App Engineer · Modeling & AI · Connectors · Lifecycle · User Research · Data Trust  
**Phase 3 parked:** Content · Partnerships · Paid Acquisition · Support  

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11 | lead_captured: 0 (never seen)
(Source: HANDOVER week of 13 Sep — Analytics must refresh **after** PostHog connector)
GitHub tip: `9c706b55`
**Auth locks CLOSED (evidence):** `/api/events` GET+POST → 401; `/admin/ai-governance` → 401; GET `/api/feedback` → 401; company forecasting → 401.
**OPEN CRITICAL (CoS curl 16 Sep 00:32 GST, tip still `9c706b55`):** GET `/api/notifications/email-stats` → **200**, 98 rows, keys include `to`; GET `/api/integrations/available` → **200**; GET `/api/integrations/companies/1/status` → **200**; GET `/api/templates/` → **200**; POST `/api/templates/companies/1/apply/1` → **404** (not 401). “Created scenario 55” **not re-proven** this pass — do not treat as verified write.

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
| Reviewer | Blast-radius of #6/#10 + 16 Sep critical opens (templates/integrations/notifications) | — | — | **P0** |
| Analytics | Prove devices≈sessions; verify lead_captured; add signup_completed | — | — | **blocked** — PostHog connector |
| Conversion Eng | Rage-click replays → one conversion change | — | — | blocked on PostHog replay until connector |
| SEO & AI Search | Ship SSR cross-links + contact pack; add /ai-cfo to sitemap | content-drafts/… | — | queued |
| Reliability | Deploy-landed monitor (hash + body) | — | — | queued |
| QA Engineer | GitHub Actions test CI on every PR | .github/workflows | — | needs Vishesh Actions minutes |
| Finance Watcher | Spend register + Railway/LLM billing watch | — | — | starting |
| Chief of Staff | Docs pack for RM: ORG-22 + CHARTER + STATE + DECISIONS.md + AUTONOMY.md | agents/* | via RM | stubs seeded; tip stays `9c706b55` until RM proves ship |
| Release Manager | Throughput for docs + P0 auth locks once Reviewer clears | — | — | standing |

## Blocked
| Item | Blocked on | Since |
| Analytics identity + replay | Vishesh authorizes PostHog connector (522965) | 15 Sep |
| QA CI | Vishesh approves GitHub Actions minutes | 16 Sep |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
(see prior rows through #9/#10 — tip `9c706b55`)

## Corrections — things we believed that were false
| Believed | Actually | Found by | Cost |
| Pending §3 uncommitted forever | Shipped `4ef45867` 15 Sep | Bot/RM | month of dead tools |
| Prefix fix alone is safe | `/api/events` public until #6 | Audit 15 Sep | live ID leak window |
| Auth locks closed everything | templates/integrations/notifications still open | Reviewer 16 Sep | live PII + unauth catalogs |
| email-stats is private | GET `/api/notifications/email-stats` **200**, 98 emails, field `to` present | CoS curl 00:32 GST | live recipient leak |
| `/api/integrations/*` locked | GET available **200**; GET companies/1/status **200** | CoS curl 00:32 GST | stranger sees catalog + company 1 |
| templates apply not reachable | GET `/api/templates/` **200**; POST apply/1 → **404 not 401** | CoS curl 00:32 GST | path runs unauth; write-to-scenario-55 **unverified** |
| Bundle hash must change for backend/SSR | Auth/SSR can land with same `index-*.js` | Bot 15 Sep | wrong deploy signal |
