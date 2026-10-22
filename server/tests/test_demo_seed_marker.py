"""The demo seed may only delete and rename companies it created itself.

The demo account is shared and its password is public, so the seed runs for any
visitor who signs in. HAG-651 is the consequence: a second company a visitor
created under the demo user was deleted by the next login's duplicate cleanup,
and the rename that follows applied to whichever row ``.first()`` returned.

The fix is provenance: the seed writes ``metadata_json["seed_created"] = True``
on the rows it creates, and only those rows can be deleted or renamed.

The marker has to exist before it is written, so a first run on an unmarked
account guesses -- and records the guess under ``seed_guessed`` so the run that
later acts on it can say so. The unit tests below take plain ``id`` /
``metadata_json`` with the one write injected; the last four run the seed itself
against an in-memory SQLite, because a source-text check passes on the same
defect under a different name. The last of those asserts, per company-scoped
table, that a row the bootstrap only GUESSED was the seed's receives no writes at
all -- the fields a name-only test checks are the smallest part of what lands.
"""

import logging
from types import SimpleNamespace

import pytest

from server.seed.demo_companies import (
    SEED_GUESSED,
    SEED_MARKER,
    ensure_seed_marked,
    is_seed_created,
    is_seed_guess,
    needs_bootstrap,
    pick_primary_id,
    rows_to_purge,
)


def company(cid, metadata=None):
    return SimpleNamespace(id=cid, metadata_json=metadata)


class SaveSpy:
    """Stands in for save_metadata_value so a test can assert the write exactly."""

    def __init__(self):
        self.calls = []

    def __call__(self, db, row, path, value, **kwargs):
        self.calls.append((row.id, path, value, kwargs.get("commit", True)))


class FakeSession:
    """Counts commits, so "the two marker keys commit together" is measurable."""

    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


# --- the predicate -----------------------------------------------------------


def test_only_a_literal_true_counts_as_seed_created():
    assert is_seed_created({SEED_MARKER: True}) is True
    assert is_seed_created({SEED_MARKER: False}) is False
    assert is_seed_created({SEED_MARKER: "true"}) is False
    assert is_seed_created({SEED_MARKER: 1}) is False
    assert is_seed_created({}) is False
    assert is_seed_created(None) is False


def test_is_sample_is_not_provenance():
    # is_sample is visitor-triggerable -- the sample-data route sets it on the
    # caller's own company -- so treating it as provenance would authorise
    # deleting the row it appears to protect.
    assert is_seed_created({"is_sample": True}) is False


# --- which row is the primary, and which rows may be deleted -----------------


def test_primary_is_the_marked_row_even_when_a_visitor_row_holds_the_lower_id():
    rows = [
        company(1, {"is_sample": True}),
        company(2, {SEED_MARKER: True}),
        company(3, {SEED_MARKER: True}),
    ]
    assert pick_primary_id(rows) == 2
    assert needs_bootstrap(rows) is False


def test_only_marked_rows_after_the_primary_are_purged():
    rows = [
        company(1, {}),
        company(2, {SEED_MARKER: True}),
        company(3, {"is_sample": True}),
        company(4, {SEED_MARKER: True}),
        company(5, None),
    ]
    assert [c.id for c in rows_to_purge(rows, 2)] == [4]


def test_nothing_is_purged_when_nothing_is_marked():
    # The delete fails closed: an unmarked duplicate seed row is left in place
    # rather than risking a visitor's company.
    rows = [company(1), company(2), company(3)]
    assert needs_bootstrap(rows) is True
    assert rows_to_purge(rows, None) == []
    assert rows_to_purge(rows, 1) == []


# --- bootstrap: the one-time guess, and the warning that makes it visible ----


def test_a_marked_account_writes_nothing():
    rows = [company(1, {SEED_MARKER: True}), company(2, {})]
    spy = SaveSpy()
    session = FakeSession()
    assert ensure_seed_marked(session, rows, save=spy) == 1
    assert spy.calls == []
    assert session.commits == 0, "a marked account must not open a transaction"


def test_bootstrap_marks_the_lowest_id_once_and_warns_with_id_and_row_count(caplog):
    rows = [company(7, None), company(8, {})]
    spy = SaveSpy()
    session = FakeSession()
    with caplog.at_level(logging.WARNING, logger="server.seed.demo_companies"):
        assert ensure_seed_marked(session, rows, save=spy) == 7

    # Two writes, same row: the marker, and the key that says it was a guess.
    # Neither commits on its own and the session commits exactly once after
    # both, which is what makes a death between them leave neither key.
    # Kills the mutation `delete save(db, primary, SEED_GUESSED, True, commit=False)`,
    # which leaves every provenance test green and the rename-refusal alarm silent.
    assert spy.calls == [
        (7, SEED_MARKER, True, False),
        (7, SEED_GUESSED, True, False),
    ]
    assert session.commits == 1, (
        "the two marker keys must land in ONE commit: committing the first "
        "separately leaves a row that reads as provenance with the guess missing"
    )
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]
    message = warnings[0].getMessage()
    assert SEED_MARKER in message
    assert "7" in message, message
    assert "2 row(s)" in message, message


def test_an_account_with_no_companies_writes_nothing():
    spy = SaveSpy()
    session = FakeSession()
    assert ensure_seed_marked(session, [], save=spy) is None
    assert spy.calls == []
    assert session.commits == 0


def test_a_blob_write_that_drops_the_marker_reboots_and_warns(caplog):
    # A whole-blob writer elsewhere replaces metadata_json and takes the marker
    # with it. That fails closed for deletion -- nothing is purged -- but it
    # silently stops the dedupe and the reset, so the re-bootstrap must be loud.
    rows = [company(1, {"theme": "dark"}), company(2, {"theme": "light"})]
    assert rows_to_purge(rows, None) == []

    spy = SaveSpy()
    session = FakeSession()
    with caplog.at_level(logging.WARNING, logger="server.seed.demo_companies"):
        assert ensure_seed_marked(session, rows, save=spy) == 1

    assert spy.calls == [
        (1, SEED_MARKER, True, False),
        (1, SEED_GUESSED, True, False),
    ]
    assert session.commits == 1
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]
    assert SEED_MARKER in warnings[0].getMessage()



# --- the seed actually runs ----------------------------------------------------
#
# Replaces three source-text checks. Those fail on a verbatim revert and pass on
# the same defect under a different name -- measured: restoring the old delete
# loop two lines below the pinned one left all 12 tests green. These run the seed
# against real rows instead, so what is asserted is the outcome, not the spelling.
#
# Both orderings are required: each ordering alone catches one of the two
# mutations and misses the other.

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import ARRAY as _ARRAY
from sqlalchemy.dialects.postgresql import JSONB as _JSONB
from sqlalchemy.dialects.postgresql import UUID as _UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(_JSONB, "sqlite")
def _jsonb_as_json(_type, _compiler, **_kw):
    return "JSON"


@compiles(_ARRAY, "sqlite")
def _array_as_json(_type, _compiler, **_kw):
    return "JSON"


@compiles(_UUID, "sqlite")
def _uuid_as_char(_type, _compiler, **_kw):
    return "CHAR(36)"


def _seeded_session(visitor_first: bool, *, seed_marked: bool = True):
    """In-memory SQLite with the demo account and one visitor company.

    ``conftest.py`` is where the JSONB shim belongs; it is inline here only so
    this file can be read alone.
    """
    import server.models  # noqa: F401  registers every table on Base.metadata
    from server.core.db import Base
    from server.models.company import Company
    from server.models.user import User

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    demo = User(email="demo@founderconsole.ai", password_hash="x", role="owner")
    db.add(demo)
    db.commit()
    visitor = Company(user_id=demo.id, name="A Visitor's Co", metadata_json={"is_sample": True})
    # The steady state: the seed has run before, so its own row carries the
    # marker. The first-run guess is a separate question and has its own test.
    seed_row = Company(
        user_id=demo.id,
        name="TechFlow Analytics",
        metadata_json={SEED_MARKER: True} if seed_marked else {},
    )
    for row in ([visitor, seed_row] if visitor_first else [seed_row, visitor]):
        db.add(row)
        db.commit()
    return db, Company, visitor.id, demo.id


@pytest.mark.parametrize("visitor_first", [True, False])
def test_the_seed_never_deletes_or_renames_a_company_it_did_not_create(visitor_first):
    from server.seed.seed_demo import seed_demo_data

    db, Company, visitor_id, _demo_id = _seeded_session(visitor_first)

    seed_demo_data(db)
    db.expire_all()

    still = db.query(Company).filter(Company.id == visitor_id).first()
    assert still is not None, "the seed deleted a company the visitor created"
    assert still.name == "A Visitor's Co", (
        f"the seed renamed a visitor's company to {still.name!r}"
    )


def test_the_run_that_would_rename_a_visitor_row_refuses_and_warns(caplog):
    """An alarm is worth only what it says on the run that does the damage.

    Run 1 dies after the marker commit -- a real shape: the marker is committed
    first and ~30 content commits follow it. The marker is now on the guessed
    row, so run 2 skips the bootstrap and goes straight to the rename. If only
    the bootstrap warns, the warning is spent on the run that produced no
    outcome and the run that would rename a visitor's company says nothing.

    The run must REFUSE and must say which row and how big the account is. The
    assertion is on the sentence, not on ``caplog.records``: a level is not a
    filter, so the bootstrap's warning reaches this logger's records too, and a
    mutation that writes no marker at all left the old ``assert caplog.records``
    green while the sentence this test exists for never appeared.

    Kills four mutations, and nothing else in the file kills them:
      * drop the ``is_seed_guess`` gate above the industry write, so the
        visitor's row is renamed -- silent damage, and ``after`` catches it;
      * refuse but log nothing, or log a message that does not name the row;
      * drop the row count from the message;
      * stop recording ``seed_guessed`` at bootstrap, so no run can tell a guess
        from provenance and the rename goes ahead silently.
    """
    import server.seed.seed_demo as seed_demo
    from server.seed.demo_companies import ensure_seed_marked as real_ensure

    # The first-run shape: nothing is marked yet, so the seed guesses. Here the
    # guess lands on the visitor's row, which is the moment the alarm exists for.
    db, Company, visitor_id, demo_id = _seeded_session(visitor_first=True, seed_marked=False)

    def marker_then_crash(session, rows, **kwargs):
        real_ensure(session, rows, **kwargs)  # commits the marker, as production does
        raise RuntimeError("injected: the run died after the marker commit")

    seed_demo.ensure_seed_marked = marker_then_crash
    try:
        with pytest.raises(RuntimeError):
            seed_demo.seed_demo_data(db)
    finally:
        seed_demo.ensure_seed_marked = real_ensure
    db.rollback()

    db.expire_all()
    before = db.query(Company).filter(Company.id == visitor_id).first().name
    assert before == "A Visitor's Co", f"run 1 was supposed to change nothing, got {before!r}"
    assert is_seed_guess(
        db.query(Company).filter(Company.id == visitor_id).first().metadata_json
    ), "fixture wrong: run 1 was supposed to mark the visitor's row as the guess"

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="server.seed.seed_demo"):
        seed_demo.seed_demo_data(db)

    db.expire_all()
    after = db.query(Company).filter(Company.id == visitor_id).first().name
    assert after == "A Visitor's Co", (
        f"the run renamed a row the bootstrap only GUESSED was the seed's to {after!r}: "
        "the refusal exists because the rename cannot be undone afterwards"
    )

    refusals = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and "REFUSING to seed company id=" in r.getMessage()
    ]
    assert len(refusals) == 1, (
        "the run that would have renamed a visitor's company logged no refusal at "
        "WARNING, or logged more than one: "
        + repr([r.getMessage() for r in caplog.records])
    )
    message = refusals[0].getMessage()
    assert f"id={visitor_id}" in message, (
        f"the alarm does not name the row it refused to rename (id={visitor_id}): {message}"
    )
    assert "2 row(s)" in message, (
        "the alarm does not say how big the demo account is, so an operator cannot "
        f"tell a two-row mistake from a ten-row one: {message}"
    )


def test_the_run_that_renames_the_seeds_own_row_stays_silent(caplog):
    """The control for the alarm above.

    A row the seed created itself carries the marker and not the guess, so the
    rename must still happen and must not warn. Without this, "warn on every
    rename" passes, and an alarm that fires on the healthy path is one an
    operator learns to scroll past.

    Kills the mutation: drop the ``is_seed_guess`` guard so the WARNING fires on
    whichever row is renamed.
    """
    import server.seed.seed_demo as seed_demo

    db, Company, _visitor_id, _demo_id = _seeded_session(visitor_first=True)
    seed_row = db.query(Company).filter(Company.name == "TechFlow Analytics").one()
    assert not is_seed_guess(seed_row.metadata_json), "fixture wrong: the seed's own row"
    seed_row.name = "Renamed By Hand"
    db.commit()

    with caplog.at_level(logging.WARNING, logger="server.seed.seed_demo"):
        seed_demo.seed_demo_data(db)

    db.expire_all()
    assert db.query(Company).filter(Company.id == seed_row.id).one().name == (
        "TechFlow Analytics"
    ), "the seed stopped healing its own row"
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING], (
        "the seed warned while renaming a row it created itself: `seed_guessed` is "
        "being read as `any marked row`. "
        + repr([r.getMessage() for r in caplog.records])
    )


# --- forward compatibility: the two marker keys are one write ----------------
#


def test_a_death_between_the_two_marker_keys_leaves_neither():
    """The marker and the guess are committed together, or not at all.

    Measured on the reviewed revision, which committed them separately: dying
    between the writes left the row carrying ``{'is_sample': True,
    'seed_created': True}`` -- provenance with the guess missing -- and an
    ordinary second run renamed that visitor's company with nothing at WARNING
    from ``seed_demo``. That is this card's original harm on a one-statement
    window, so the window is closed rather than alarmed around.

    Kills the mutation: restore ``commit=True`` on the first save (or add a
    ``db.commit()`` between the two), which is exactly the reviewed shape. This
    is the only test that goes red for it -- the write-order tests assert the
    kwargs and would still see two writes.
    """
    from server.core.company_metadata import save_metadata_value

    db, Company, visitor_id, _demo_id = _seeded_session(visitor_first=True, seed_marked=False)
    row = db.query(Company).filter(Company.id == visitor_id).one()

    def dying_save(session, target, path, value, **kwargs):
        if path == SEED_GUESSED:
            raise RuntimeError("injected: the process died before the second key")
        save_metadata_value(session, target, path, value, **kwargs)

    with pytest.raises(RuntimeError):
        ensure_seed_marked(db, [row], save=dying_save)
    db.rollback()
    db.expire_all()

    after = db.query(Company).filter(Company.id == visitor_id).one()
    assert after.metadata_json == {"is_sample": True}, (
        "a death between the two marker writes left the row looking like "
        f"provenance: {after.metadata_json!r}"
    )


# --- the creation path is marked too -----------------------------------------


def _session_with_no_companies(*, demo_user_exists: bool):
    """In-memory SQLite, the demo account, and no company under it."""
    import server.models  # noqa: F401  registers every table on Base.metadata
    from server.core.db import Base
    from server.models.user import User

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    if demo_user_exists:
        db.add(User(email="demo@founderconsole.ai", password_hash="x", role="owner"))
        db.commit()
    return db


@pytest.mark.parametrize("demo_user_exists", [True, False])
def test_the_company_the_seed_creates_carries_the_marker(demo_user_exists):
    """Both creation branches mark the row they create.

    Sentinel's NOTE: removing BOTH ``save_metadata_value(..., SEED_MARKER, True)``
    calls on the creation path left every test green, so a third of this feature
    was held by nothing. A seed that creates its company unmarked is the state
    this card exists to end: the next run finds nothing marked, guesses, and the
    guess is what renames a visitor's company.

    Kills the mutation: delete either creation-path marker write. The ``True``
    and ``False`` parameters are the two branches -- an existing demo user with
    no company, and no demo user at all -- and each parameter kills the one in
    its own branch, so dropping both turns both red.
    """
    import server.seed.seed_demo as seed_demo
    from server.models.company import Company

    db = _session_with_no_companies(demo_user_exists=demo_user_exists)
    seed_demo.seed_demo_data(db)
    db.expire_all()

    created = db.query(Company).filter(Company.name == "TechFlow Analytics").one()
    assert is_seed_created(created.metadata_json), (
        "the seed created a company and did not mark it, so the next run guesses "
        f"and can rename a visitor's row: {created.metadata_json!r}"
    )
    assert not is_seed_guess(created.metadata_json), (
        "a company the seed created itself is provenance, not a guess"
    )


# --- the gate: a guessed row receives no writes at all ----------------------


def _row_counts(db, company_id):
    """Rows per company-scoped table, keyed by table name.

    Every table with a ``company_id`` column is enumerated from ``Base.metadata``
    rather than listed by hand, and counted per table rather than in total: a
    single total hides the trade a partial fix makes -- eighteen families instead
    of twenty-four rows is still "some number went up". A table added next month
    is covered without editing this list.
    """
    import server.models  # noqa: F401  registers every table on Base.metadata
    from sqlalchemy import func, select

    from server.core.db import Base

    counts = {}
    for table in Base.metadata.sorted_tables:
        if "company_id" not in table.columns:
            continue
        counts[table.name] = db.execute(
            select(func.count()).select_from(table).where(table.c.company_id == company_id)
        ).scalar()
    return counts


def test_a_guessed_row_receives_no_writes_at_all():
    """The refusal is an early return, so NOTHING lands on the guessed row.

    Rev 3 guarded only the rename: the three fields were protected and the other
    ~30 writers below the guard still ran. In this fixture the guess lands on the
    visitor's row, so rev 3 put the financial re-create, the ``_seed_*`` families
    and the CONNECTED connector rows onto a company the visitor owns -- while the
    test that asserted the name was unchanged stayed green.

    Asserted per table, across every table carrying ``company_id``, plus the
    three fields, plus the user count (``seed_team_members`` sits below the gate
    too). The before/after diff is what fails, so a new writer added below the
    gate is caught without editing this test.

    Kills the mutation: move the gate back to a guard around the three renamed
    fields (rev 3's shape), or move any one of the writers above the early
    return. Both leave the row's name intact and still red this test.
    """
    import server.seed.seed_demo as seed_demo
    from server.models.user import User

    db, Company, visitor_id, _demo_id = _seeded_session(visitor_first=True, seed_marked=False)

    def snapshot():
        db.expire_all()
        row = db.query(Company).filter(Company.id == visitor_id).one()
        return {
            "name": row.name,
            "industry": row.industry,
            "stage": row.stage,
            "metadata_json": dict(row.metadata_json or {}),
            "users": db.query(User).count(),
            "tables": _row_counts(db, visitor_id),
        }

    before = snapshot()
    assert is_seed_guess(
        db.query(Company).filter(Company.id == visitor_id).one().metadata_json
    ) is False, "fixture wrong: the guess is recorded by the run under test, not before it"
    assert not any(before["tables"].values()), (
        "fixture wrong: the visitor row starts with rows in "
        + repr({k: v for k, v in before["tables"].items() if v})
    )

    seed_demo.seed_demo_data(db)

    after = snapshot()

    # The rows come first: it is the larger damage and the one rev 3 shipped, so
    # a red here names the table rather than one of the three protected fields.
    grew = {
        name: (before["tables"][name], after["tables"][name])
        for name in sorted(before["tables"])
        if after["tables"][name] != before["tables"].get(name, 0)
    }
    assert not grew, (
        "the seed wrote rows belonging to a company it only GUESSED was its own. "
        f"{len(grew)} of {len(before['tables'])} company-scoped tables changed "
        f"(before, after): {grew}. The refusal must return before every writer, "
        "not guard a few fields."
    )

    # The three fields rev 3 already protected -- restated so a red above is not
    # misread as a name-only regression.
    assert (after["name"], after["industry"], after["stage"]) == (
        before["name"],
        before["industry"],
        before["stage"],
    ), (
        "the seed wrote a field on a row it only GUESSED was its own: "
        f"{before['name']!r}/{before['industry']!r}/{before['stage']!r} -> "
        f"{after['name']!r}/{after['industry']!r}/{after['stage']!r}"
    )

    assert after["users"] == before["users"], (
        f"the seed created {after['users'] - before['users']} user row(s) for a "
        "guessed company: seed_team_members ran below the gate"
    )

    # The one thing the run may touch: recording where it refused, so the next
    # run can say so. Anything else in metadata_json is a write it must not make.
    assert sorted(after["metadata_json"]) == sorted(
        ["is_sample", SEED_MARKER, SEED_GUESSED]
    ), (
        "the refusing run wrote metadata keys beyond the guess record: "
        f"before {sorted(before['metadata_json'])}, after {sorted(after['metadata_json'])}"
    )
    assert after["metadata_json"][SEED_GUESSED] is True, (
        "the guess was not recorded, so the next run cannot tell a guess from "
        f"provenance: {after['metadata_json']!r}"
    )
