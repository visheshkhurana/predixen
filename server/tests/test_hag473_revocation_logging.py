"""HAG-473: a second revocation failure of the same class must not be silent.

``_guarded_revocation`` swallows SQLAlchemy errors so a missing revocation table
degrades to "revocation off" instead of 500ing every authenticated request. The
warning, though, was emitted once per exception class per process, so the second
and every later failure of that class produced no output at all - a genuinely
different ``ProgrammingError`` looked exactly like the intended missing-table
degradation.

These tests drive the guard directly, twice, and assert the second occurrence is
observable: in the suppressed counter and in a second warning.
"""
import contextlib
import logging

import pytest
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, SQLAlchemyError

from server.core import security


class _FakeDb:
    """Just enough Session for the guard: flush, then a savepoint that lets the
    exception through (the real begin_nested() does the same on failure)."""

    def flush(self):
        pass

    def begin_nested(self):
        return contextlib.nullcontext()


def _programming_error() -> ProgrammingError:
    return ProgrammingError("SELECT 1", None, Exception("column does not exist"))


@pytest.fixture(autouse=True)
def _clean_state():
    security._revocation_warned.clear()
    security._revocation_suppressed.clear()
    yield
    security._revocation_warned.clear()
    security._revocation_suppressed.clear()


def _raising(exc):
    def fn():
        raise exc
    return fn


def test_second_failure_of_the_same_class_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger=security.__name__):
        assert security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default="off") == "off"
        first = len([r for r in caplog.records if "revocation" in r.message.lower()])

        assert security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default="off") == "off"
        second = len([r for r in caplog.records if "revocation" in r.message.lower()])

    assert first == 1, "the first failure should warn once"
    assert second == 2, (
        "the second failure of the same class must be observable, not silent; "
        f"records were {[r.message for r in caplog.records]}"
    )


def test_suppressed_counter_records_every_occurrence():
    for _ in range(3):
        security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default=None)

    assert security.revocation_suppressed_counts() == {"ProgrammingError": 3}


def test_distinct_classes_are_counted_separately():
    security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default=None)
    security._guarded_revocation(_FakeDb(), _raising(InvalidRequestError("bad bind")), default=None)
    security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default=None)

    assert security.revocation_suppressed_counts() == {
        "ProgrammingError": 2,
        "InvalidRequestError": 1,
    }


def test_the_guard_still_degrades_instead_of_raising():
    """The availability trade is the whole reason the catch is broad; a genuine
    ProgrammingError must not reach the caller."""
    assert security._guarded_revocation(
        _FakeDb(), _raising(_programming_error()), default="off"
    ) == "off"


def test_a_successful_call_is_not_counted():
    security._guarded_revocation(_FakeDb(), lambda: "ok", default=None)
    assert security.revocation_suppressed_counts() == {}


def test_the_counter_is_a_copy():
    security._guarded_revocation(_FakeDb(), _raising(_programming_error()), default=None)
    counts = security.revocation_suppressed_counts()
    counts["ProgrammingError"] = 999
    assert security.revocation_suppressed_counts() == {"ProgrammingError": 1}


def test_non_sqlalchemy_errors_are_not_swallowed():
    with pytest.raises(ValueError):
        security._guarded_revocation(_FakeDb(), _raising(ValueError("bug in the query builder")), default=None)
