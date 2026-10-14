"""HAG-163: the Quant lane's own check script runs, and its LTV:CAC answer is pinned.

`quant_forge_tools_check.py` next to this file is a **verbatim copy** of
`hive/reports/quant-forge-tools-check.py` (Quant lane, card HAG-172), the script the
maths file `hive/reports/quant-forge-tools-maths.md` says reproduced every number in it.
Copied, not edited — sha256:

    88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67

This file pins **sections 3 and 5** of that script: LTV:CAC, and the annual-versus-monthly
churn trap. It is deliberately the python job's test rather than a step in the node job:
`pytest.ini` sets `testpaths = server/tests`, so a new file here is collected with no
change to `.github/workflows/pr-checks.yml`, whose node job lists every TypeScript test by
hand.

Why a test around a script that already passes: the script is the *reference*, and the
TypeScript implementation in `client/src/lib/tools/ltvCac.ts` is pinned to the same
literals in `server/tests/ltv-cac.test.ts`. Pinning both sides means a drift in either the
reference or the implementation fails a test instead of quietly disagreeing. The literals
below were read off the real output with `repr()`, not typed from the docs.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("quant_forge_tools_check.py")

# The maths file's worked example, Tool 3: ARPA $500/month, 80% gross margin, 2% monthly
# churn, $120,000 of fully loaded S&M, 24 customers won.
EXPECTED_LTV = "20000.00"
EXPECTED_CAC = "5000.00"
EXPECTED_RATIO = "4.0000"
EXPECTED_PAYBACK = "12.5000"


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
    been edited since. The same digest guards the copies that the two sibling tests run for
    Tool 1 and Tool 2, so the three tools cannot end up on different scripts.
    """
    digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert digest == "88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67", (
        f"the vendored check script is not the copy the maths file names (sha256 {digest})"
    )


def test_reference_worked_example_matches_the_hand_computation(output: str) -> None:
    """All four lines of the worked example, pinned whole."""
    assert f"LTV = 500 * 0.80 / 0.02 = {EXPECTED_LTV}" in output
    assert f"CAC = 120000 / 24 = {EXPECTED_CAC}" in output
    assert f"LTV:CAC = {EXPECTED_RATIO}" in output
    assert (
        f"CAC payback months = CAC/(ARPA*GM) = {EXPECTED_CAC} / 400.00 = {EXPECTED_PAYBACK}"
    ) in output


def test_reference_payback_denominator_is_gross_profit_per_customer(output: str) -> None:
    """$500 x 80% = $400, which is the number payback divides by — and LTV's numerator too.

    Asserted separately because it is the one figure that ties the two textbook lines
    together: `payback = CAC / (ARPA x GM)` and `LTV = (ARPA x GM) / churn` share it.
    """
    assert "= 5000.00 / 400.00 = 12.5000" in output


def test_reference_annual_form_agrees_with_the_monthly_form(output: str) -> None:
    """The same identity in the other unit, which is what makes the churn trap visible.

    The line is split around the float Python prints for 0.24 rather than pinned whole:
    `0.239999999999999991118216` is CPython's repr of the nearest double to 0.24, so a
    literal copy of it here would be asserting the interpreter's formatting, not the maths.
    The two ends are what matter — ARPA x 12 and the answer both equal the monthly form's.
    """
    assert "annual-churn form: LTV = ARPA_annual*GM/annual_churn = 6000*0.80/" in output
    line = next(l for l in output.splitlines() if l.startswith("annual-churn form:"))
    assert line.endswith(f"= {EXPECTED_LTV}"), (
        "the annual-churn form must give the same LTV as the monthly form at 2%/month"
    )


def test_reference_marks_the_zero_churn_case_as_needing_a_cap(output: str) -> None:
    """The reference calls it out itself: `churn = 0` has no finite LTV.

    The implementation's answer is the maths file's ruling — floor the churn at 0.1% per
    month and label the floor — which is why this assertion is about the *problem* and not
    about a number. A tool that printed the uncapped result would print an infinite score.
    """
    assert (
        "ltv churn=0             -> LTV undefined/infinite (churn = 0): needs a cap; "
        f"CAC = {EXPECTED_CAC}"
    ) in output


def test_reference_edge_cases_are_the_ones_the_page_reports(output: str) -> None:
    """The other four rows of the maths file's edge-case table, as the script prints them."""
    assert f"ltv gm=0                -> LTV = 0.00; CAC = {EXPECTED_CAC}" in output
    assert f"ltv cust=0              -> LTV = {EXPECTED_LTV}; CAC undefined (0 new customers)" in output
    assert f"ltv sm=0                -> LTV = {EXPECTED_LTV}; CAC = 0 -> ratio undefined" in output
    assert f"ltv churn=0.5 (50%/mo)  -> LTV = 800.00; CAC = {EXPECTED_CAC}" in output


def test_reference_reports_the_churn_trap_the_page_must_print(output: str) -> None:
    """Section 5, the trap: monthly churn is not twelve times monthly.

    Compounded, 2%/month is 21.53% a year; the naive 24% understates LTV by 11.5%. The page
    prints all three of those numbers.
    """
    assert "monthly churn 2% -> compounded annual churn = 0.215283 (21.53%)" in output
    assert (
        "naive 12*2% = 24% ; LTV with 24% = 20000.00 ; "
        "LTV with compounded = 22296.20 ; difference = 11.5%"
    ) in output


def test_the_trap_overstates_nothing(output: str) -> None:
    """The naive rate is bigger and its LTV is smaller — the direction is asserted, not assumed."""
    line = next(l for l in output.splitlines() if l.startswith("naive 12*2%"))
    naive_ltv = float(re.search(r"LTV with 24% = ([\d.]+)", line).group(1))
    compounded_ltv = float(re.search(r"LTV with compounded = ([\d.]+)", line).group(1))
    assert compounded_ltv > naive_ltv, (
        "a naive annual churn must understate LTV, never overstate it"
    )


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
    assert '<Route path="/tools/ltv-cac">' in _read("client/src/App.tsx")
    assert 'path: "/tools/ltv-cac"' in _read("scripts/generate-sitemap.ts")
    assert (
        "<loc>https://founderconsole.ai/tools/ltv-cac</loc>"
        in _read("client/public/sitemap.xml")
    )


def test_the_page_is_prerendered_with_its_own_canonical() -> None:
    """Edit three: without this entry the page is a soft duplicate of the homepage."""
    prerender = _read("server/seo-prerender.ts")
    assert 'path === "/tools/ltv-cac"' in prerender
    assert 'canonical: SITE_URL + "/tools/ltv-cac"' in prerender
    assert "function buildLtvCacBodyContent(): string {" in prerender
    assert "bodyContent: buildLtvCacBodyContent()," in prerender
    # A crawler should read the same substance the page shows, plus a way to sign up.
    body = prerender.split("function buildLtvCacBodyContent", 1)[1]
    assert "gross margin divided by monthly churn" in body
    assert "Fully loaded" in body or "fully loaded" in body
    assert "Monthly churn is not twelve times monthly" in body
    assert 'href="/auth"' in body
