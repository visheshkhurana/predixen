"""HAG-233: the free runway calculator is reachable above the fold on `/`.

Why this file is Python rather than a `.test.ts`: `pr-checks.yml` lists every
TypeScript test file by hand as its own step, and that workflow is on the hold
list, so a new `.test.ts` would not run in CI at all. `pytest.ini` sets
`testpaths = server/tests`, so this file is collected automatically with no
workflow change. It is the half of the coverage that actually executes.

What is being guarded. `/` already linked /tools/runway-calculator in two
places — the footer (`MarketingLayout`) and the server-rendered homepage body
(`buildLandingBodyContent`) — so the card's original premise, "add the link",
was already satisfied for a crawler. The real gap was a human looking at the
hero, who saw two buttons and no way in without creating an account. A change
that adds a third invisible link cannot be measured, so the assertions below pin
the three things that make this one measurable and honest:

  1. the link is inside `Hero()`, i.e. above the fold — not a footer or midpage
     link, which is what the card explicitly ruled out;
  2. its click is emitted as `cta_click` with a location no other call site
     uses, or the hero's clicks are indistinguishable from the signup button's
     and the experiment cannot be read;
  3. the "input submitted" half is `calculator_used` on the runway calculator,
     once per page load, from the first input event.

The claims assertion reads the whole visible line through `visible_text()`, not
between tag boundaries: the JSX joining the prompt to its link is `{" "}`, which
a `>`/`<` pattern cannot span, so the original extractor never saw the lead
sentence. HAG-299 instance 3.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

LANDING = REPO_ROOT / "client/src/pages/landing.tsx"
CALCULATOR = REPO_ROOT / "client/src/pages/runway-calculator.tsx"
MARKETING_LAYOUT = REPO_ROOT / "client/src/components/marketing/MarketingLayout.tsx"
PRERENDER = REPO_ROOT / "server/seo-prerender.ts"

CALC_PATH = "/tools/runway-calculator"


def visible_text(jsx: str) -> str:
    """The words a reader sees in a JSX block.

    `re.findall(r">([^<>{}]+)<", block)` was this file's original extractor and
    it was blind: the JSX between "Just want your runway?" and the link text is
    `{" "}`, and a pattern that excludes `{` and `}` cannot span it, so no match
    could start at the opening tag and the leading sentence was never scanned
    while the assertion read as though it covered the whole line. HAG-299
    instance 3.

    This walks the block instead of pattern-matching across it. Brace depth, so
    the `>` in `onClick={() => ...}` does not end the tag early; comments
    dropped; `{" "}` kept as the space it renders as; every other expression
    dropped, because an expression is not visible copy.
    """
    jsx = re.sub(r"\{/\*.*?\*/\}", " ", jsx, flags=re.S)
    space_only = re.compile(r'\{\s*"(\s*)"\s*\}')
    out: list[str] = []
    i, depth, in_tag = 0, 0, False
    while i < len(jsx):
        ch = jsx[i]
        if ch == "<" and depth == 0:
            in_tag = True
        elif ch == ">" and in_tag and depth == 0:
            in_tag = False
        elif ch == "{":
            if depth == 0:
                m = space_only.match(jsx, i)
                if m:
                    out.append(m.group(1))
                    i = m.end()
                    continue
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif not in_tag and depth == 0:
            out.append(ch)
        i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def prompt_block() -> str:
    """The one line this file exists to police: the hero's calculator prompt,
    from just past its opening tag to just before its closing one."""
    hero = hero_slice()
    block = hero[hero.index('data-testid="text-hero-calculator-prompt"') :]
    block = block[block.index(">") + 1 : block.index("</motion.p>")]
    return block


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def hero_slice() -> str:
    """Just the `Hero()` component: the part of `/` a visitor sees first."""
    src = read(LANDING)
    start = src.index("function Hero() {")
    end = src.index("function HowItWorks() {", start)
    return src[start:end]


def test_the_hero_links_the_calculator():
    hero = hero_slice()
    assert f'href="{CALC_PATH}"' in hero, "the hero has no link to the free calculator"


def test_the_link_is_above_the_fold_not_another_footer_link():
    # The card ruled out "another footer-or-midpage link", so being inside
    # Hero() is the requirement, and the demo mock sits below it.
    src = read(LANDING)
    hero = hero_slice()
    assert f'href="{CALC_PATH}"' in hero
    # "<TwinDashboardDemo />" (the usage, not the import at the top of the file)
    # is the demo mock that sits below the button row.
    assert src.index(f'href="{CALC_PATH}"') < src.index("<TwinDashboardDemo />")


def test_the_link_appears_once_in_the_component():
    # One link, so the metric has exactly one cause. A second copy on the page
    # would make a rise in calculator visitors unattributable.
    assert read(LANDING).count(f'href="{CALC_PATH}"') == 1


def test_the_click_is_instrumented_with_a_location_of_its_own():
    hero = hero_slice()
    assert 'trackFunnel("cta_click", { location: "hero-calculator" })' in hero, (
        "the new CTA is not instrumented"
    )
    # Distinct from the signup button's location. If these ever collapse to the
    # same string the experiment silently stops being readable.
    assert 'location: "hero"' in hero
    assert "hero-calculator" != "hero"


def test_the_cta_can_be_driven_by_the_qa_lab():
    # A testid is what makes the link clickable from a script rather than by
    # eye, which is the difference between a checked change and a claimed one.
    hero = hero_slice()
    assert 'data-testid="link-hero-runway-calculator"' in hero
    assert 'data-testid="text-hero-calculator-prompt"' in hero


def test_the_input_submitted_half_fires_once_on_the_first_input():
    # calculator_used is the "someone actually used the tool" step. It fires
    # once per page load from the first input event, with the calculator name.
    src = read(CALCULATOR)
    assert 'useCalculatorUsedOnce("runway")' in src
    assert "onInput={onCalculatorInput}" in src


def test_the_hero_copy_was_not_rewritten():
    # Constraint from the card: do not touch the hero copy. The headline and
    # subtitle are byte-pinned so a later edit has to be deliberate.
    src = read(LANDING)
    assert '["The Flight Simulator", false],' in src
    assert '["for Founders", true],' in src
    assert (
        "Know your real runway, pressure-test every big decision before you commit, and get AI strategy\n"
        "          you can take to your board. Run your startup like a simulation."
    ) in src
    assert 'data-testid="button-hero-start-simulation"' in src


def test_the_new_line_claims_only_what_outreach_already_claims():
    # OUTREACH.md's approved claim, and the only one: public beta, free, the
    # calculator needs no login. No number, no price, no discount, no promise
    # this page cannot keep.
    text = visible_text(prompt_block())
    # Pin the extractor itself, not just its output. The original one-line
    # findall returned the link text and silently omitted this sentence, so the
    # checks below ran on half the line. If the pass ever goes blind again,
    # this fails first and says so. HAG-299 instance 3.
    assert "Just want your runway?" in text, f"the text pass cannot see the lead sentence: {text!r}"
    assert "needs no login" in text
    for banned in ("$", "%", "trial", "discount", "guarantee", "30-day", "free beta"):
        assert banned not in text, f"the new line makes an unapproved claim: {banned}"
    assert not any(ch.isdigit() for ch in text), f"the new line quotes a number: {text!r}"


def test_the_text_pass_reads_across_a_jsx_space_expression():
    # The extractor's own guard, on a block shaped like the one it has to read:
    # text, `{" "}`, a tag carrying an arrow-function prop, more text. Without
    # this, the pass could go blind to a sentence again and every assertion
    # built on it would keep passing on less text. Same shape as #86's
    # `assert.ok(routes.length > 100)`: the guard must fail if it goes vacuous.
    sample = """
      Just want your runway?{" "}
      <Link href="/x" onClick={() => trackFunnel("a", { b: "c" })}>
        The free runway calculator needs no login
      </Link>
    """
    text = visible_text(sample)
    assert "Just want your runway?" in text, text
    assert "needs no login" in text, text
    assert "trackFunnel" not in text, "an expression leaked into visible copy"
    assert "href" not in text, "an attribute leaked into visible copy"


def test_the_crawler_path_is_untouched():
    # The change is a prominence change, not a new route. The homepage body a
    # non-JS crawler reads must keep linking the calculator.
    src = read(PRERENDER)
    body = src[src.index("function buildLandingBodyContent") :]
    body = body[: body.index("function buildBlogListBodyContent")]
    assert f'href="{CALC_PATH}"' in body


def test_the_footer_link_is_still_there():
    # Added, not moved. If the footer link had been removed instead, a rise in
    # calculator visitors would measure the move, not the prominence.
    assert f'href: "{CALC_PATH}"' in read(MARKETING_LAYOUT)
