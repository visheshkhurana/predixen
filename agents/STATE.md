# Team State — updated 15 Sep 2026 by Integrator

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11
(Source: HANDOVER week of 13 Sep — Instrument must refresh post single-identity ship)
Last verified deploy tip on GitHub: `26791cd7` (auth lock PR #6). Live probes at 23:39 GST still showed open `/api/events` (200) and `/admin/ai-governance/state` (500) — Railway had not yet rolled this tip (health uptime ~348s from prior start). Bundle observed `index-eWXmctMP.js`.

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
| Integrator | Lock `/api/events` + `/admin/ai-governance/*` | events.py, ai-governance/routes.ts, requireAuth.ts | #6 `26791cd7` | **merged to main; awaiting Railway + live 401 evidence** |
| Reviewer | Audit blast radius of #6 | — | #6 | after live 401 |
| Instrument | Prove devices≈sessions post identity fix | — | — | pending |
| Conversion | Watch rage-click replays; confirm `lead_captured` | — | — | pending |
| Discovery | SEO audit post full SSR | — | — | pending |
| Reliability | Deploy-landed monitor + auth 401 verify | — | — | pending |
| Historian | Keep STATE/HANDOVER honest | agents/STATE.md | — | seeded |

## Blocked
| Item | Blocked on | Since |
| Live 401 claim for auth lock | Railway deploy of `26791cd7` | 15 Sep |
| PostHog connector for Instrument | Vishesh / connector install | 15 Sep |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
| Item | PR/commit | Verified by | Metric effect |
| Section-3 conversion | `4ef45867` | Bot+Ops | lead_captured in calculator chunk |
| Marketing SSR ×7 | `#5` `586dbbf8` + `cc2642c4` | Bot+Ops: ssr-content=1 on seven paths | SEO surface |
| Auth lock `/api/events` + ai-governance | `#6` `26791cd7` | **code on main only — NOT yet live-verified** | closes ID leak once Railway lands |

## Corrections — things we believed that were false
| Believed | Actually | Found by | Cost |
| Pending §3 uncommitted forever | Shipped `4ef45867` 15 Sep | Bot/Integrator | month of dead tools |
| Prefix fix alone is safe | `/api/events` became public read+write | Audit 15 Sep | live ID leak until auth patch lands in prod |
| Merged = shipped | Must prove live 401 / changed body | Integrator 15 Sep | almost claimed shipped early |
| Deploy = push | Must wait for new process / probe | HANDOVER §8 | stranded commits |
