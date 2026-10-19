"""HAG-265. Six of the sixteen route->feature patterns named no live route.

`ROUTE_FEATURE_MAP` in `server/core/subscription.py` is what the paywall
middleware consults to decide which feature a request belongs to. Six of its
patterns had drifted off the routes they were meant to name, so a request to
those endpoints resolved to no feature at all.

The two that matter most, because they are the most expensive per-call AI paths
on the product:

- `POST /companies/{company_id}/chat` -- the main Copilot call. `COPILOT` was
  bound to a `/companies/N/copilot` segment that does not exist, so `chat` was
  named by no pattern in the map.
- `POST /scenarios/{scenario_id}/simulate` -- what the product's own scenario
  page calls. `SIMULATIONS` was bound to the `/simulation/...` v2 family, which
  `/scenarios` does not use.

The other four were path-shape mismatches: the routers are registered and the
endpoints are live, the pattern just spelled the segment differently
(`truth-scan` for `/truth/`, `export/board-deck` for `/board-export/`,
`digital-twin` for `/twin/`, `doc-generator/` for `/companies/N/doc-generator/`).

A note on how this is measured, because measuring it the obvious way gives the
wrong answer: FastAPI route paths are *templates*, so `path` is
`/companies/{company_id}/chat`, not `/companies/42/chat`. A pattern containing
`\\d+` therefore matches nothing if it is tested against the template, and every
`/companies/...` pattern looks dead. The paths are concretised first.

This file fails on the commit it fixes, with six dead patterns named.

Run: .venv/bin/python -m pytest server/tests/test_route_feature_map.py -q
"""

import re

import pytest

from server.core.plans import Feature
from server.core.subscription import ROUTE_FEATURE_MAP


def _concretise(template: str) -> str:
    """Turn a FastAPI path template into something a request could look like."""
    parts = re.split(r"(\{[^}]*\})", template)
    out = []
    for part in parts:
        if part.startswith("{") and part.endswith("}"):
            name = part[1:-1].lower()
            out.append("42" if name.endswith("_id") or name == "id" else "abc")
        else:
            out.append(part)
    return "".join(out)


@pytest.fixture(scope="module")
def live_paths():
    """Every route the app actually serves, including the background-loaded ones."""
    from server import main

    # `_register_remaining_routers` runs on a daemon thread during startup, so a
    # plain import only ever sees the critical routers (8 of 417).
    main._register_remaining_routers(main.app)
    templates = sorted({getattr(r, "path", "") for r in main.app.routes}
                       - {""})
    assert len(templates) > 100, (
        f"only {len(templates)} routes were registered -- the app did not finish "
        "assembling, so this test would pass vacuously"
    )
    return [_concretise(t) for t in templates]


def test_no_pattern_is_dead(live_paths):
    """The defect. Fails on the base commit naming all six."""
    dead = [
        f"{feature.name}: {pattern.pattern}"
        for pattern, feature in ROUTE_FEATURE_MAP
        if not any(pattern.search(path) for path in live_paths)
    ]

    assert dead == [], (
        "these patterns match no live route, so a request to the endpoints they "
        "were meant to name resolves to no feature:\n  " + "\n  ".join(dead)
    )


def test_the_two_expensive_paths_are_named(live_paths):
    """The two the map most needed to name, asserted by their real shape."""
    for path in ("/companies/42/chat", "/scenarios/42/simulate"):
        assert path in live_paths, f"{path} is not a live route any more"

        named = [
            feature.name
            for pattern, feature in ROUTE_FEATURE_MAP
            if pattern.search(path)
        ]
        assert named, f"{path} is a live route named by no pattern in the map"


def test_the_trailing_feedback_route_still_resolves_to_copilot(live_paths):
    """A prefix pattern has to keep working for the paths under it."""
    feature_for = {
        path: next(
            (f.name for p, f in ROUTE_FEATURE_MAP if p.search(path)), None
        )
        for path in ("/companies/42/chat", "/companies/42/chat/feedback",
                     "/companies/42/quick-chat")
    }

    assert feature_for == {
        "/companies/42/chat": "COPILOT",
        "/companies/42/chat/feedback": "COPILOT",
        "/companies/42/quick-chat": "COPILOT",
    }, f"Copilot's routes do not all resolve to COPILOT: {feature_for}"


def test_a_scenario_id_need_not_be_numeric(live_paths):
    """`/scenarios/shared/{share_uuid}` is live, so `\\d+` would have been wrong."""
    pattern = next(
        p for p, f in ROUTE_FEATURE_MAP
        if f is Feature.SIMULATIONS and "scenarios" in p.pattern
    )

    assert pattern.search("/scenarios/9f2c1e77-4b21/simulate"), (
        "scenario ids are matched as digits, but the map's own sibling route "
        "takes a uuid"
    )
    assert any(p.startswith("/scenarios/shared/") for p in live_paths), (
        "the /scenarios/shared/{share_uuid} route is gone, so this reasoning "
        "about non-numeric ids no longer has a witness"
    )


def test_the_map_still_covers_every_feature_it_claimed_to():
    """`copilot` being dead meant COPILOT had no live pattern at all."""
    covered = {feature for _, feature in ROUTE_FEATURE_MAP}

    for feature in (Feature.COPILOT, Feature.SIMULATIONS, Feature.TRUTH_SCAN,
                    Feature.DATA_CONNECTORS, Feature.FUNDRAISING_OS,
                    Feature.CAP_TABLE, Feature.BOARD_DECK, Feature.HIRING_PLANNER,
                    Feature.DIGITAL_TWIN, Feature.AI_GRAPHICS,
                    Feature.INVESTOR_ROOM, Feature.DOCUMENT_GENERATOR,
                    Feature.FLIGHT_SIMULATOR):
        assert feature in covered, f"{feature.name} is named by no pattern"
