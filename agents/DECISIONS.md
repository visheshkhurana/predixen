# Decisions log

Monday 09:00 GST council: CoS + Product/Engineering/Growth Leads + Finance Watcher. Type 1 still batched daily to Vishesh.

| Date (GST) | Type | Decision | By | Evidence / note |
|---|---|---|---|---|
| 16 Sep | staffing | Phase 1 nine live; do not spawn phase 2 until identity + signup verified and `lead_captured` fires 2 straight weeks | Bot / Vishesh org design | agents/ORG-22.md @ 9c706b55 |
| 16 Sep | records | CHARTER/STATE/ORG-22/DECISIONS/AUTONOMY to land via RM docs PR; origin tip stays `9c706b55` until RM proves next ship | Bot → CoS | this file |
| 16 Sep | Type 1 | Do not edit `templates.py` / `integrations.py` / `notifications.py` until Vishesh greens the lock PR | Reviewer / Bot | standing file claim; P0 live holes |
| 16 Sep | Type 1 | Hold P0 auth locks on templates/integrations/notifications; other Phase 1 PRs continue | Vishesh via Bot | open + human-hold |
| 16 Sep | records | #11 merged `d4b3bcb1` | RM | tip `74655640` |
| 16 Sep | records | #12 live (`9d559d17`); CoS Googlebot recheck 00:40 GST | RM / CoS | tip then `23520ef3` |
| 16 Sep | records | #13 dispatch-only CI (`3c2f1094`) | RM / QA | `workflow_dispatch` only; docs `77410c22` |
| 16 Sep | Type 2 | **OVERRIDE:** start Phase 2 (9 agents + Exec/Build/Growth/Gates rooms) **before** identity/signup/`lead_captured`×2w tripwire. Gate unmet (`lead_captured`=0). Do not spawn Phase 3. | Vishesh via Bot | Bot 00:42 GST; CoS log. Auth locks remain human-hold. |
| 16 Sep | records | Mid-restart: do not cite `#16` live (uptime ~7s; `/ai-cfo` 0 hrefs) | CoS curl 00:45 GST | tip `34ce49e7` |
| 16 Sep | records | `#16` **live** after settle: `/ai-cfo` hrefs runway/survival/default-alive/auth + WebApplication ld=1; uptime 57.7s. `#14` still **not** shipped — control asset 200 HTML | CoS curl 00:47 GST | tip `34ce49e7` |
| 16 Sep | records | `#15` merged `295aedb5` still Phase 1 parked; DECISIONS/AUTONOMY absent on origin | CoS | follow-up docs PR |
