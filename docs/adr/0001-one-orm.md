# ADR-0001: One ORM as system of record

- Status: Accepted
- Date: 2026-09-16
- Accepted: 2026-09-21 (Gate 2 after #17)
- Deciders: Engineering Lead
- Consulted: App Engineer, Modeling & AI, Connectors, Reliability

## Context
FounderConsole talks to Postgres through two ORMs in active use:
- **SQLAlchemy** (Python FastAPI): ~179 files under `server/` import sqlalchemy; models live in the Python stack; startup migrations in `server/core/migrations.py` use SQLAlchemy.
- **Drizzle** (Node/Express side): `drizzle-orm` / `drizzle-kit` in `package.json`; used from `server/db.ts`, `server/ai-governance/routes.ts`, `server/jarvis-*.ts`, and related TypeScript paths.

Two schemas and two migration stories raise replica and drift risk. A rewrite is out of scope; we need a reversible decision that stops the dual write surface growing.

## Decision
**SQLAlchemy is the system of record for Postgres schema and migrations.** New tables/columns land only via the Python migration path (see ADR-0002). Drizzle may remain for read-only or transitional TypeScript access that does not invent schema; no new Drizzle `push` / schema ownership.

## Consequences
- Positive: one place to reason about schema; unblocks reversible migrations and multi-replica safety.
- Negative: TypeScript paths that currently mutate via Drizzle need a thin FastAPI API or SQLAlchemy-backed service before they can keep writing.
- Follow-ups: inventory Drizzle write sites; freeze `drizzle-kit push` in CI; ADR-0002 lands the migration runner.

## Kill criteria
Revert or pause if a required ship is blocked more than 48h solely by this boundary with no FastAPI alternative, or if dual-write data loss is observed in staging.

## Out of scope
Rewriting all Drizzle callers in one PR; renaming packages; auth lock files.
