"""Create the schema `qa_runner.py` needs, in a database that has none.

`qa_runner.py` seeds synthetic companies and writes rows, but it never creates its
own tables - it opens `SessionLocal()` and starts inserting. On a developer's box
that is invisible, because their database already has a schema. On a fresh
database it is the first thing that fails:

    sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: users

That is why nothing has ever run the QA lab except someone with a pre-populated
local database, and why `OPERATING-MODEL.md` could list it in the golden path for
months while no process on the floor or in CI executed it.

This script exists so CI can give the lab a disposable database. It is the
schema-creation half of `server/main.py:210` (`Base.metadata.create_all`), reused
rather than reimplemented, for a throwaway database only.

WHAT IT DOES NOT DO
-------------------
It does not mask an incomplete schema. Some tables carry raw
`sqlalchemy.dialects.postgresql.JSONB` columns, which SQLite's dialect cannot
render at all:

    sqlalchemy.exc.CompileError: (in table 'leads', column 'tags'):
    Compiler <SQLiteTypeCompiler> can't render element of type JSONB

Those tables are listed in `UNRENDERABLE_ON_SQLITE` below, and the script **fails
loudly if the set it could not create is anything else** - so a *new* table that
cannot be created turns CI red instead of being silently skipped. That is the
whole point: a skip list that cannot drift is a fact, one that can drift is a
trap.

Usage (from the repository root):

    DATABASE_URL=sqlite:////tmp/qa.db python qa-lab/runner/init_qa_db.py

Exit codes: 0 = the expected schema exists; 1 = something else happened.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# Tables whose columns are PostgreSQL-only (`JSONB`). SQLite's dialect refuses to
# compile the CREATE TABLE. None of them are in the QA lab's path - the lab
# touches users, companies, financial_records, scenarios, truth_scans and the
# simulation tables, all of which SQLite renders.
#
# If this list is wrong in either direction the script fails: a table that
# becomes renderable is a stale entry, and a table that stops being renderable is
# a new gap.
UNRENDERABLE_ON_SQLITE = frozenset({
    "leads",                 # server/models/lead.py:60        tags = Column(JSONB, ...)
    "simulation_accuracy",   # server/models/simulation_accuracy.py:23
    "lead_campaigns",        # server/models/lead_gen.py:25
    "lead_events",           # server/models/lead_gen.py:63
})

# Imported for their side effect of registering tables on `Base.metadata`.
# Mirrors the model imports at the top of `qa_runner.py`, plus the modules it
# pulls in transitively.
MODEL_MODULES = (
    "user", "company", "financial", "scenario", "truth_scan",
    "conversation", "chat", "dataset", "customer", "transaction",
    "assumption_set", "company_decision", "company_source",
    "fundraising", "scenario_version",
)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("DATABASE_URL is not set; refusing to create tables in whatever the "
              "default happens to be.", file=sys.stderr)
        return 1
    if not database_url.startswith("sqlite"):
        print(f"DATABASE_URL is not SQLite ({database_url.split(':')[0]}); "
              f"use Base.metadata.create_all directly for a PostgreSQL database.",
              file=sys.stderr)
        return 1

    for name in MODEL_MODULES:
        importlib.import_module("server.models." + name)

    from sqlalchemy.schema import CreateTable

    from server.core.db import Base, engine

    created, refused = [], []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            name = table.name
            try:
                conn.execute(CreateTable(table))
                created.append(name)
            except Exception as exc:  # CompileError for JSONB; anything else is a bug
                refused.append((name, type(exc).__name__, str(exc).split("):")[0]))

    unexpected = [r for r in refused if r[0] not in UNRENDERABLE_ON_SQLITE]
    print(f"created {len(created)} tables")
    for name, kind, detail in refused:
        print(f"  not renderable on SQLite: {name} ({kind}) {detail[:120]}")

    if unexpected:
        print(f"\nUNEXPECTED: {len(unexpected)} table(s) could not be created and are "
              f"not on the known PostgreSQL-only list: "
              f"{[u[0] for u in unexpected]}", file=sys.stderr)
        return 1

    missing = [t for t in UNRENDERABLE_ON_SQLITE if t in created]
    if missing:
        print(f"\nSTALE SKIP LIST: {missing} was created after all; remove it from "
              f"UNRENDERABLE_ON_SQLITE so the list keeps meaning something.",
              file=sys.stderr)
        return 1

    for required in ("users", "companies", "financial_records", "scenarios", "truth_scans"):
        if required not in created:
            print(f"\nMISSING: the QA lab writes to '{required}' and it was not "
                  f"created.", file=sys.stderr)
            return 1

    print("schema ready for qa-lab/runner/qa_runner.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
