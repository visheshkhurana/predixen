"""Published facts must match the product, not an older draft.

llms.txt is indexed and quoted. It used to list Starter $29 / Growth $49 /
Scale $99 as the published prices while /pricing says every feature is free
during the public beta, and it said 37 connectors while the registry has 34.
Organization sameAs also pointed at https://github.com/founderconsole, which
404s. The product repo is visheshkhurana/predixen; that URL is not a profile
we should ask a crawler to cite.
"""

from __future__ import annotations

import ast
from pathlib import Path

import server.connectors as connectors_pkg
from server.connectors.registry import ConnectorRegistry

ROOT = Path(__file__).resolve().parents[2]
LLMS = ROOT / "client" / "public" / "llms.txt"
SAMEAS_FILES = [
    ROOT / "client" / "index.html",
    ROOT / "client" / "src" / "pages" / "landing.tsx",
    ROOT / "server" / "seo-prerender.ts",
    LLMS,
]
# Current marketing surfaces. Historical campaign scripts (send_update_v*.py)
# stay as the text that was sent.
COUNT_FILES = [
    LLMS,
    ROOT / "client" / "index.html",
    ROOT / "client" / "src" / "pages" / "landing.tsx",
    ROOT / "client" / "src" / "pages" / "faq.tsx",
    ROOT / "client" / "src" / "pages" / "product.tsx",
    ROOT / "client" / "src" / "pages" / "ai-cfo.tsx",
    ROOT / "client" / "src" / "pages" / "alternatives.tsx",
    ROOT / "client" / "src" / "pages" / "how-it-works.tsx",
    ROOT / "client" / "src" / "pages" / "marketing-features.tsx",
    ROOT / "client" / "src" / "pages" / "auth.tsx",
    ROOT / "server" / "seo-prerender.ts",
    ROOT / "server" / "email" / "templates.py",
    # Added with the ai-cfo fix: the PR edits these three to say 34 and they were
    # not asserted, so a revert to 37 here would have passed CI.
    ROOT / "client" / "src" / "data" / "blog-posts.ts",
    ROOT / "client" / "src" / "components" / "marketing" / "redesign" / "TwinDashboardDemo.tsx",
    ROOT / "server" / "services" / "notifications.py",
]

# Every public marketing surface that carried the retired trial offer. The
# previous version of this guard read landing.tsx only, which is exactly why
# /ai-cfo kept selling a 30-day trial and "$29/month" while the rest of the
# site said free during early access.
#
# Legal text is deliberately absent: client/src/pages/terms.tsx and the Terms
# block in server/seo-prerender.ts still describe a one-time 30-day trial.
# Changing legal copy is a separate decision, not a marketing-string fix.
TRIAL_FILES = [
    ROOT / "client" / "src" / "pages" / "landing.tsx",
    ROOT / "client" / "src" / "pages" / "ai-cfo.tsx",
    ROOT / "client" / "src" / "pages" / "pricing.tsx",
    ROOT / "client" / "src" / "pages" / "faq.tsx",
    ROOT / "client" / "src" / "pages" / "product.tsx",
    ROOT / "client" / "src" / "pages" / "marketing-features.tsx",
    ROOT / "client" / "src" / "pages" / "alternatives.tsx",
    ROOT / "client" / "src" / "pages" / "how-it-works.tsx",
    ROOT / "client" / "src" / "pages" / "auth.tsx",
]
RETIRED_OFFER_PHRASES = (
    "30-day",
    "Start Free Trial",
    "Paid plans from $29",
)
STALE_COUNT_PHRASES = (
    "37 data connector",
    "37 Data Connector",
    "37 connectors",
    "37 read-only",
    "37 integrations",
    "37 real OAuth",
    "37 production connector",
    'value: 37, suffix: "+"',
    'value="37+"',
)


def _registered_module_names() -> list[str]:
    source = (ROOT / "server" / "connectors" / "__init__.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_CONNECTOR_MODULES":
                    return list(ast.literal_eval(node.value))
    raise AssertionError("_CONNECTOR_MODULES not found")


def test_registry_has_34_connectors():
    names = _registered_module_names()
    assert len(names) == 34, names
    assert len(set(names)) == 34
    connectors_pkg.load_all_connectors()
    registered = ConnectorRegistry.get_available_providers()
    assert len(registered) == 34, sorted(registered)


def test_llms_txt_prices_the_free_beta_and_counts_34_connectors():
    text = LLMS.read_text()
    lowered = " ".join(text.lower().split())
    assert "every feature is free during the public beta" in lowered
    assert "no plan is charged yet" in lowered
    assert "paid tiers come later" in lowered
    # Planned dollar amounts must not be the citable price. /pricing still
    # shows them as the later plan, and this file must not.
    assert "$29" not in text
    assert "$49" not in text
    assert "$99" not in text
    assert "34 read-only data connectors" in text
    assert "37" not in text


def test_sameas_does_not_cite_the_missing_github_org():
    for path in SAMEAS_FILES:
        text = path.read_text()
        assert "github.com/founderconsole" not in text, path


def test_marketing_pages_do_not_sell_a_30_day_trial():
    """The retired offer, checked on every page that carried it.

    Assertion scope is the point: the old version read landing.tsx only, so
    ai-cfo.tsx could ship the same claim -- in JSON-LD, no less -- and pass.
    """
    for path in TRIAL_FILES:
        text = path.read_text()
        for phrase in RETIRED_OFFER_PHRASES:
            assert phrase not in text, f"{path}: still sells the retired offer: {phrase!r}"


def test_landing_frames_the_published_plans_as_planned():
    text = (ROOT / "client/src/pages/landing.tsx").read_text()
    assert "Starter ($29)" not in text
    assert "prices below are planned for later" in text


def test_current_marketing_copy_does_not_claim_37_connectors():
    for path in COUNT_FILES:
        text = path.read_text()
        for phrase in STALE_COUNT_PHRASES:
            assert phrase not in text, f"{path}: still says {phrase!r}"
