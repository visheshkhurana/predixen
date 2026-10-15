"""HAG-163: the Quant lane's own check script runs, and its burn-multiple answer is pinned.

`quant_forge_tools_check.py` next to this file is a **verbatim copy** of
`hive/reports/quant-forge-tools-check.py` (Quant lane, card HAG-172), the script the
maths file `hive/reports/quant-forge-tools-maths.md` says reproduced every number in it.
Copied, not edited — sha256 of both files:

    88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67

The card's instruction is to *run that script in the PR's tests*. That is what this file
does, and it is deliberately the python job's test rather than a step in the node job:
`pytest.ini` sets `testpaths = server/tests`, so a new file here is collected with no
change to `.github/workflows/pr-checks.yml`, whose node job lists every TypeScript test
by hand and would otherwise need a new line for each one.

Why a test around a script that already passes: the script is the *reference*, and the
TypeScript implementation in `client/src/lib/tools/burnMultiple.ts` is pinned to the same
literals in `server/tests/burn-multiple.test.ts`. Pinning both sides means a drift in
either the reference or the implementation fails a test instead of quietly disagreeing.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("quant_forge_tools_check.py")

# The maths file's worked example, Tool 1. These are the numbers
# `client/src/lib/tools/burnMultiple.ts` must also produce.
EXPECTED_NET_NEW_ARR = 150_000
EXPECTED_NET_BURN = 450_000
EXPECTED_MULTIPLE = 3.0


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
    been edited since.
    """
    import hashlib

    digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert digest == "88b139c09d963259f31b5dda61660f1fac42027b3a00116320491d79a39c8a67", (
        f"the vendored check script is not the copy the maths file names (sha256 {digest})"
    )


def test_reference_net_new_arr_and_net_burn(output: str) -> None:
    assert f"net new ARR = 180000 + 30000 - 45000 - 15000 = {EXPECTED_NET_NEW_ARR}" in output
    assert f"net burn    = 600000 - 150000 = {EXPECTED_NET_BURN}" in output


def test_reference_burn_multiple_is_three(output: str) -> None:
    assert re.search(
        rf"burn multiple = {EXPECTED_NET_BURN} / {EXPECTED_NET_NEW_ARR} = 3\.0000", output
    ), "the reference script no longer reports 3.0000 for the worked example"


def test_reference_reconciles_the_worked_example(output: str) -> None:
    """CHOICE 3's check, on the reference's own dataset."""
    assert "cross-check (ending-starting ARR) = 150000 == net_new_arr? True" in output


def test_reference_confirms_the_window_cannot_move_the_ratio(output: str) -> None:
    """The monthly-average variant is 3.0000 as well, which is why the page says so."""
    assert "monthly-average variant: burn/3 = 150000.00, ARR/3 = 50000.00, ratio = 3.0000" in output


def test_reference_reports_every_burn_multiple_edge_case(output: str) -> None:
    """The four rows of the maths file's edge-case table that concern this tool."""
    assert "bm burn=300k arr=0      -> undefined (no new ARR): division by zero" in output
    assert "bm burn=300k arr=-50k   -> -6.0000 (shrinking: negative, not 'efficient')" in output
    assert "bm burn=-20k arr=100k   -> -0.2000 (cash-flow positive: clamp to 0 / 'n/a')" in output
    assert "bm burn=0    arr=100k   -> 0.0000" in output


def test_the_reference_never_prints_infinity_or_nan(output: str) -> None:
    """The summary table's closing rule, asserted over the reference's whole output.

    Matched as a standalone token, not as a substring: the script legitimately prints the
    words "undefined/infinite (churn = 0)" as a *reason string*, and a naive
    `"inf" not in output` would fail on that word while saying nothing about the numbers.
    A real degenerate value prints as a bare `inf` or `nan` surrounded by non-letters.
    """
    leaked = re.search(r"(?<![A-Za-z])(inf|infinity|nan)(?![A-Za-z])", output, re.IGNORECASE)
    assert leaked is None, (
        f"the reference script printed a degenerate float {leaked.group(0)!r} as a value"
    )
