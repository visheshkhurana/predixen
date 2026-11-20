"""Connectors wait and retry when a vendor rate-limits them (429)."""

import asyncio
import pathlib

import httpx

from server.connectors.http import RetryTransport, http_client, retry_after_seconds


def _run(coro):
    return asyncio.run(coro)


class _Seq(httpx.AsyncBaseTransport):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def handle_async_request(self, request):
        self.calls += 1
        status, headers = self.responses.pop(0)
        return httpx.Response(status, headers=headers, json={"ok": status == 200}, request=request)


def _client(seq, sleeps, **kw):
    async def fake_sleep(s):
        sleeps.append(s)
    return httpx.AsyncClient(transport=RetryTransport(seq, sleep=fake_sleep, **kw), base_url="https://api.example.com")


def test_429_waits_for_retry_after_then_succeeds():
    seq, sleeps = _Seq([(429, {"Retry-After": "2"}), (200, {})]), []

    async def go():
        async with _client(seq, sleeps) as c:
            return await c.get("/deals")

    res = _run(go())
    assert res.status_code == 200 and seq.calls == 2 and sleeps == [2.0]


def test_429_retries_post_but_503_does_not():
    seq, sleeps = _Seq([(429, {"Retry-After": "0"}), (200, {})]), []

    async def post():
        async with _client(seq, sleeps) as c:
            return await c.post("/query", json={"q": 1})

    assert _run(post()).status_code == 200 and seq.calls == 2

    seq2 = _Seq([(503, {}), (200, {})])

    async def post503():
        async with _client(seq2, []) as c:
            return await c.post("/query", json={"q": 1})

    assert _run(post503()).status_code == 503 and seq2.calls == 1


def test_503_retries_get_with_backoff():
    seq, sleeps = _Seq([(503, {}), (503, {}), (200, {})]), []

    async def go():
        async with _client(seq, sleeps) as c:
            return await c.get("/x")

    assert _run(go()).status_code == 200
    assert len(sleeps) == 2 and 1 <= sleeps[0] < 1.6 and 2 <= sleeps[1] < 2.6


def test_gives_up_after_max_retries_and_returns_the_429():
    seq, sleeps = _Seq([(429, {"Retry-After": "1"})] * 5), []

    async def go():
        async with _client(seq, sleeps, max_retries=3) as c:
            return await c.get("/x")

    assert _run(go()).status_code == 429 and seq.calls == 4 and len(sleeps) == 3


def test_long_retry_after_is_capped_and_budget_stops_waiting():
    seq, sleeps = _Seq([(429, {"Retry-After": "3600"}), (429, {"Retry-After": "3600"}), (200, {})]), []

    async def go():
        async with _client(seq, sleeps, max_wait=20, total_budget=30) as c:
            return await c.get("/x")

    # 20s capped wait, then a second 20s would pass the 30s budget: give up.
    assert _run(go()).status_code == 429 and sleeps == [20]


def test_retry_after_http_date():
    assert retry_after_seconds("Wed, 21 Oct 2015 07:28:10 GMT", now=1445412480.0) == 10.0
    assert retry_after_seconds("garbage") is None
    assert retry_after_seconds(None) is None


def test_http_client_wraps_the_transport():
    client = http_client(timeout=5.0)
    assert isinstance(client._transport, RetryTransport)
    _run(client.aclose())


def test_every_connector_uses_the_retrying_client():
    root = pathlib.Path(__file__).resolve().parents[1] / "connectors"
    offenders = [f.name for f in root.glob("*.py")
                 if f.name != "http.py" and "httpx.AsyncClient(" in f.read_text()]
    assert offenders == []
