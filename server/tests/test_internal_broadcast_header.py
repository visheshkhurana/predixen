"""Python -> Express broadcasts must carry x-internal-secret.

Express rejects /internal/broadcast/* without it in production (503/401),
which silently killed live WebSocket updates.
"""
import asyncio

import httpx
import pytest

from server.utils import websocket_broadcast as wb
from server.workers import simulation_worker as sw

SECRET = "test-internal-secret"


class _Resp:
    status_code = 200

    def json(self):
        return {"clients": 1}


class _Recorder:
    calls = []

    def __init__(self, *a, **kw):
        self.init_kwargs = kw

    def post(self, url, **kw):
        _Recorder.calls.append((url, kw))
        return _Resp()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _AsyncRecorder(_Recorder):
    async def post(self, url, **kw):
        _Recorder.calls.append((url, kw))
        return _Resp()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def recorder(monkeypatch):
    _Recorder.calls = []
    monkeypatch.setattr(httpx, "Client", _Recorder)
    monkeypatch.setattr(httpx, "AsyncClient", _AsyncRecorder)
    return _Recorder.calls


def _assert_all_signed(calls, expected_count):
    assert len(calls) == expected_count
    for url, kw in calls:
        assert "/internal/broadcast/" in url
        assert kw["headers"]["x-internal-secret"] == SECRET


def test_async_and_sync_broadcasters_send_secret(monkeypatch, recorder):
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    assert asyncio.run(wb.broadcast_metric_update(1, {"mrr": 1}))
    assert asyncio.run(wb.broadcast_simulation_update(2, "running", 50))
    assert asyncio.run(wb.broadcast_truth_scan_update(3))
    assert wb.broadcast_metric_update_sync(1, {"mrr": 1})
    assert wb.broadcast_truth_scan_update_sync(3)
    _assert_all_signed(recorder, 5)


def test_simulation_worker_completion_sends_secret(monkeypatch, recorder):
    monkeypatch.setenv("INTERNAL_API_SECRET", SECRET)
    sw._broadcast_completion(42, {"runway": 12})
    _assert_all_signed(recorder, 1)
    url, kw = recorder[0]
    assert url.endswith("/internal/broadcast/simulation")
    assert kw["json"]["scenarioId"] == 42


def test_secret_read_per_call(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", "one")
    assert wb.internal_headers() == {"x-internal-secret": "one"}
    monkeypatch.setenv("INTERNAL_API_SECRET", "two")
    assert wb.internal_headers() == {"x-internal-secret": "two"}


def test_no_header_when_secret_unset(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_SECRET", raising=False)
    assert wb.internal_headers() == {}
