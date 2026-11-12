"""Industry homepages (`/for/<slug>`): wiring and published facts, from pytest.

Why a pytest as well as `server/tests/industry-homepage.test.ts`: CI's pytest job
collects every `test_*.py`, while TypeScript tests only run when someone adds a
step to `.github/workflows/pr-checks.yml`, which is hold-listed. So this file
pins the parts that can be checked from source text without Node, and runs the
TypeScript suite too when `tsx` is installed (it is in a dev checkout; it is
skipped, not failed, where node_modules is absent).

Run: uv run pytest server/tests/test_industry_homepage.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "client" / "src" / "data" / "industry-pages.ts"
APP = ROOT / "client" / "src" / "App.tsx"
KNOWN_ROUTES = ROOT / "server" / "known-routes.ts"
SITEMAP = ROOT / "client" / "public" / "sitemap.xml"
PRERENDER = ROOT / "server" / "seo-prerender.ts"
PICKER = ROOT / "client" / "src" / "components" / "marketing" / "IndustryPicker.tsx"
TS_TEST = ROOT / "server" / "tests" / "industry-homepage.test.ts"
CONNECTORS_INIT = ROOT / "server" / "connectors" / "__init__.py"


def _slugs() -> list[str]:
    text = CONFIG.read_text()
    block = text[text.index("export const INDUSTRY_PAGES") :]
    return re.findall(r'^    slug: "([a-z0-9-]+)",$', block, flags=re.M)


def test_six_industries_are_configured():
    slugs = _slugs()
    assert len(slugs) == len(set(slugs))
    assert {"d2c", "saas", "marketplace", "agency", "fintech", "startup"} <= set(slugs)


def test_route_known_route_and_sitemap_for_every_industry():
    assert '<Route path="/for/:slug">' in APP.read_text()
    assert '"/for/:slug"' in KNOWN_ROUTES.read_text()
    sitemap = SITEMAP.read_text()
    for slug in _slugs():
        assert f"<loc>https://founderconsole.ai/for/{slug}</loc>" in sitemap, slug


def test_prerender_reads_the_shared_config():
    text = PRERENDER.read_text()
    assert 'from "../client/src/data/industry-pages"' in text
    assert 'path.startsWith("/for/")' in text
    # No slug is hard-coded in the server: the config is the only list.
    branch = text[text.index('path.startsWith("/for/")') :][:1200]
    for slug in _slugs():
        assert f'"{slug}"' not in branch, slug


def test_copy_respects_published_facts():
    text = CONFIG.read_text()
    for phrase in ("$29", "$49", "$99", "30-day", "Start Free Trial", "37 "):
        assert phrase not in text, phrase
    for count in re.findall(r"(\d+) (?:read-only )?(?:data )?connectors", text):
        assert count == "34"
    assert "free during the public beta" in text.lower()


def test_connectors_named_are_registered():
    registered = set(re.findall(r'"([a-z_]+)"', CONNECTORS_INIT.read_text()))
    text = CONFIG.read_text()
    for group in re.findall(r"connectors: \[([^\]]*)\]", text):
        for name in re.findall(r'"([^"]+)"', group):
            assert name.lower().replace(" ", "_") in registered, name


def test_picker_is_client_only_and_bot_gated():
    picker = PICKER.read_text()
    assert "shouldShowIndustryPicker" in picker
    assert "navigator.userAgent" in picker
    # The SSR builder for industry pages must never emit the picker.
    prerender = PRERENDER.read_text()
    assert "What kind of business do you run" not in prerender
    assert "industry-picker" not in prerender


@pytest.mark.skipif(
    not (ROOT / "node_modules" / ".bin" / "tsx").exists() or shutil.which("node") is None,
    reason="node_modules/tsx not installed",
)
def test_typescript_suite_passes():
    result = subprocess.run(
        [str(ROOT / "node_modules" / ".bin" / "tsx"), "--test", str(TS_TEST)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
