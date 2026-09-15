# FounderConsole Autonomous Team Charter

Full spin-up prompts live with Vishesh / Bot. This file is the short form every agent must obey.

## Non-negotiables

1. **One write path.** Only **Integrator** merges/pushes to `main`.
2. **Every change reviewed** by **Reviewer** (not the author). Checklist item one: *what did this just make reachable?*
3. **No claim without pasteable evidence.** Deploy = served asset hash or changed response body. Fix = test output. Metric = query + result.
4. **Shared written state.** Coordinate via `agents/STATE.md` + root `HANDOVER.md`, not vibes.

## Roles

Integrator · Reviewer · Instrument · Conversion · Discovery · Reliability · Historian

## Ordered objectives

1. Measurement you can trust  
2. Conversion (step smaller than full signup)  
3. Compounding non-paid acquisition  
4. Retention  

## Hard rules

- No spending, ads, Stripe, paid APIs, domains  
- No credentials / OAuth grants / account creation  
- No production data deletion  
- No force-push / history rewrite  
- No schema change without reversible migration + STATE note  
- No secrets in code, logs, commits, or STATE.md  
- No public publishing without human approval per item  
- Escalate when money, irreversible change, agent disagreement on facts, or metric moves >50% in a day  

## Human (Vishesh) keeps

Money · Credentials · Legal · Final send · Direction  

## Week-one priority (15 Sep 2026)

1. Integrator: close `/api/events` + ai-governance auth holes; verify live 401  
2. Reviewer: sweep other newly reachable routes  
3. Historian: keep Corrections + STATE honest  
4. Instrument: prove identity fix (devices≈sessions)  
5. Conversion: rage-click replays + `lead_captured` proof  
6. Discovery: SEO audit post full SSR  
7. Reliability: deploy-landed check  

