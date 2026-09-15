# Team State — updated 15 Sep 2026 ~23:45 GST by Integrator

## Baseline (refresh weekly, cite the query)
devices/week: 31 | sessions/week: 48 | signup_view: 23 | calculator_used: 11
(Source: HANDOVER week of 13 Sep — Instrument must refresh post single-identity ship)
Last verified live tip: auth lock landed (health uptime reset ~63s at 19:44Z). Bundle still `index-eWXmctMP.js` (auth-only change).

## Org (charter roles)
| Role | Agent | Push to main? |
| Integrator | Integrator | YES — only |
| Reviewer | Reviewer | no (PR review) |
| Instrument | Instrument | no (PR) |
| Conversion | Conversion | no (PR) |
| Discovery | Discovery | no (PR) |
| Reliability | Reliability | no (PR) |
| Historian | Historian | no (PR) |

## In flight
| Agent | Item | Files claimed | PR | Status |
| Reviewer | Blast-radius audit of #6/#7 | — | #6 #7 | requested |
| Instrument | Prove devices≈sessions post identity fix | — | — | pending |
| Conversion | Watch rage-click; confirm `lead_captured` | — | — | pending |
| Discovery | SEO audit post full SSR | — | — | pending |
| Reliability | Ongoing deploy-landed monitor | — | — | pending |
| Historian | Keep STATE/HANDOVER honest | agents/STATE.md | — | ongoing |

## Blocked
| Item | Blocked on | Since |
| n8n ai-governance callbacks | Vishesh must set `AI_GOVERNANCE_SECRET` on Railway (no default in code) | 15 Sep — unsigned/missing → 503 fail-closed |
| PostHog connector for Instrument | Vishesh / connector install | 15 Sep |
| Money/ads restart | human only | standing |

## Shipped this week (evidence required)
| Item | PR/commit | Verified by | Metric effect |
| Section-3 conversion | `4ef45867` | Bot+Ops | lead_captured in calculator chunk |
| Marketing SSR ×7 | `#5` `586dbbf8` + `cc2642c4` | Bot+Ops ssr-content=1 | SEO surface |
| Auth lock events + ai-governance | `#6` `26791cd7` + `#7` `65c7ca01` | Integrator live curls 19:44Z UTC (below) | closes public read/write on `/api/events` and sessionless founder panel |

### Pasteable evidence — auth lock (2026-09-15T19:44:46Z)
```
GET  /api/events -> 401 {"detail":"Not authenticated"}
POST /api/events -> 401 {"detail":"Not authenticated"}
GET  /admin/ai-governance/state -> 401 {"error":"Authentication required"}
POST /admin/ai-governance/ask -> 401 {"error":"Authentication required"}
POST /admin/ai-governance/callback (unsigned) -> 503 {"error":"AI governance callback not configured"}
POST /api/leads -> 200 {"status":"ok","created":true}  # regression OK
health uptime≈63s after roll; tip main includes 65c7ca01
```

## Corrections — things we believed that were false
| Believed | Actually | Found by | Cost |
| Merged = shipped | Must wait for new uptime + probe | Integrator | almost false-claimed |
| Mount order irrelevant | callback after `app.use` got session 401 | Integrator live probe | #7 hotfix |
| Default HMAC secret OK | removed; prod must set env | Audit | 503 until secret set |
