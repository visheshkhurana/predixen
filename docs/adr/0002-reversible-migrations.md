# ADR-0002: Reversible migrations off web startup

- Status: Proposed
- Date: 2026-09-16
- Deciders: Engineering Lead
- Consulted: Reliability, Release Manager, QA Engineer

## Context
Schema changes today run inside the web process:
- `server/core/migrations.py` (~1789 lines) executes at startup when configured.
- Config flags also allow `Base.metadata.create_all`, benchmark/demo seed, and credential auto-migrate on boot (`server/core/config.py`, `credential_migration.py`).

That is unsafe with multiple Railway replicas (races, partial applies, opaque rollbacks) and couples deploys to migration success in ways that are hard to prove.

## Decision
Adopt **explicit versioned reversible migrations** (Alembic or equivalent) run as a **separate release step**, not inside FastAPI lifespan. Web startup only **checks** that the DB revision matches the expected head and fails health clearly if not. Startup `create_all` and inline DDL in `migrations.py` are frozen for new work and retired incrementally.

## Consequences
- Positive: rollbacks become real; replicas can scale without double-migrating; RM can prove migrate-then-serve order.
- Negative: deploy pipeline gains a step; first cut needs a baseline revision from current prod schema.
- Follow-ups: one-shot baseline revision; move credential migration to an explicit job; document RM checklist.

## Kill criteria
Pause if migrate step exceeds deploy SLO or blocks daily ship without a documented hot-fix path; do not remove startup safety checks until the new runner has one green prod deploy with pasteable evidence.

## Out of scope
Rewriting all 1789 lines in one PR; Data Trust / encryption redesign; claiming templates/integrations/notifications lock files.
