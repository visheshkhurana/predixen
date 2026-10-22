"""The auth bucket must be the caller, and only the caller.

HAG-482 was measured on production: 33 sequential POSTs to /auth/login, 33 x 200,
zero 429, while the response headers said limit 10/min. The key was the *last*
X-Forwarded-For entry, which behind the Railway edge is an upstream hop and not
the visitor, so requests could be spread across buckets. The effective limit
became "10/min multiplied by the number of upstream identities".

The resolution rule is now: X-Real-IP when the TCP peer is loopback (that is the
Express proxy, and the edge wrote that header), otherwise the X-Forwarded-For
entry in front of exactly TRUSTED_PROXY_HOPS trusted hops. This file changes no
production code; it holds that rule in place, because nothing did before, and the
regression was live in production for as long as it took someone to measure it.

The fake request carries `starlette.datastructures.Headers`, not a dict,
because that is what production hands the middleware: a case-insensitive
mapping. A dict cannot model one, so it was never a faithful stand-in for the
thing under test. It is not, however, a double that hides this revert: measured
with a dict, the historical title-case lookup misses, the code falls through to
the socket address, and every caller lands in one shared bucket, which four of
these tests catch. The swap rests on fidelity to production, not on a green row.

Every drive test runs twice — once with X-Real-IP and once without — because the
two take different branches in client_ip, and a limit that holds in one shape
while fragmenting in the other is still the production bug.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from starlette.datastructures import Headers

from server.middleware.rate_limiter import (
    TRUSTED_PROXY_HOPS,
    RateLimiterMiddleware,
    client_ip,
)

CLIENT = "203.0.113.7"
OTHER = "198.51.100.9"
EDGE = "152.233.10.4"
LOOPBACK = "127.0.0.1"

# The two header shapes the edge can produce. Express dials FastAPI over
# loopback in both; Railway writes X-Real-IP when it has one.
SHAPES = ("with-x-real-ip", "chain-only")


def _headers(shape: str, client: str, xff=None):
    xff = f"{client}, {EDGE}" if xff is None else xff
    if shape == "with-x-real-ip":
        return {"peer": LOOPBACK, "real_ip": client, "xff": xff}
    return {"peer": LOOPBACK, "real_ip": None, "xff": xff}


def _request(path: str, *, peer: str, real_ip=None, xff=None, method="POST"):
    headers = {}
    if real_ip is not None:
        headers["x-real-ip"] = real_ip
    if xff is not None:
        headers["x-forwarded-for"] = xff
    return type(
        "R",
        (),
        {
            "url": type("U", (), {"path": path})(),
            "method": method,
            # Starlette Headers, not a plain dict: production hands the
            # middleware a case-insensitive mapping and a dict is not one, so
            # the double was never faithful whether or not it hid this bug.
            # Measured: with a dict the historical revert still fails four of
            # these tests (the title-case lookup misses, the code falls through
            # to the socket address, and every caller shares that bucket).
            # See HAG-482 review, HIGH.
            "headers": Headers(headers),
            "client": type("C", (), {"host": peer})(),
            "scope": {"extensions": {"peer_host": peer}},
        },
    )()


class _Row:
    def __init__(self, count, start):
        self._values = (count, start)

    def __getitem__(self, i):
        return self._values[i]


class _WindowStore:
    """The fixed-window rule from _check_rate_limit's SQL, in memory.

    Keys and counts only: these tests are about which bucket a request lands in,
    not about the window arithmetic, which the SQL already owns.
    """

    def __init__(self):
        self.rows = {}

    def connect(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, _sql, params):
        key = params["key"]
        endpoint = params["endpoint"]
        now = params["now"]
        cutoff = params["cutoff"]
        count, start = self.rows.get((key, endpoint), (0, None))
        if start is None or start < cutoff:
            count, start = 1, now
        else:
            count += 1
        self.rows[(key, endpoint)] = (count, start)
        return type("R", (), {"fetchone": lambda _s: _Row(count, start)})()

    def commit(self):
        return None


async def _ok(_request):
    return type("Resp", (), {"status_code": 200, "headers": {}})()


def _post(middleware, **kwargs):
    return asyncio.run(middleware.dispatch(_request("/auth/login", **kwargs), _ok))


def _drive(middleware, times: int, **kwargs):
    return [_post(middleware, **kwargs).status_code for _ in range(times)]


def _middleware(store):
    middleware = RateLimiterMiddleware(MagicMock())
    return middleware, patch("server.middleware.rate_limiter._get_engine", return_value=store)


# --- the rule itself --------------------------------------------------------


def test_the_identifier_is_the_caller_not_the_last_forwarded_hop():
    assert client_ip({"x-real-ip": CLIENT, "x-forwarded-for": f"{CLIENT}, {EDGE}"}, LOOPBACK) == CLIENT
    # No X-Real-IP: the client is the entry two hops in, not the last one.
    assert client_ip({"x-forwarded-for": f"{CLIENT}, {EDGE}"}, LOOPBACK) == CLIENT
    # Direct to FastAPI: X-Real-IP is a header the caller wrote, so it is ignored.
    assert client_ip({"x-real-ip": "1.2.3.4", "x-forwarded-for": f"{CLIENT}, {EDGE}"}, "10.1.2.3") == CLIENT
    # No headers and no peer: there is nothing to resolve, so the rule returns
    # the empty string. That is the answer this line pins; the empty key is one
    # shared bucket either way, which is why relabelling it "unknown" is not
    # tested here.
    assert client_ip({}, "") == ""


def test_a_dual_stack_peer_is_still_the_express_proxy():
    """127.0.0.1 arrives as ::ffff:127.0.0.1 on a dual-stack listener.

    ``ipaddress`` resolves an IPv4-mapped address inside ``is_loopback`` from CPython
    3.10.16, 3.11.11, 3.12.4 and 3.13.0 on. Before those patch releases ``if
    addr.is_loopback`` is False for ``::ffff:127.0.0.1`` and the branch below is what
    recognises the Express proxy.
    The Dockerfile pins no Python patch version -- it apt-installs Debian bookworm's
    ``python3`` and builds the venv from it -- and nothing in this repo records which
    point release the image actually runs, so nothing here can show the interpreter is
    past the backport. The branch is therefore the only guarantee of the behaviour in
    production.
    The CI pin ``3.11`` resolves to the newest 3.11.x, which carries the change, so CI
    does not exercise the branch.
    Measured on this machine (``ipaddress.ip_address("::ffff:127.0.0.1").is_loopback``):
    True 3.10.20, 3.12.13, 3.13.12, 3.14.7; False 3.11.4.
    Take the branch away and X-Real-IP is no longer trusted, every request
    silently takes the X-Forwarded-For path instead, and the bucket becomes an
    upstream hop rather than the visitor -- this card's fragmentation on a
    different listener, with nothing logged.

    The two branches are made to disagree (X-Real-IP names CLIENT, the chain
    names OTHER) so the assertion names the branch and not merely the outcome.

    Kills the mutation: replace the ``_is_loopback(client_host)`` call in
    ``client_ip`` with a literal set, ``client_host in ("127.0.0.1", "::1")``.
    That is the only test in this file that goes red for it, because every other
    one hands the peer a plain 127.0.0.1, which the set still matches.

    It does *not* kill the IPv4-mapped branch written by hand inside
    ``_is_loopback``. ``ipaddress`` resolves an IPv4-mapped address inside ``is_loopback``
    from CPython 3.10.16, 3.11.11, 3.12.4 and 3.13.0 on. Before those patch releases
    ``if addr.is_loopback`` is False for ``::ffff:127.0.0.1`` and the branch below is
    what recognises the Express proxy. The Dockerfile pins no Python patch version -- it
    apt-installs Debian bookworm's ``python3`` and builds the venv from it -- and nothing
    in this repo records which point release the image actually runs, so nothing here
    can show the interpreter is past the backport. The branch is therefore the only
    guarantee of the behaviour in production. The CI pin ``3.11`` resolves to the newest
    3.11.x, which carries the change, so CI does not exercise the branch.
    Measured on this machine (``ipaddress.ip_address("::ffff:127.0.0.1").is_loopback``):
    True 3.10.20, 3.12.13, 3.13.12, 3.14.7; False 3.11.4.
    """
    headers = Headers({"x-real-ip": CLIENT, "x-forwarded-for": f"{OTHER}, {EDGE}"})
    assert client_ip(headers, "::ffff:127.0.0.1") == CLIENT, (
        "a dual-stack peer is the Express proxy on this host, so X-Real-IP must "
        "still be trusted; without the IPv4-mapped branch the bucket falls back "
        "to an upstream hop"
    )


def test_the_trusted_hop_count_is_the_documented_two():
    # The rule above is only as good as this number: Express sets trust proxy 1
    # and the Railway edge is the hop in front of it.
    assert TRUSTED_PROXY_HOPS == 2


# --- a minute of logins -----------------------------------------------------


def test_a_whole_minute_of_logins_reaches_429_in_one_bucket():
    for shape in SHAPES:
        store = _WindowStore()
        middleware, engine = _middleware(store)
        limit = middleware.rate_limit_auth
        with engine:
            statuses = _drive(middleware, 33, **_headers(shape, CLIENT))
        assert statuses[:limit] == [200] * limit, shape
        assert statuses[limit:] == [429] * (33 - limit), (
            f"{shape}: every request past the limit must be refused — "
            f"33 x 200 with a 10/min limit was the production bug, got {statuses}"
        )
        assert list(store.rows) == [(CLIENT, "auth")], (
            f"{shape}: one client must occupy one bucket, got {sorted(store.rows)}"
        )


def test_a_forged_leftmost_entry_does_not_open_a_new_bucket():
    for shape in SHAPES:
        store = _WindowStore()
        middleware, engine = _middleware(store)
        limit = middleware.rate_limit_auth
        with engine:
            first = _drive(middleware, limit, **_headers(shape, CLIENT))
            # The caller prepends an address of its choosing. Behind two trusted
            # hops that value is the caller's own text, not a routing fact.
            forged = [f"10.0.0.{n}, {CLIENT}, {EDGE}" for n in range(limit)]
            second = [
                _post(middleware, **_headers(shape, CLIENT, xff=xff)).status_code
                for xff in forged
            ]
        assert first == [200] * limit, shape
        assert second == [429] * limit, (
            f"{shape}: a caller-chosen leftmost entry must not open a new bucket, got {second}"
        )
        assert list(store.rows) == [(CLIENT, "auth")], (
            f"{shape}: got {sorted(store.rows)}"
        )


def test_two_clients_behind_one_edge_do_not_share_a_bucket():
    for shape in SHAPES:
        store = _WindowStore()
        middleware, engine = _middleware(store)
        limit = middleware.rate_limit_auth
        with engine:
            mine = _drive(middleware, limit, **_headers(shape, CLIENT))
            theirs = _drive(middleware, limit, **_headers(shape, OTHER))
        assert mine == [200] * limit, shape
        assert theirs == [200] * limit, (
            f"{shape}: one client's traffic must not rate-limit another's"
        )
        assert set(store.rows) == {(CLIENT, "auth"), (OTHER, "auth")}, shape


def test_a_direct_caller_cannot_choose_its_bucket_with_x_real_ip():
    store = _WindowStore()
    middleware, engine = _middleware(store)
    limit = middleware.rate_limit_auth
    with engine:
        statuses = [
            _post(
                middleware,
                peer="10.1.2.3",
                real_ip=f"172.16.0.{n}",
                xff=f"{CLIENT}, {EDGE}",
            ).status_code
            for n in range(limit + 1)
        ]
    assert statuses[:limit] == [200] * limit
    assert statuses[limit] == 429, (
        f"a non-loopback peer is not the Express proxy, so X-Real-IP is the "
        f"caller's own header — trusting it let each request pick a bucket. Got {statuses}"
    )
    assert list(store.rows) == [(CLIENT, "auth")], f"got {sorted(store.rows)}"
