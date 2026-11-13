"""HAG-294: the floor's own visits are labelled, never dropped.

Why this file is Python as well as the `.test.ts` beside it. `pr-checks.yml`
names every TypeScript test file by hand as its own step, and that workflow is on
the hold list, so `server/tests/internal-traffic.test.ts` will not run in CI until
Vishesh adds a step for it. `pytest.ini` sets `testpaths = server/tests`, so this
file is collected automatically with no workflow change: it is the half of the
coverage that actually executes today.

The two files are not duplicates. The `.test.ts` is behavioural and covers the
classifier's decisions - above all that an ordinary browser is *not* labelled. This
file covers the wiring, which a unit test on a pure function cannot see:

  1. **the tag is unconditional.** `From search or AI (verified)` is only readable
     if every event carries the label, so the tag is applied at `dispatch()`, the
     single choke point, and the assertion is on the code that routes *around* it
     rather than on the tag itself. A caller who forgets to pass a property cannot
     produce an untagged event, because no caller passes it.
  2. **nothing is dropped.** God's instruction was explicit - "Two-number split,
     NOT a hard filter - a filter that drops a real founder is worse than the noise
     it removes." So the classifier module is asserted to have no route to the
     event queue at all, and the queue is asserted never to consult the verdict.
     A filter added later fails here rather than in a traffic number nobody
     re-reads for a week.
  3. **the PostHog key is untouched.** The card priced this change at 3 rather than
     1 "only because a change touching the PostHog key is on Vishesh's hold list",
     so the key is pinned: this PR must not be the thing that moved it.

The probe path is pinned as a literal because it is the specific URL
`founderconsole/scoreboard/latest.md` names as the floor's own 404 test. If the
constant drifts from that path the classifier keeps reporting "ok" while matching
nothing, which is precisely the failure mode this column already suffered from.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CLASSIFIER = REPO_ROOT / "client/src/lib/internal-traffic.ts"
POSTHOG = REPO_ROOT / "client/src/lib/posthog.ts"
QUEUE = REPO_ROOT / "client/src/lib/posthog-queue.ts"

# Named in `founderconsole/scoreboard/latest.md` note 3 as the floor's own 404 test.
PROBE_PREFIX = "/this-page-does-not-exist-"

# The token shipped in the bundle. Pinned only so this PR cannot be the change that
# moved it - the hold-list condition on HAG-294.
POSTHOG_KEY = "phc_C3jjovUPQChwDJoJdCp6E7adYRKBYSPETq5bNJw7pt6M"

EXPECTED_REASONS = {"flag", "webdriver", "internal-user-agent", "internal-probe-path"}


def block(src: str, marker: str) -> str:
    """The brace-balanced body of the function whose declaration contains `marker`.

    Asserting on a whole file cannot distinguish "the tag is applied here" from "the
    tag is applied here and bypassed three lines down", so the assertions read the
    one function they are about.
    """
    at = src.index(marker)
    start = src.index("{", at)
    depth, i = 0, start
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
        i += 1
    raise AssertionError(f"unbalanced braces after {marker!r}")


def test_the_ts_test_exists_but_is_not_wired_into_ci_yet():
    """Stated, not hidden: the executing half today is this file."""
    assert (REPO_ROOT / "server/tests/internal-traffic.test.ts").exists()

    workflow = REPO_ROOT / ".github/workflows/pr-checks.yml"
    if not workflow.exists():  # pragma: no cover - workflow is optional in a worktree
        return
    assert "internal-traffic.test.ts" not in workflow.read_text(), (
        "if the TS test is now named in pr-checks.yml, this Python half is no longer "
        "the only half that runs - update the module docstring"
    )


def test_every_event_is_tagged_at_the_single_choke_point():
    src = POSTHOG.read_text()
    dispatch = block(src, "function dispatch(")

    assert "tagInternalTraffic(call)" in dispatch, "dispatch does not tag the call"
    # Tagged on BOTH legs: the fast path and the queued path. Tagging only the
    # enqueue leg would leave every event after the SDK loads untagged, which is
    # every event in a normal session.
    assert "flushPostHogQueue(client, [tagged])" in dispatch
    assert "enqueue(tagged)" in dispatch


def test_the_tag_is_derived_from_the_environment_not_passed_in():
    """The label wins over a caller's own property of the same name."""
    src = POSTHOG.read_text()
    tagger = block(src, "function tagInternalTraffic(")

    assert "internalTrafficProperties()" in tagger
    # Spread last, in both branches, so a caller cannot overwrite the verdict.
    assert "{ ...call.properties, ...tag }" in tagger
    assert "{ ...call.traits, ...tag }" in tagger


def test_all_client_calls_go_through_the_queue():
    """`dispatch` is the choke point because nothing else can reach the SDK."""
    src = POSTHOG.read_text()
    direct = re.findall(r"\b(?:client|sdk)\.(?:capture|identify|reset|register)\b", src)
    assert not direct, f"the SDK is called outside the queue: {direct}"


def test_the_classifier_cannot_drop_an_event():
    """It labels; it has no path to the queue, so it cannot suppress anything."""
    src = CLASSIFIER.read_text()
    for forbidden in ("posthog", "flushPostHogQueue", "enqueue", "dispatch", "pending"):
        assert forbidden not in src, (
            f"{forbidden!r} appears in the classifier - the label must not be able to "
            "reach the event queue, or 'verified' quietly becomes a filter"
        )


def test_the_queue_never_consults_the_verdict():
    """The queue is downstream of the tag and must stay blind to it."""
    src = QUEUE.read_text()
    assert "fc_internal" not in src


def test_both_keys_are_always_present():
    """`fc_internal = false` must be testable, so 'absent' is not signalling 'verified'."""
    src = CLASSIFIER.read_text()
    props = block(src, "export function internalTrafficProperties(")
    assert "fc_internal:" in props
    assert "fc_internal_reason:" in props


def test_the_reason_set_is_exactly_the_four_signals():
    src = CLASSIFIER.read_text()
    union = src[src.index("export type InternalReason") :]
    union = union[: union.index(";")]
    assert set(re.findall(r'"([a-z-]+)"', union)) == EXPECTED_REASONS


def test_the_probe_prefix_is_the_path_the_scoreboard_names():
    src = CLASSIFIER.read_text()
    assert f'INTERNAL_PROBE_PREFIX = "{PROBE_PREFIX}"' in src


def test_the_posthog_key_is_unchanged():
    """The hold-list condition on this card, asserted rather than promised."""
    assert f"'{POSTHOG_KEY}'" in POSTHOG.read_text() or f'"{POSTHOG_KEY}"' in POSTHOG.read_text()


def test_a_plain_browser_is_not_labelled():
    """The one behaviour worth duplicating here: a false label is the expensive bug.

    Duplicated deliberately. This is the assertion that protects a real founder's
    visit from being counted as ours, and it is the only one in the `.test.ts` whose
    failure would silently corrupt the number rather than crash.
    """
    src = CLASSIFIER.read_text()
    classify = block(src, "export function classifyInternalTraffic(")

    fallthrough = classify.rstrip().rsplit("return", 1)[-1]
    assert fallthrough.strip().startswith("{ internal: false"), (
        "the classifier's last return no longer falls through to 'not internal' - "
        f"it now returns {fallthrough.strip()[:60]}"
    )
