# Team State — updated 16 Sep 2026 ~00:30 GST by Bot (phase-1 spin-up)

## Staffing (ORG-22 · Phase 1 · 9 agents)
**Active:** Chief of Staff · Reviewer · Release Manager · Analytics · Conversion Eng · SEO & AI Search · Reliability · QA Engineer · Finance Watcher  
**Phase 2 parked (do not spawn):** Product Lead · Engineering Lead · Growth Lead · App Engineer · Modeling & AI · Connectors · Lifecycle · User Research · Data Trust  
**Phase 3 parked:** Content · Partnerships · Paid Acquisition · Support  

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11 | lead_captured: 0 (never seen)
(Source: HANDOVER week of 13 Sep — Analytics must refresh **after** PostHog connector)
GitHub tip: `9c706b55`
**Auth locks CLOSED (evidence):** `/api/events` GET+POST → 401; `/admin/ai-governance` → 401; GET `/api/feedback` → 401; company forecasting → 401.
**OPEN CRITICAL (16 Sep audit @ 9c706b55):** unauth `POST /api/templates/companies/*/apply/*` (created scenario 55); unauth `/api/integrations/*` connect/sync/status; unauth `GET /api/notifications/email-stats` (PII) + send endpoints.

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
| Chief of Staff | Commit ORG-22 + CHARTER/STATE via RM; seed DECISIONS.md + AUTONOMY.md | agents/* | via RM | active |
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
| Auth locks closed everything | templates/integrations/notifications still open | Audit 16 Sep | live PII + company writes |
| Bundle hash must change for backend/SSR | Auth/SSR can land with same `index-*.js` | Bot 15 Sep | wrong deploy signal |
