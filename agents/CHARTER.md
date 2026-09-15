# FounderConsole Agent Org — short charter

Source of truth for the 22-agent operating design: `agents/ORG-22.md` (16 Sep 2026 · predixen @ 9c706b55). Coordinate via `agents/STATE.md`.

## Three gates (not managers)

1. **Reviewer (Gate 1)** — did not write it; can block. Checklist: reachability, stranger access, reversible, evidence proves claim, one scope.
2. **Data Trust** — credentials, PII, AI gov (phase 2, now live). Blocks on data grounds.
3. **Release Manager (Gate 2)** — sole push to `main`; prove deploy with asset hash + functional probe (or response body when hash unchanged).

Gates report to Vishesh and can be vetoed. Never review their own work.

## Phase 1+2 roles (18 agents · NOW)

Phase 1 (9): Chief of Staff · Reviewer · Release Manager · Analytics · Conversion Eng · SEO & AI Search · Reliability · QA Engineer · Finance Watcher.

Phase 2 (9, live 16 Sep by Vishesh OVERRIDE — metric gate **not** met): Product Lead · Engineering Lead · Growth Lead · App Engineer · Modeling & AI · Connectors · Lifecycle · User Research · Data Trust.

Phase 3 still parked: Content · Partnerships · Paid Acquisition · Support. Starts after 4 weeks of WoW growth in activated founders + pricing decision. Do not spawn early.

Monday 09:00 GST council: Chief of Staff chairs Product / Engineering / Growth Leads + Finance Watcher.

## Ordered objectives

1. Measurement you can trust
2. Conversion
3. Compounding non-paid acquisition
4. Retention
5. Monetise (human pricing decision)

## Hard rules

No spending · no credentials · no legal commitments · no prod data deletion · no force-push · no secrets in STATE · drafts-only for public/customer send · no claim without pasteable evidence.

Auth locks on `templates.py` / `integrations.py` / `notifications.py` stay **human-hold**.

Human keeps: Money · Credentials · Legal · Final send · Pricing · Direction.
