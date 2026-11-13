"""Tally and WooCommerce call a user-supplied server; it must be a public host.

Ported from #138 onto the shared check in server/core/url_safety.py. Tally's
``tally_url`` was not one of the checked fields and defaulted to
http://localhost:9000, so a connect or sync request made this server call
itself (or any internal address it was given). WooCommerce's ``store_url`` was
checked at construction only with ``allow_unresolved=True``, so a name that did
not resolve yet (or later resolved inward) was never re-checked.
"""

import asyncio
import socket

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors.tally import TallyConnector
from server.connectors.woocommerce import WooCommerceConnector
from server.core.url_safety import UnsafeTargetError

INTERNAL_URLS = [
    "http://127.0.0.1:9000",
    "http://2130706433/",  # decimal 127.0.0.1
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://10.1.2.3/",
    "http://172.16.0.5/",
    "http://192.168.1.1/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://localhost:9000",
    "http://postgres.railway.internal:5432",
    "http://metadata.google.internal/",
]


def _config(provider: str, creds: dict) -> ConnectorConfig:
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds)


class _DNS:
    """Controllable resolver: every name maps to ``self.address`` (or fails)."""

    def __init__(self):
        self.address = "93.184.216.34"

    def __call__(self, host, port, *args, **kwargs):
        # Numeric hosts resolve to themselves, as the C resolver does.
        if host in ("2130706433",):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port or 0))]
        if self.address is None:
            raise socket.gaierror("unknown host")
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (self.address, port or 0))]


@pytest.fixture
def dns(monkeypatch):
    resolver = _DNS()
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    return resolver


@pytest.fixture
def sent(monkeypatch):
    calls = []

    async def fake_send(self, request, *args, **kwargs):
        calls.append(str(request.url))
        return httpx.Response(200, content=b"<ENVELOPE></ENVELOPE>", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    return calls


def _tally(url):
    creds = {"company_name": "Acme"}
    if url is not None:
        creds["tally_url"] = url
    return TallyConnector(_config("tally", creds))


def _woo(url):
    return WooCommerceConnector(
        _config("woocommerce", {"store_url": url, "consumer_key": "ck", "consumer_secret": "cs"})
    )


# --- Tally ------------------------------------------------------------------


@pytest.mark.parametrize("url", INTERNAL_URLS)
def test_tally_never_requests_an_internal_host(url, sent, dns):
    try:
        conn = _tally(url)
    except UnsafeTargetError:
        assert sent == []
        return
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_tally_without_a_url_no_longer_calls_localhost(sent, dns):
    conn = _tally(None)
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_tally_rechecks_dns_before_the_first_request(sent, dns):
    # Resolves publicly when the connector is built ...
    conn = _tally("http://tally.example.com:9000")
    # ... and to an internal address by the time it is used.
    dns.address = "10.0.0.7"
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_tally_unresolvable_at_request_time_is_refused(sent, dns):
    dns.address = None
    conn = _tally("http://tally.example.com:9000")  # allowed while unresolved
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_tally_public_host_is_allowed_without_redirects(sent, dns):
    conn = _tally("http://tally.example.com:9000")
    assert asyncio.run(conn.authenticate()) is True
    assert sent and sent[0].startswith("http://tally.example.com:9000")
    client = asyncio.run(conn._get_client())
    assert client.follow_redirects is False


def test_tally_forms_client_does_not_follow_redirects(dns):
    conn = TallyConnector(_config("tally", {"use_tally_forms": True, "api_key": "k"}))
    client = asyncio.run(conn._get_client())
    assert client.follow_redirects is False


# --- WooCommerce ------------------------------------------------------------


@pytest.mark.parametrize("url", INTERNAL_URLS)
def test_woocommerce_never_requests_an_internal_store(url, sent, dns):
    try:
        conn = _woo(url)
    except ValueError:  # UnsafeTargetError is a ValueError
        assert sent == []
        return
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_woocommerce_rechecks_dns_before_sending_credentials(sent, dns):
    dns.address = None
    conn = _woo("https://shop.example.com")  # unresolved at construction: let through
    dns.address = "::1"
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_woocommerce_public_store_is_allowed_without_redirects(sent, dns):
    conn = _woo("https://shop.example.com")
    asyncio.run(conn.authenticate())
    assert sent and sent[0].startswith("https://shop.example.com/wp-json/wc/v3/products")
    client = asyncio.run(conn._get_client())
    assert client.follow_redirects is False
