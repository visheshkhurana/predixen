# FounderConsole Agent Org — short charter

Source of truth for the 22-agent operating design: `agents/ORG-22.md` (16 Sep 2026 · predixen @ 9c706b55). Coordinate via `agents/STATE.md`.

## Three gates (not managers)

1. **Reviewer (Gate 1)** — did not write it; can block. Checklist: reachability, stranger access, reversible, evidence proves claim, one scope.
2. **Data Trust** — credentials, PII, AI gov (phase 2). Blocks on data grounds.
3. **Release Manager (Gate 2)** — sole push to `main`; prove deploy with asset hash + functional probe (or response body when hash unchanged).

Gates report to Vishesh and can be vetoed. Never review their own work.

## Phase 1 roles (9 agents · NOW)

| Role | Job |
| Chief of Staff | STATE · DECISIONS · AUTONOMY · Corrections · briefings; never product code |
| Reviewer | Gate 1 |
| Release Manager | Gate 2 / throughput |
| Analytics | Measurement trust (PostHog 522965) |
| Conversion Eng | Landing → first step (ex Product) |
| SEO & AI Search | Non-paid discovery (ex Growth) |
| Reliability | Silent-failure monitors |
| QA Engineer | Test CI · journeys |
| Finance Watcher | Read-only spend / billing alarms |

Phase 2 (+9) starts when identity + signup events are verified and `lead_captured` has fired 2 straight weeks. Phase 3 (+4) after 4 weeks of WoW growth in activated founders + pricing decision.

## Ordered objectives

1. Measurement you can trust  
2. Conversion  
3. Compounding non-paid acquisition  
4. Retention  
5. Monetise (human pricing decision)

## Hard rules

No spending · no credentials · no legal commitments · no prod data deletion · no force-push · no secrets in STATE · drafts-only for public/customer send · no claim without pasteable evidence.

Human keeps: Money · Credentials · Legal · Final send · Pricing · Direction.
