# ADR-0003: Background loops off the web process

- Status: Accepted
- Date: 2026-09-16
- Accepted: 2026-09-21 (Gate 2 after #17)
- Deciders: Engineering Lead
- Consulted: Reliability, Modeling & AI

## Context
FastAPI `lifespan` kicks deferred startup that creates asyncio tasks on the web worker, including:
- scheduler loop (~600s)
- competitor scan loop
- truth_scan refresh loop
- crawler health loop

A second replica doubles those jobs. Reliability’s #14 deploy-landed monitor is separate and must not be collided with.

## Decision
Move periodic background loops to a **dedicated worker process** (or single elected leader) before horizontal scale. Web process stays request-serving; health reports worker liveness separately. Feature-flag or process type gates which loops run where.

## Consequences
- Positive: safe replica count; clearer ownership of silent-failure monitors.
- Negative: new process to deploy and watch; short dual-run window during cutover.
- Follow-ups: inventory every `asyncio.create_task` in lifespan; coordinate crawler health with Reliability (do not fork #14).
- Constraint: do not start runtime implementation until PR #38 is green, or explicitly coordinate with Reliability (do not collide with #38 / deploy-landed monitor).

## Kill criteria
Revert cutover if worker miss rate exceeds web-embedded baseline for 24h, or if deploy complexity blocks a P0 ship.

## Out of scope
Changing crawler_health semantics owned by Reliability; paid infra plan changes (escalate to Vishesh).
