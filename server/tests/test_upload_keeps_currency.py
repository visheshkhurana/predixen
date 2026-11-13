"""An upload without a stated currency must not reset an INR company to USD."""

import pytest

from server.api.ingest import _detected_currency


@pytest.mark.parametrize("value,expected", [
    (None, None),
    ("", None),
    ("  inr ", "INR"),
    ("USD", "USD"),
    ("Rs.", None),
    ("XYZ", None),
    (42, None),
])
def test_detected_currency(value, expected):
    assert _detected_currency(value) == expected


def test_missing_currency_is_no_longer_defaulted_to_usd():
    src = open("server/api/ingest.py").read()
    assert "get('currency', 'USD')" not in src
