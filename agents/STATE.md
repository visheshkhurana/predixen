# Team State — updated 15 Sep 2026 ~23:44 GST by Historian

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11
(Source: HANDOVER week of 13 Sep — Instrument must refresh post single-identity ship)
Last verified deploy: GitHub tip `65c7ca01` (#7) after `#6` `26791cd7`. Live 23:43 GST: `/api/events` GET+POST → **401**; `/admin/ai-governance` → **401**; health uptime ~130s (new process). Bundle still `index-eWXmctMP.js` — SSR/auth can land without client hash change; cite response bodies.

## Org (charter roles)
| Role | Agent | Push to main? |
| Integrator | Integrator | YES — only |
| Reviewer | Reviewer | no (PR review) |
| Instrument | Instrument | no (PR) |
| Conversion | Conversion | no (PR) |
| Discovery | Discovery | no (PR) |
| Reliability | Reliability | no (PR) |
| Historian | Historian | no (PR) |

Coordination: this file + HANDOVER.md. Prefer FounderConsole Core / Ops rooms + STATE.md.

## In flight
| Agent | Item | Files claimed | PR | Status |
| Reviewer | Audit blast radius of #6 / newly reachable routes | — | after #6 | due now that live 401 proven |
| Instrument | Prove devices≈sessions post identity fix | — | — | pending (PostHog connector blocked) |
| Conversion | Watch rage-click replays; confirm `lead_captured` | — | — | pending |
| Discovery | SEO hygiene (sitemap privacy/terms + strip shell JSON-LD) | client/public/sitemap.xml, server/seo-prerender.ts | with Integrator | audit done; fix with Integrator |
| Discovery | Free-tool SSR cross-links + contact enrich pack | content-drafts/ssr-crosslinks-contact-v1.md → seo-prerender.ts | with Integrator | **pack ready** (do not invent metrics; Integrator pastes) |
| Reliability | Deploy-landed monitor (served hash / body) | — | — | pending |
| Historian | Keep HANDOVER in sync with verified prod | HANDOVER.md | docs PR | local rewrite ready; origin HANDOVER still morning-stale |

## Done this session (evidence)
| Agent | Item | Evidence |
| Discovery | Post-SSR SEO audit | `/workspace/content-drafts/seo-audit-post-ssr.md` (~23:40 GST Googlebot curls) |
| Integrator | Auth lock live | Historian 23:43 GST: events GET/POST 401; `/admin/ai-governance` 401 after `#6`/`#7` |

## Blocked
| Item | Blocked on | Since |
| PostHog connector for Instrument | Vishesh / connector install | 15 Sep |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
| Item | PR/commit | Verified by | Metric effect |
| Section-3 conversion | `4ef45867` | Historian 23:40 GST: `/api/leads`→200 (public capture); `/api/simulations/jobs`→401; slack POST-only live; bundle `index-eWXmctMP.js` | calculator capture; `lead_captured` still Conversion/Instrument |
| Marketing SSR ×7 | `#5` `586dbbf8` + `cc2642c4` | Historian 23:40 GST ssr-content=1 on seven+ paths | SEO surface; Discovery audit done |
| Auth lock `/api/events` + ai-governance | `#6` `26791cd7` (+ `#7` `65c7ca01` callback fix) | Historian 23:43 GST: events GET+POST **401**; `/admin/ai-governance` **401**; uptime ~130s | closes public events ID leak |
| Team CHARTER + STATE on main | `f29f978b` | on origin/main | coordination surface |

### Pasteable evidence — auth lock (Integrator, 2026-09-15T19:44:46Z)
```
GET/POST /api/events -> 401 {"detail":"Not authenticated"}
GET /admin/ai-governance/state -> 401 {"error":"Authentication required"}
POST /admin/ai-governance/callback (unsigned) -> 503 fail-closed (AI_GOVERNANCE_SECRET unset)
POST /api/leads -> 200 public capture OK
```

## Corrections — things we believed that were false
| Believed | Actually | Found by | Cost |
| Pending §3 uncommitted forever | Shipped `4ef45867` 15 Sep | Bot/Integrator | month of dead tools |
| `/api/leads` still 404 | 401 after ship | Ops/Bot; Historian | — |
| Blank marketing pages after prerender PRs | Live ssr-content on all 7 | Ops/Bot; Historian | — |
| Prefix fix alone is safe | `/api/events` became public read+write until `#6` | Audit 15 Sep | live ID leak window |
| Events still open at 23:40 GST forever | Pre-roll of `#6`; live 401 at 23:43 GST | Bot + Historian | almost left STATE saying open |
| Merged = shipped | Must prove live 401 / changed body | Integrator 15 Sep | almost claimed early |
| Bundle hash must change for backend/SSR | Auth/SSR can land with same `index-*.js` | Bot 15 Sep | wrong deploy signal |
| Deploy = push | Must wait for new process / probe | HANDOVER §8 | stranded commits |
| Display path = Final URL (Ads) | Cosmetic only | HANDOVER §8 | wrong diagnoses ×2 |
