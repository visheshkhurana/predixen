"""HAG-274. `RestAPIConnector.authenticate` said yes to clients that cannot authenticate.

From Sentinel's #90 review (`hive/reports/sentinel-review-pr90.md`). Two of the three
ways it returned `True` are avoidable, and they are the two most common shapes of REST
authentication failure:

(a) **A 3xx redirect returned `True`.** `httpx>=0.28.1` is pinned and
    `httpx.AsyncClient()` defaults to `follow_redirects=False`, so a `302 -> /login`
    comes back AS the response, and the check was `status_code < 400`. An unauthenticated
    call against a protected API -- which answers a redirect, not a 401 -- was recorded as
    a successful authentication. The finding survives `follow_redirects=True`: it would
    follow to the login page, get a 200, and still say yes.

(b) **A credential-less request could return `True`.** Both builders guard with
    `if api_key and ...`, so with no key at all they silently build an *unauthenticated*
    request despite `REQUIRED_CREDENTIALS = ["api_key"]`. Pointed at a public endpoint
    that is a 200 and a `True`.

(c) Nothing ties the 200 to the credential. That is inherent to a generic REST connector
    and is not asserted here.

The fix mirrors `google_sheets.authenticate`, which the same review found tight: check the
credential is present *before* the call, and require exactly `== 200`.

`authenticate()` is not an access-control boundary -- no authorization decision reads it.
A false `True` misleads the person who configured the connector: told it works, finds out
at `fetch_data`. A correctness defect with a bad error surface, not a leak.

Run: /Users/visheshkhurana/predixen/.venv/bin/python -m pytest \
        server/tests/test_rest_api_authenticate.py -o addopts="" -p no:cacheprovider -q
"""

import asyncio
from typing import Any, Dict
from unittest.mock import patch

from server.connectors.base import ConnectorConfig
from server.connectors.rest_api import RestAPIConnector


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class FakeClient:
    """Stands in for `httpx.AsyncClient`, recording what was asked of it."""

    calls: list = []

    def __init__(self, status_code: int = 200, **kwargs: Any):
        self.status_code = status_code
        self.kwargs = kwargs

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def request(self, *args: Any, **kwargs: Any) -> FakeResponse:
        FakeClient.calls.append((args, kwargs))
        return FakeResponse(self.status_code)

    async def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        return await self.request(*args, **kwargs)


def connector(credentials: Dict[str, Any] | None = None) -> RestAPIConnector:
    config = ConnectorConfig(
        provider_id="rest_api",
        company_id=1,
        credentials=credentials if credentials is not None else {"api_key": "secret-key"},
        settings={"endpoint_url": "https://api.example.com/reports"},
    )
    return RestAPIConnector(config)


def authenticates(status_code: int, credentials: Dict[str, Any] | None = None) -> bool:
    FakeClient.calls = []
    with patch("httpx.AsyncClient", lambda **kw: FakeClient(status_code, **kw)):
        return asyncio.run(connector(credentials).authenticate())


def test_a_redirect_is_not_a_successful_authentication():
    """The defect. `302 -> /login` is how a protected API refuses an unauthenticated call."""
    assert authenticates(302) is False


def test_every_3xx_is_refused():
    """Pinning the class of answer, not just the one status code."""
    for status_code in (301, 302, 303, 307, 308):
        assert authenticates(status_code) is False, f"HTTP {status_code} was accepted"


def test_a_missing_api_key_is_refused_before_any_request():
    """`REQUIRED_CREDENTIALS = ["api_key"]` means a keyless instance cannot authenticate."""
    assert authenticates(200, credentials={}) is False
    assert FakeClient.calls == [], (
        "a request was sent without the credential this connector requires"
    )


def test_a_white_space_api_key_is_not_a_key():
    """`api_key` present but empty builds the same unauthenticated request."""
    assert authenticates(200, credentials={"api_key": ""}) is False
    assert FakeClient.calls == []


def test_a_real_200_still_authenticates():
    """The case that must keep working: a key, and a 200 from the endpoint."""
    connection = connector()
    FakeClient.calls = []
    with patch("httpx.AsyncClient", lambda **kw: FakeClient(200, **kw)):
        result = asyncio.run(connection.authenticate())

    assert result is True
    assert connection._authenticated is True
    assert len(FakeClient.calls) == 1


def test_the_key_is_still_sent_when_it_is_present():
    """The refusal above must come from the presence check, not from dropping the header."""
    connection = connector({"api_key": "secret-key"})
    FakeClient.calls = []
    with patch("httpx.AsyncClient", lambda **kw: FakeClient(200, **kw)):
        asyncio.run(connection.authenticate())

    _, kwargs = FakeClient.calls[0]
    assert kwargs["headers"].get("Authorization") == "Bearer secret-key"


def test_a_401_is_still_refused():
    """Unchanged behaviour, kept so the tightening cannot loosen it."""
    assert authenticates(401) is False


def test_a_500_is_still_refused():
    assert authenticates(500) is False


def _test_connection(status_code: int, credentials: Dict[str, Any] | None = None) -> bool:
    FakeClient.calls = []
    with patch("httpx.AsyncClient", lambda **kw: FakeClient(status_code, **kw)):
        return asyncio.run(connector(credentials).test_connection())


def test_connection_refuses_redirects():
    """test_connection used `status < 400`, so 301/302 counted as a live API."""
    for status_code in (301, 302, 303, 307, 308):
        assert _test_connection(status_code) is False, f"HTTP {status_code} was accepted"

    # The client must not follow the redirect onto a 200 login page.
    seen: dict = {}

    class RecordingClient(FakeClient):
        def __init__(self, status_code: int = 302, **kwargs: Any):
            super().__init__(status_code, **kwargs)
            seen.update(kwargs)

    with patch("httpx.AsyncClient", lambda **kw: RecordingClient(302, **kw)):
        assert asyncio.run(connector().test_connection()) is False
    assert seen.get("follow_redirects") is False


def test_connection_accepts_2xx_and_refuses_the_rest():
    assert _test_connection(200) is True
    assert _test_connection(201) is True
    assert _test_connection(299) is True
    # The old `< 400` check accepted these.
    assert _test_connection(300) is False
    assert _test_connection(399) is False
    assert _test_connection(401) is False
    assert _test_connection(500) is False
