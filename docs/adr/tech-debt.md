# Tech debt register

Living register for [ADR-0004](./0004-tech-debt-register.md). Engineering Lead reviews this file at the Monday council.

Seeded 2026-10-05 from files confirmed in the repo. Counts below cite the command that produced them.

## TD-001

- id: TD-001
- area/path: `server/core/migrations.py` (called from `server/main.py`; flag in `server/core/config.py`)
- what the debt is: Schema changes are a single startup migration module. `run_migrations` runs `ensure_*` helpers (idempotent `CREATE` / `ALTER ... IF NOT EXISTS`) when `should_run_migrations` is on. `wc -l server/core/migrations.py` → 1789.
- why it was taken: Boot-time helpers for columns and tables that predate a versioned runner. [ADR-0002](./0002-reversible-migrations.md) records this as the current path.
- owner role: Reliability
- cost if left alone: Multiple replicas can race, apply part of the file, and leave rollbacks hard to prove (ADR-0002).
- exit condition: Web startup no longer executes `run_migrations`. Schema changes go through an explicit versioned reversible migration step (ADR-0002).

## TD-002

- id: TD-002
- area/path: `server/main.py` (`lifespan` → `_run_deferred_startup`)
- what the debt is: The web process starts background loops with `asyncio.create_task`: `run_scheduler_loop(interval_seconds=600)` (`server/email/onboarding_sequence.py`), `run_competitor_scan_loop` (`server/api/competitors.py`), `run_truth_scan_refresh_loop` (`server/services/truth_refresh.py`), and `run_crawler_health_loop` (`server/services/crawler_health.py`). The same function also starts `run_deploy_landed_loop` (`server/services/deploy_landed.py`).
- why it was taken: The loops are created inside FastAPI lifespan deferred startup. There is no separate worker entrypoint for them. [ADR-0003](./0003-background-loops-off-web.md) records the four periodic loops; the deploy-landed monitor stays with Reliability and is not part of this row's exit.
- owner role: Reliability
- cost if left alone: A second web replica runs a second copy of each loop (ADR-0003).
- exit condition: The scheduler, competitor scan, truth-scan refresh, and crawler health loops start on a dedicated worker or single elected leader, and the web process stays request-serving (ADR-0003).

## TD-003

- id: TD-003
- area/path: `pyproject.toml` (`sqlalchemy`); `server/core/migrations.py`; `package.json` (`drizzle-orm`, `drizzle-kit`, script `db:push`); `shared/schema.ts`; `server/db.ts`; `drizzle.config.ts`
- what the debt is: Two schema systems are in the tree. Python uses SQLAlchemy (`sqlalchemy>=2.0.45` in `pyproject.toml`; migrations import `sqlalchemy`). TypeScript uses Drizzle (`drizzle-orm` / `drizzle-kit` in `package.json`; `pgTable` definitions in `shared/schema.ts`; `drizzle()` in `server/db.ts`; `drizzle.config.ts` points `schema` at `./shared/schema.ts` and `out` at `./migrations`).
- why it was taken: The Python API and the Node/Express side both talk to Postgres. [ADR-0001](./0001-one-orm.md) records both as in active use.
- owner role: Engineering Lead
- cost if left alone: Two schemas and two migration stories can drift (ADR-0001).
- exit condition: New tables and columns land only through the SQLAlchemy migration path. Drizzle does not own schema (ADR-0001).

## TD-004

- id: TD-004
- area/path: `package.json` (`name`); product name in `server/main.py`
- what the debt is: `package.json` `name` is `rest-express`. The FastAPI app title and the startup log in `server/main.py` say FounderConsole. Confirmed with `node -e "console.log(require('./package.json').name)"` → `rest-express`.
- why it was taken: The repo does not record a decision to keep the name. The published package name is still the template string.
- owner role: Engineering Lead
- cost if left alone: npm metadata, lockfile headers, and scripts identify a template name while the running app identifies as FounderConsole.
- exit condition: `package.json` `name` is a name chosen for this product, and it is no longer `rest-express`.
