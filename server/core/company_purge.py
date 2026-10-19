"""Delete a company and every row that depends on it, driven by FK metadata.

The hand-maintained list in DELETE /companies/{id} drifted from the models
(it filtered InvestorPipeline.company_id, a column that does not exist, so
every delete raised and returned 500; ~25 company-owned tables were never
listed at all). Walking the declared foreign keys keeps the cascade complete
as tables are added.

Rules, applied recursively from ``companies``:
  * a NOT NULL foreign key means the child cannot outlive the parent: delete it
    (after its own children);
  * a nullable foreign key means the row has a life of its own (billing
    subscriptions, audit logs, notifications): detach it by setting NULL.
Self-references are skipped; a single DELETE removes the whole set, and
Postgres checks NO ACTION constraints at statement end.

Tables the ORM metadata cannot see are handled first (see
``UNLINKED_COMPANY_TABLES`` and ``_live_company_fks``): raw-SQL tables from
server/core/migrations.py, models whose ``company_id`` has no declared FK, and
any FK to ``companies`` that exists only in the live database (e.g.
company_states is created with REFERENCES companies(id) while its model
declares none). Missing those made the final DELETE FROM companies fail and the
whole purge roll back.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy import Table, inspect, select, text
from sqlalchemy.orm import Session

from server.core.db import Base

logger = logging.getLogger(__name__)

COMPANY_TABLE = "companies"

# Nullable FKs default to "detach", but these rows are pure derived data for
# the company and are deleted instead.
DELETE_ON_NULLABLE = {"simulation_cache"}


# (table, column, action) for company-owned rows the FK walk cannot reach:
# raw-SQL tables (server/core/migrations.py) and models whose company_id has no
# ForeignKey. Ordered children first (graph_edges -> graph_nodes; event_payloads
# cascade from events). Nullable log columns are detached like other logs.
UNLINKED_COMPANY_TABLES = (
    ("graph_edges", "company_id", "delete"),
    ("graph_nodes", "company_id", "delete"),
    ("events", "company_id", "delete"),
    ("company_flags", "company_id", "delete"),
    ("ai_agent_budgets", "company_id", "delete"),
    ("ai_agent_logs", "company_id", "nullify"),
    ("autopilot_runs", "company_id", "delete"),
    ("data_confidence_scores", "company_id", "delete"),
    ("company_states", "company_id", "delete"),
    ("shared_scenarios", "company_id", "delete"),
    ("metric_snapshots", "company_id", "delete"),
    ("agent_simulation_runs", "company_id", "delete"),
    ("analytics_events", "company_id", "nullify"),
)


@dataclass
class _Step:
    action: str  # "delete" | "nullify"
    table: Table
    # Column on `table` and the parent selectable it must match.
    column: object
    parent_select: object


def _load_all_models() -> None:
    """Import every model module so Base.metadata knows every table."""
    import importlib
    import pkgutil

    import server.models as models_pkg

    for mod in pkgutil.iter_modules(models_pkg.__path__):
        try:
            importlib.import_module(f"server.models.{mod.name}")
        except Exception as e:  # a broken optional model must not block deletes
            logger.warning("company_purge: could not import server.models.%s: %s", mod.name, e)


def _children(parent: Table):
    """(child_table, fk) for every FK in metadata pointing at `parent`."""
    for table in Base.metadata.sorted_tables:
        if table is parent:
            continue
        for fk in table.foreign_keys:
            if fk.column.table is parent:
                yield table, fk


def plan_company_purge(company_id: int, existing_tables: Optional[Set[str]] = None) -> List[_Step]:
    """Ordered statements that remove `company_id` and its dependents.

    Children always precede parents. Tables missing from `existing_tables`
    (modelled but never migrated) are skipped with their subtree. Exposed for
    tests.
    """
    _load_all_models()
    companies = Base.metadata.tables[COMPANY_TABLE]
    steps: List[_Step] = []

    def visit(table: Table, row_select, depth: int, path: tuple) -> None:
        # row_select: SELECT of `table` rows being deleted (a Select object).
        if depth > 6:
            raise RuntimeError(f"company_purge: FK chain too deep at {table.name}")
        for child, fk in _children(table):
            if existing_tables is not None and child.name not in existing_tables:
                continue
            if child.name in path:
                continue  # FK cycle; the cycle's first member is already queued
            parent_values = row_select.with_only_columns(fk.column)
            if fk.parent.nullable and child.name not in DELETE_ON_NULLABLE:
                steps.append(_Step("nullify", child, fk.parent, parent_values))
            else:
                child_rows = select(child).where(fk.parent.in_(parent_values))
                visit(child, child_rows, depth + 1, path + (child.name,))
                steps.append(_Step("delete", child, fk.parent, parent_values))

    root = select(companies).where(companies.c.id == company_id)
    visit(companies, root, 0, (COMPANY_TABLE,))
    return steps


def _metadata_company_fks() -> Set[tuple]:
    """(table, column) pairs whose FK to companies the ORM already declares."""
    _load_all_models()
    companies = Base.metadata.tables[COMPANY_TABLE]
    return {
        (t.name, fk.parent.name)
        for t in Base.metadata.sorted_tables
        for fk in t.foreign_keys
        if fk.column.table is companies
    }


def _live_company_fks(inspector, existing: Set[str]) -> List[tuple]:
    """(table, column, nullable) for single-column FKs to companies in the DB."""
    found = []
    for table in sorted(existing):
        if table == COMPANY_TABLE:
            continue
        try:
            fks = inspector.get_foreign_keys(table)
        except Exception:
            continue
        for fk in fks:
            cols = fk.get("constrained_columns") or []
            if fk.get("referred_table") != COMPANY_TABLE or len(cols) != 1:
                continue
            nullable = True
            try:
                for c in inspector.get_columns(table):
                    if c["name"] == cols[0]:
                        nullable = bool(c.get("nullable", True))
            except Exception:
                pass
            found.append((table, cols[0], nullable))
    return found


def plan_unlinked_purge(existing: Set[str], live_fks: List[tuple]) -> List[tuple]:
    """(table, column, action) to run before the FK-metadata plan. Exposed for tests."""
    declared = _metadata_company_fks()
    plan: List[tuple] = []
    seen = set()
    for table, column, action in UNLINKED_COMPANY_TABLES:
        if table in existing and (table, column) not in declared:
            plan.append((table, column, action))
            seen.add((table, column))
    for table, column, nullable in live_fks:
        if (table, column) in declared or (table, column) in seen:
            continue
        action = "nullify" if nullable and table not in DELETE_ON_NULLABLE else "delete"
        plan.append((table, column, action))
        seen.add((table, column))
    return plan


def _quote(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"company_purge: unexpected identifier {name!r}")
    return f'"{name}"'


def purge_company(db: Session, company_id: int) -> None:
    """Remove the company row and everything hanging off it. Caller commits."""
    inspector = inspect(db.get_bind())
    existing = set(inspector.get_table_names())
    for table, column, action in plan_unlinked_purge(existing, _live_company_fks(inspector, existing)):
        if action == "nullify":
            sql = f"UPDATE {_quote(table)} SET {_quote(column)} = NULL WHERE {_quote(column)} = :cid"
        else:
            sql = f"DELETE FROM {_quote(table)} WHERE {_quote(column)} = :cid"
        db.execute(text(sql), {"cid": company_id})
    for step in plan_company_purge(company_id, existing):
        if step.action == "nullify":
            stmt = (
                step.table.update()
                .where(step.column.in_(step.parent_select))
                .values({step.column.name: None})
            )
        else:
            stmt = step.table.delete().where(step.column.in_(step.parent_select))
        db.execute(stmt)
    companies = Base.metadata.tables[COMPANY_TABLE]
    db.execute(companies.delete().where(companies.c.id == company_id))


def describe_plan(company_id: Optional[int] = 0) -> List[str]:
    """Human-readable plan, e.g. 'delete investor_pipeline.round_id'."""
    return [f"{s.action} {s.table.name}.{s.column.name}" for s in plan_company_purge(company_id or 0)]
