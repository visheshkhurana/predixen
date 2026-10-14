"""HAG-163: the Quant lane's own check script runs, and its dilution answer is pinned.

`quant_forge_tools_check.py` next to this file is a **verbatim copy** of
`hive/reports/quant-forge-tools-check.py` (Quant lane, card HAG-172), the script the
maths file `hive/reports/quant-forge-tools-maths.md` says reproduced every number in it.
Copied, not edited — sha256:

    88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67

This file pins **section 2, DILUTION** of that script. It is deliberately the python
job's test rather than a step in the node job: `pytest.ini` sets `testpaths =
server/tests`, so a new file here is collected with no change to
`.github/workflows/pr-checks.yml`, whose node job lists every TypeScript test by hand.

Why a test around a script that already passes: the script is the *reference*, and the
TypeScript implementation in `client/src/lib/tools/dilution.ts` is pinned to the same
literals in `server/tests/dilution.test.ts`. Pinning both sides means a drift in either
the reference or the implementation fails a test instead of quietly disagreeing. The
worked-example literals below are the same numbers that file asserts.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("quant_forge_tools_check.py")

# The maths file's worked example, Tool 2: $8M pre-money, $2M raised, 8,000,000 founder
# shares, 1,000,000 pool shares, a 12% post-money pool target.
EXPECTED_NEW_POOL_SHARES = 411_765
EXPECTED_INVESTOR_SHARES = 2_352_941
EXPECTED_POST_SHARES = 11_764_706
EXPECTED_FOUNDER_PCT = 0.6800
EXPECTED_POOL_PCT = 0.1200
EXPECTED_INVESTOR_PCT = 0.2000


@pytest.fixture(scope="module")
def output() -> str:
    """Run the reference script once; every assertion below reads this."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"the Quant lane's check script exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result.stdout


def test_the_reference_script_is_the_one_the_maths_file_records() -> None:
    """Byte-identity is the whole value of vendoring it, so it is asserted, not assumed.

    Compared against the literal the maths file records rather than against the file in
    `hive/reports/`: CI has no access to the hive, and the point is that this copy has not
    been edited since. The same digest guards the copy that `test_quant_forge_tools.py`
    runs for Tool 1, so the two tools cannot end up on different scripts.
    """
    digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert digest == "88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67", (
        f"the vendored check script is not the copy the maths file names (sha256 {digest})"
    )


def test_reference_pool_shuffle_matches_the_hand_computation(output: str) -> None:
    """The row the page's headline is built on: 20% to the investor, 68% to the founders."""
    assert (
        "pool to 12%:     "
        f"dP={EXPECTED_NEW_POOL_SHARES} N={EXPECTED_INVESTOR_SHARES} post={EXPECTED_POST_SHARES} "
        f"investor%={EXPECTED_INVESTOR_PCT:.4f} founder%={EXPECTED_FOUNDER_PCT:.4f} "
        f"pool%={EXPECTED_POOL_PCT:.4f}"
    ) in output, "the reference script no longer reproduces the maths file's worked example"


def test_reference_no_pool_case_is_the_simple_formula(output: str) -> None:
    """With no pool the founders keep 71.11%, which is the number a naive tool prints."""
    assert (
        "no pool change: dP=0 N=2250000 post=11250000 "
        "investor%=0.2000 founder%=0.7111"
    ) in output


def test_reference_brute_force_agrees_with_the_algebra(output: str) -> None:
    """The independent check in the script: solving by iteration on price, not by formula."""
    assert (
        f"brute-force check: dP={EXPECTED_NEW_POOL_SHARES} N={EXPECTED_INVESTOR_SHARES} "
        f"post={EXPECTED_POST_SHARES}  (matches algebra: True)"
    ) in output


def test_reference_confirms_the_investor_share_is_independent_of_the_pool(output: str) -> None:
    """`R / (V_pre + R)` is 0.2000 both with the pool shuffle and without it.

    This is the TEXTBOOK row, and the reason the page can say the investor's percentage
    does not move when the pool target does.
    """
    assert "simple check R/(V_pre+R) = 0.2000" in output
    assert output.count("investor%=0.2000") == 2, (
        "the investor's share must be identical in the no-pool and 12%-pool rows"
    )


def test_reference_reports_the_cumulative_multi_round_figure_the_page_quotes(output: str) -> None:
    """The one multi-round number the page prints, pinned to the script that derived it."""
    assert (
        "cumulative keep (0.81*0.82*0.85) = 0.564570 -> cumulative dilution = 0.4354"
    ) in output


def test_the_reference_never_prints_a_degenerate_float(output: str) -> None:
    """Asserted over the whole output, as a standalone token.

    A bare `inf` or `nan` surrounded by non-letters is a value; the script legitimately
    prints the *words* "undefined" and "infinite" inside reason strings, so a naive
    substring check would fail on those while saying nothing about the numbers.
    """
    leaked = re.search(r"(?<![A-Za-z])(inf|infinity|nan)(?![A-Za-z])", output, re.IGNORECASE)
    assert leaked is None, (
        f"the reference script printed a degenerate float {leaked.group(0)!r} as a value"
    )


# ---------------------------------------------------------------------------------------
# The THREE edits a new public page needs, asserted here rather than only in the TypeScript
# test. `pr-checks.yml` lists every TypeScript test by hand and is on the hold list, so a
# new `.test.ts` does not run in CI; this file is collected by `pytest.ini`'s `testpaths`
# with no workflow change at all. The third edit is the one that matters: `injectSEO`
# returns the shell untouched for a path it does not know, and that shell is `index,
# follow` with the homepage canonical, so an unmapped page ships as a soft duplicate of `/`
# and can never rank. The `<Route>` and the sitemap are already held by CI —
# `sitemap-drift.test.ts` and the `generate:sitemap` + `git diff --exit-code` step.
# ---------------------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_the_page_is_served_and_the_sitemap_can_see_it() -> None:
    """Edits one and two."""
    assert '<Route path="/tools/dilution">' in _read("client/src/App.tsx")
    assert 'path: "/tools/dilution"' in _read("scripts/generate-sitemap.ts")
    assert (
        "<loc>https://founderconsole.ai/tools/dilution</loc>"
        in _read("client/public/sitemap.xml")
    )


def test_the_page_is_prerendered_with_its_own_canonical() -> None:
    """Edit three: without this entry the page is a soft duplicate of the homepage."""
    prerender = _read("server/seo-prerender.ts")
    assert 'path === "/tools/dilution"' in prerender
    assert 'canonical: SITE_URL + "/tools/dilution"' in prerender
    assert "function buildDilutionBodyContent(): string {" in prerender
    assert "bodyContent: buildDilutionBodyContent()," in prerender
    # A crawler should read the same substance the page shows, plus a way to sign up.
    body = prerender.split("function buildDilutionBodyContent", 1)[1]
    assert "amount raised divided by the post-money valuation" in body
    assert "dilutes existing holders and never the new investor" in body
    assert 'href="/auth"' in body
