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
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Set

from sqlalchemy import Table, inspect, select
from sqlalchemy.orm import Session

from server.core.db import Base

logger = logging.getLogger(__name__)

COMPANY_TABLE = "companies"

# Nullable FKs default to "detach", but these rows are pure derived data for
# the company and are deleted instead.
DELETE_ON_NULLABLE = {"simulation_cache"}


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


def purge_company(db: Session, company_id: int) -> None:
    """Remove the company row and everything hanging off it. Caller commits."""
    existing = set(inspect(db.get_bind()).get_table_names())
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
