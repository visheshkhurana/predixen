"""
Outbound URL validation for connectors that call a user-supplied host.

A connector that takes a base URL from the user (Tally, WooCommerce) must
only ever reach the public internet. ``validate_public_url`` enforces that:

- scheme must be https (http is allowed only outside production),
- the host must not be an internal name (localhost, *.internal, *.local,
  *.railway.internal, ...),
- every address the host resolves to must be globally routable. IP literals
  are parsed the way the C resolver parses them, so decimal / octal / hex
  IPv4 forms are caught, and IPv4-mapped IPv6 is unwrapped.

Clients built on top of a validated URL must also be created with
``follow_redirects=False`` (see ``SAFE_CLIENT_KWARGS``) so a public host
cannot bounce the request to an internal one.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

SAFE_CLIENT_KWARGS = {"follow_redirects": False}

_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
}
_BLOCKED_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".railway.internal",
    ".localdomain",
    ".home.arpa",
)


class UnsafeURLError(ValueError):
    """The URL points somewhere a connector must not reach."""


def _http_allowed() -> bool:
    try:
        from server.core.config import settings

        return not settings.is_production
    except Exception:  # pragma: no cover - config import failure -> be strict
        return False


def _parse_ip_literal(host: str) -> Optional[ipaddress._BaseAddress]:
    """Return an address if ``host`` is any IP literal form, else None."""
    h = host.strip("[]")
    try:
        return ipaddress.ip_address(h)
    except ValueError:
        pass
    # inet_aton accepts the legacy forms: 2130706433, 0177.0.0.1, 0x7f.1, 127.1
    if all(c in "0123456789abcdefxABCDEFX." for c in h) and any(c.isdigit() for c in h):
        try:
            return ipaddress.IPv4Address(socket.inet_aton(h))
        except OSError:
            return None
    return None


def _is_public(addr: ipaddress._BaseAddress) -> bool:
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:
            return _is_public(addr.ipv4_mapped)
        if addr.sixtofour is not None:
            return _is_public(addr.sixtofour)
        if addr.teredo is not None:
            return False
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        return False
    return addr.is_global


def _check_host_name(host: str) -> None:
    h = host.lower().rstrip(".")
    if not h:
        raise UnsafeURLError("URL must include a host")
    if h in _BLOCKED_HOSTNAMES or h.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeURLError("URL must point to a public host")
    if "." not in h and _parse_ip_literal(h) is None:
        # single-label names resolve via search domains to internal hosts
        raise UnsafeURLError("URL must point to a public host")


def _resolve(host: str, port: int) -> list[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError("URL host could not be resolved") from exc
    addrs = []
    for info in infos:
        ip = info[4][0].split("%", 1)[0]
        addrs.append(ipaddress.ip_address(ip))
    if not addrs:
        raise UnsafeURLError("URL host could not be resolved")
    return addrs


def validate_public_url(
    url: str,
    *,
    resolve: bool = True,
    allow_http: Optional[bool] = None,
) -> str:
    """Raise ``UnsafeURLError`` unless ``url`` targets a public host.

    ``resolve=False`` skips DNS (cheap structural check, e.g. in __init__);
    callers must run the full check before the first request.
    Returns the URL unchanged on success.
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("URL is required")
    if len(url) > 2048:
        raise UnsafeURLError("URL is too long")
    parsed = urlparse(url.strip())
    if allow_http is None:
        allow_http = _http_allowed()
    allowed_schemes = ("https", "http") if allow_http else ("https",)
    if parsed.scheme not in allowed_schemes:
        raise UnsafeURLError("URL must use https://")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URL must not embed credentials")
    host = parsed.hostname or ""
    _check_host_name(host)

    literal = _parse_ip_literal(host)
    if literal is not None:
        if not _is_public(literal):
            raise UnsafeURLError("URL must point to a public host")
        return url

    if resolve:
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise UnsafeURLError("URL has an invalid port") from exc
        for addr in _resolve(host, port):
            if not _is_public(addr):
                raise UnsafeURLError("URL must point to a public host")
    return url


async def validate_public_url_async(url: str, **kwargs) -> str:
    """``validate_public_url`` with DNS off the event loop."""
    return await asyncio.to_thread(validate_public_url, url, **kwargs)
