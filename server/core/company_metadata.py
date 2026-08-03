"""Atomic, per-key writes to ``companies.metadata_json``.

``metadata_json`` is a single shared JSON blob that a dozen unrelated features
write to: connector credentials, smart alerts, alert rules, hiring plans, the
copilot's knowledge base and conversation state, auto-simulations and the
strategic diagnosis.

Every one of those used to do a full-dict read-modify-write::

    metadata = company.metadata_json or {}
    metadata["smart_alerts"] = alerts
    company.metadata_json = metadata
    db.commit()

Two requests that touch *different* keys therefore clobber each other: both read
the blob, each replaces the whole thing, and the last writer wins — silently
dropping the other's key. That is what made a freshly-created hiring plan 404 on
``/simulate``: a concurrent writer had already overwritten the blob without
``hiring_plans`` in it.

These helpers rewrite only the addressed path. On PostgreSQL the whole update is
one statement, so the row lock it takes serializes concurrent writers and
sibling keys survive. Paths may be nested (``("connectors", provider_id)``),
which narrows the write further: two providers connecting at once no longer race
over the shared ``connectors`` sub-dict.

Non-PostgreSQL backends (SQLite, used by the tests) fall back to the old
read-modify-write. There is no concurrency to protect there.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Sequence, Union

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)

MetadataPath = Union[str, Sequence[str]]

# The nested-path SQL repeats its base expression once per level, so depth is
# deliberately capped. Nothing in the app addresses deeper than two.
_MAX_PATH_DEPTH = 4

_BASE = "COALESCE(metadata_json::jsonb, '{}'::jsonb)"


def _normalize_path(path: MetadataPath) -> List[str]:
    keys = [path] if isinstance(path, str) else list(path)
    if not keys:
        raise ValueError("metadata path must have at least one key")
    if len(keys) > _MAX_PATH_DEPTH:
        raise ValueError(f"metadata path deeper than {_MAX_PATH_DEPTH}: {keys!r}")
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError(f"metadata path keys must be non-empty strings: {keys!r}")
    return keys


def _build_merge(base: str, keys: List[str], value_param: str, params: Dict[str, Any]) -> str:
    """Build a jsonb expression that sets ``keys`` within ``base``.

    Uses ``||`` (merge) rather than ``jsonb_set`` because ``jsonb_set``'s
    ``create_missing`` only creates the *final* path element -- setting
    ``{connectors,stripe}`` is a silent no-op when ``connectors`` is absent.
    Merging builds any missing ancestors on the way down.
    """
    key_param = f"k{len(params)}"
    params[key_param] = keys[0]

    if len(keys) == 1:
        inner = f"CAST(:{value_param} AS jsonb)"
    else:
        child_base = f"COALESCE(({base}) -> :{key_param}, '{{}}'::jsonb)"
        inner = _build_merge(child_base, keys[1:], value_param, params)

    return f"({base}) || jsonb_build_object(:{key_param}, {inner})"


def _is_postgres(db) -> bool:
    try:
        return db.get_bind().dialect.name == "postgresql"
    except Exception:  # pragma: no cover - defensive; falls back to ORM path
        return False


def _fallback_set(company, keys: List[str], value: Any) -> None:
    metadata = dict(company.metadata_json or {})
    node = metadata
    for key in keys[:-1]:
        child = node.get(key)
        child = dict(child) if isinstance(child, dict) else {}
        node[key] = child
        node = child
    node[keys[-1]] = value
    company.metadata_json = metadata
    flag_modified(company, "metadata_json")


def _fallback_delete(company, keys: List[str]) -> None:
    metadata = dict(company.metadata_json or {})
    node = metadata
    for key in keys[:-1]:
        child = node.get(key)
        if not isinstance(child, dict):
            return
        child = dict(child)
        node[key] = child
        node = child
    node.pop(keys[-1], None)
    company.metadata_json = metadata
    flag_modified(company, "metadata_json")


def save_metadata_value(db, company, path: MetadataPath, value: Any, *, commit: bool = True) -> None:
    """Write ``value`` at ``path`` inside ``company.metadata_json``.

    Only that path is rewritten; every sibling key is left as it is in the
    database, including keys another request wrote after this one read the row.

    Pass ``commit=False`` when the caller owns the transaction (e.g. the write
    must land together with a FinancialRecord insert). The statement still runs
    immediately, so the row lock is held until the caller commits.
    """
    keys = _normalize_path(path)

    if _is_postgres(db):
        params: Dict[str, Any] = {}
        merge_sql = _build_merge(_BASE, keys, "value", params)
        params["value"] = json.dumps(value, default=str)
        params["cid"] = company.id
        db.execute(
            text(f"UPDATE companies SET metadata_json = ({merge_sql})::json WHERE id = :cid"),
            params,
        )
        # Drop any pending in-memory value so the ORM cannot flush a stale
        # full-dict write over the statement above, and so the next read of the
        # attribute reloads what is actually stored.
        db.expire(company, ["metadata_json"])
    else:
        _fallback_set(company, keys, value)

    if commit:
        db.commit()


def delete_metadata_value(db, company, path: MetadataPath, *, commit: bool = True) -> None:
    """Remove ``path`` from ``company.metadata_json``, leaving siblings intact."""
    keys = _normalize_path(path)

    if _is_postgres(db):
        params: Dict[str, Any] = {f"k{i}": key for i, key in enumerate(keys)}
        path_sql = ", ".join(f":k{i}" for i in range(len(keys)))
        params["cid"] = company.id
        db.execute(
            text(
                f"UPDATE companies SET metadata_json = "
                f"({_BASE} #- CAST(ARRAY[{path_sql}] AS text[]))::json WHERE id = :cid"
            ),
            params,
        )
        db.expire(company, ["metadata_json"])
    else:
        _fallback_delete(company, keys)

    if commit:
        db.commit()
