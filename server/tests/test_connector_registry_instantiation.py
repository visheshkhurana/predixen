"""HAG-262. A registered connector that cannot be instantiated takes the whole
provider catalogue down with it.

`ConnectorRegistry.list_connectors()` builds every registered class in a loop and
calls `get_provider_info()` on the instance. Two classes were registered while
still abstract -- `GoogleSheetsConnector` and `RestAPIConnector` shipped
`test_connection`/`fetch_data` but never `authenticate`, which
`BaseConnector.authenticate` declares as `@abstractmethod`. Python raises on
instantiation, so the loop raised, so `GET /connectors/providers` answered 500
for *every* provider.

It is unconditional rather than occasional, and that is the part that hid it:
`load_all_connectors()` runs at module import (`server/api/connectors.py:34`), so
all 34 classes are registered before any request arrives, and the loop walks them
in registration order, where `google_sheets` is eighth.

The category filter looked like an escape hatch and is not one: it skips a class
before instantiating it, and both broken classes had silently inherited the base
default `PAYROLL` (they spelled the attribute `CATEGORY`, the base declares
`PROVIDER_CATEGORY`). So `?category=hris` returned 200 while the unfiltered call
and `?category=payroll` both returned 500 -- the filter dodged them for every
category except the one they were in.

Four things are pinned here, and the first two fail on the commit this fixes:

1. Every registered class is instantiable. This is the one that matters. The
   registry guard added alongside it skips a bad class instead of raising, which
   would otherwise turn a 500 into a silent omission -- this test is what keeps
   a skip loud in CI.
2. The route handler answers the unfiltered call, which is what a client sends.
3. The two classes declare the category they document, and no connector module
   spells the attribute `CATEGORY`. That misspelling is what made the filter look
   like a workaround for a defect it merely failed to expose.
4. The guard itself: one broken class is skipped and the rest still come back.

Run: .venv/bin/python -m pytest server/tests/test_connector_registry_instantiation.py -q
"""

import asyncio
import pathlib
import re

import pytest

import server.connectors as connectors_pkg
from server.connectors.base import BaseConnector, ConnectorConfig, ProviderCategory
from server.connectors.registry import ConnectorRegistry

CONNECTORS_DIR = pathlib.Path("server/connectors")


@pytest.fixture(scope="module", autouse=True)
def _loaded():
    """Mirror the API module, which loads the registry at import time."""
    connectors_pkg.load_all_connectors()
    assert ConnectorRegistry._connectors, "no connectors registered at all"


def test_every_registered_connector_is_instantiable():
    """The defect, stated directly. Fails on the base commit with a TypeError."""
    uninstantiable = []

    for provider_id, connector_class in ConnectorRegistry._connectors.items():
        try:
            connector_class(ConnectorConfig(provider_id=provider_id, company_id=0))
        except Exception as e:  # noqa: BLE001 - the point is to name every one
            uninstantiable.append(f"{provider_id} ({connector_class.__name__}): {e}")

    assert uninstantiable == [], (
        "registered connectors that cannot be constructed -- each one makes "
        "GET /connectors/providers answer 500 for every provider:\n  "
        + "\n  ".join(uninstantiable)
    )


def test_no_connector_is_registered_with_abstract_methods():
    """Same defect, narrower reading: the registry is for concrete classes."""
    offenders = [
        f"{provider_id} -> {sorted(getattr(cls, '__abstractmethods__', []))}"
        for provider_id, cls in ConnectorRegistry._connectors.items()
        if getattr(cls, "__abstractmethods__", frozenset())
    ]

    assert offenders == [], (
        "these are registered but still abstract, so instantiation raises:\n  "
        + "\n  ".join(offenders)
    )


def test_list_connectors_returns_the_catalogue_without_raising():
    listed = ConnectorRegistry.list_connectors()
    registered = set(ConnectorRegistry._connectors)

    assert isinstance(listed, list) and listed, "the catalogue came back empty"
    assert len(listed) == len(registered), (
        f"{len(registered)} connectors are registered but only {len(listed)} were "
        "listed -- the difference is being skipped"
    )

    ids = {p.get("provider_id") or p.get("id") for p in listed}
    assert {"google_sheets", "rest_api"} <= ids, (
        "the two connectors this card is about are missing from the catalogue"
    )


def test_the_providers_route_answers_the_unfiltered_call():
    """The route, not just the registry: this is what takes the 500."""
    from server.api import connectors as connectors_api

    routes = {r.path for r in connectors_api.router.routes}
    assert "/connectors/providers" in routes, "the route moved"

    # `current_user` is only used for auth, so an object stands in for it.
    providers = asyncio.run(
        connectors_api.list_providers(category=None, current_user=object())
    )
    assert isinstance(providers, list) and providers

    # And the category that used to be the only one that 500'd still works.
    payroll = asyncio.run(
        connectors_api.list_providers(category="payroll", current_user=object())
    )
    assert isinstance(payroll, list)


def test_declared_categories_are_the_ones_the_registry_reads():
    """The misspelling that made the filter look like an escape hatch."""
    sheets = ConnectorRegistry._connectors["google_sheets"]
    rest = ConnectorRegistry._connectors["rest_api"]

    assert sheets.PROVIDER_CATEGORY is ProviderCategory.ACCOUNTING, (
        "Google Sheets advertises the category the base default gives it, not "
        "the one it documents"
    )
    assert rest.PROVIDER_CATEGORY is ProviderCategory.CRM, (
        "REST API advertises the category the base default gives it, not the "
        "one it documents"
    )

    # Source-level, so the next connector copied from this pair cannot reintroduce
    # it: `CATEGORY` is not an attribute the base class or the registry knows.
    misspelled = []
    for path in sorted(CONNECTORS_DIR.glob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if re.match(r"^\s+CATEGORY\s*=", line):
                misspelled.append(f"{path}:{lineno}: {line.strip()}")

    assert misspelled == [], (
        "PROVIDER_CATEGORY is the attribute the registry filters on; a bare "
        "CATEGORY is dead code and silently inherits the base default:\n  "
        + "\n  ".join(misspelled)
    )


def test_a_broken_connector_is_skipped_and_the_rest_survive():
    """The guard. Without it, one bad class is a 500 for all 34."""

    class CannotBeBuilt(BaseConnector):
        PROVIDER_ID = "hag262_broken"
        PROVIDER_NAME = "HAG-262 broken fixture"

    registry = ConnectorRegistry._connectors
    assert "hag262_broken" not in registry, "fixture name collides with a real provider"
    registry["hag262_broken"] = CannotBeBuilt
    try:
        with pytest.raises(TypeError):
            CannotBeBuilt(ConnectorConfig(provider_id="hag262_broken", company_id=0))

        listed = ConnectorRegistry.list_connectors()
        ids = {p.get("provider_id") or p.get("id") for p in listed}

        assert "hag262_broken" not in ids, "the broken class should not be listed"
        assert len(listed) == len(registry) - 1, (
            "only the broken connector should be missing from the catalogue"
        )
    finally:
        registry.pop("hag262_broken", None)
