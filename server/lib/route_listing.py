"""List every route an app or router serves, across FastAPI versions.

From FastAPI 0.162, ``app.include_router`` no longer copies the child router's
routes into ``app.routes``; it appends one ``_IncludedRouter`` entry per
included router. Anything that walks ``app.routes`` to find paths now sees
those wrappers (no ``.path``) instead of the real routes. ``iter_routes``
expands them with FastAPI's public ``iter_route_contexts`` when it exists and
falls back to the plain list on older versions.
"""
from __future__ import annotations

from typing import Any, Iterator

try:  # FastAPI >= 0.162
    from fastapi.routing import iter_route_contexts as _iter_route_contexts
except ImportError:  # pragma: no cover - older FastAPI flattened on include
    _iter_route_contexts = None


def iter_routes(app_or_router: Any) -> Iterator[Any]:
    """Yield each served route. Every item has ``.path`` and ``.methods``
    (``None`` for mounts and other non-HTTP routes), with the include prefix
    already applied."""
    routes = list(app_or_router.routes)
    if _iter_route_contexts is None:
        yield from routes
        return
    yield from _iter_route_contexts(routes)


def route_paths(app_or_router: Any) -> set[str]:
    """The set of path templates served, e.g. ``/api/companies/{company_id}``."""
    return {p for r in iter_routes(app_or_router) if (p := getattr(r, "path", None))}
