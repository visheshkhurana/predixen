"""User-supplied connector base URLs must only reach public hosts."""

import asyncio
import socket

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors.tally import TallyConnector
from server.connectors.woocommerce import WooCommerceConnector

INTERNAL_URLS = [
    "http://127.0.0.1:9000",
    "http://2130706433/",          # decimal 127.0.0.1
    "http://0177.0.0.1/",          # octal 127.0.0.1
    "http://0x7f.1/",              # hex short form
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://10.1.2.3/",
    "http://172.16.0.5/",
    "http://192.168.1.1/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://224.0.0.1/",
    "http://[fe80::1]/",
    "http://[fd00::1]/",
    "http://localhost:9000",
    "http://postgres.railway.internal:5432",
    "http://metadata.google.internal/",
    "http://intranet/",
]


def _config(provider: str, creds: dict) -> ConnectorConfig:
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds)


@pytest.fixture
def sent(monkeypatch):
    calls = []

    async def fake_send(self, request, *args, **kwargs):
        calls.append(str(request.url))
        return httpx.Response(200, text="<ENVELOPE></ENVELOPE>", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    return calls


@pytest.fixture
def public_dns(monkeypatch):
    """Resolve every name to a public documentation-free address, no network."""

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize("url", INTERNAL_URLS)
def test_tally_never_requests_an_internal_host(url, sent, public_dns):
    conn = TallyConnector(_config("tally", {"tally_url": url, "company_name": "Acme"}))
    ok = asyncio.run(conn.authenticate())
    assert ok is False
    assert sent == []


def test_tally_rejects_a_name_that_resolves_internally(sent, monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    conn = TallyConnector(_config("tally", {"tally_url": "https://tally.example.com"}))
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_tally_public_https_host_is_allowed_without_redirects(sent, public_dns):
    conn = TallyConnector(_config("tally", {"tally_url": "https://tally.example.com"}))
    assert asyncio.run(conn.authenticate()) is True
    assert sent and sent[0].startswith("https://tally.example.com")
    client = asyncio.run(conn._get_client())
    assert client.follow_redirects is False


@pytest.mark.parametrize("url", INTERNAL_URLS)
def test_woocommerce_rejects_internal_store_urls(url, sent, public_dns):
    creds = {"store_url": url, "consumer_key": "ck", "consumer_secret": "cs"}
    try:
        conn = WooCommerceConnector(_config("woocommerce", creds))
    except ValueError:
        return
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_woocommerce_rejects_a_name_that_resolves_internally(sent, monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port, 0, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    creds = {"store_url": "https://shop.example.com", "consumer_key": "ck", "consumer_secret": "cs"}
    conn = WooCommerceConnector(_config("woocommerce", creds))
    assert asyncio.run(conn.authenticate()) is False
    assert sent == []


def test_woocommerce_public_store_is_allowed_without_redirects(sent, public_dns):
    creds = {"store_url": "https://shop.example.com", "consumer_key": "ck", "consumer_secret": "cs"}
    conn = WooCommerceConnector(_config("woocommerce", creds))
    assert asyncio.run(conn.authenticate()) is True
    client = asyncio.run(conn._get_client())
    assert client.follow_redirects is False


def test_plain_http_is_refused_in_production(monkeypatch, public_dns):
    from server.connectors import url_safety
    from server.core.config import settings

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))
    with pytest.raises(url_safety.UnsafeURLError):
        url_safety.validate_public_url("http://shop.example.com")
    assert url_safety.validate_public_url("https://shop.example.com")
