"""Outbound target checks for URLs and hosts that come from user input.

Connector credentials can name a server (base_url, instance_url, store_url,
endpoint_url, tally_url, host) or a tenant label that is spliced into a vendor hostname
(shop_domain, site, company_domain, account_id). Both are validated before a
connector is built.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import urlsplit


class UnsafeTargetError(ValueError):
    """A user-supplied outbound target that is not a public internet address."""


# Fields whose value is a full URL.
URL_FIELDS = ("base_url", "instance_url", "store_url", "endpoint_url", "api_url", "url", "tally_url")
# Fields whose value is a bare hostname.
HOST_FIELDS = ("host",)
# Fields spliced into a vendor hostname as a label.
LABEL_FIELDS = ("shop_domain", "site", "company_domain", "account_id")

# httpx clients built on a user-supplied base URL. A public host must not be
# able to bounce the request to an internal one with a redirect.
SAFE_CLIENT_KWARGS = {"follow_redirects": False}

_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,252})$")


def _ip_is_public(ip: ipaddress._BaseAddress) -> bool:
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"))
    )


def _resolve(host: str) -> Iterable[str]:
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return {info[4][0] for info in infos}


def assert_public_host(host: Optional[str], *, resolver=_resolve, allow_unresolved: bool = False) -> None:
    """Raise unless every address the host resolves to is public.

    ``allow_unresolved`` lets a name that does not resolve right now through;
    a request to it cannot connect anywhere either.
    """
    name = (host or "").strip().rstrip(".").lower()
    if not name:
        raise UnsafeTargetError("host is required")
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    if name == "localhost" or name.endswith(".localhost") or name.endswith(".internal") or name.endswith(".local"):
        raise UnsafeTargetError("host is not allowed")
    try:
        literal = ipaddress.ip_address(name)
    except ValueError:
        literal = None
    if literal is not None:
        if not _ip_is_public(literal):
            raise UnsafeTargetError("host is not allowed")
        return
    try:
        addresses = list(resolver(name))
    except (socket.gaierror, UnicodeError, OSError):
        addresses = []
    if not addresses:
        if allow_unresolved:
            return
        raise UnsafeTargetError("host could not be resolved")
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr.split("%", 1)[0])
        except ValueError:
            raise UnsafeTargetError("host is not allowed")
        if not _ip_is_public(ip):
            raise UnsafeTargetError("host is not allowed")


def assert_public_url(url: Optional[str], *, resolver=_resolve, allow_unresolved: bool = False) -> None:
    """Raise unless the URL is http(s) to a public host, with no embedded credentials."""
    value = (url or "").strip()
    try:
        parts = urlsplit(value)
    except ValueError:
        raise UnsafeTargetError("URL is not valid")
    if parts.scheme not in ("http", "https"):
        raise UnsafeTargetError("URL must use http or https")
    if parts.username or parts.password:
        raise UnsafeTargetError("URL must not contain credentials")
    try:
        parts.port
    except ValueError:
        raise UnsafeTargetError("URL is not valid")
    assert_public_host(parts.hostname, resolver=resolver, allow_unresolved=allow_unresolved)


async def assert_public_url_before_request(url: Optional[str], *, resolver=_resolve) -> None:
    """Full check right before a connector's first request to a user-supplied URL.

    Construction runs with ``allow_unresolved=True``. Here the name must resolve,
    and every address it resolves to must be public. DNS runs off the event loop.
    """
    await asyncio.to_thread(assert_public_url, url, resolver=resolver, allow_unresolved=False)


def assert_safe_label(value: Optional[str]) -> None:
    """A tenant label spliced into a vendor hostname: letters, digits, dot, dash, underscore."""
    text = (value or "").strip()
    if not _LABEL_RE.match(text):
        raise UnsafeTargetError("value contains characters that are not allowed")


def validate_connector_targets(*sources: Optional[Mapping[str, Any]], resolver=_resolve) -> None:
    """Check every target-bearing field in connector credentials/settings. Empty values are skipped."""
    for source in sources:
        if not source:
            continue
        for key in URL_FIELDS:
            value = source.get(key)
            if value:
                assert_public_url(str(value), resolver=resolver, allow_unresolved=True)
        for key in HOST_FIELDS:
            value = source.get(key)
            if value:
                assert_public_host(str(value), resolver=resolver, allow_unresolved=True)
        for key in LABEL_FIELDS:
            value = source.get(key)
            if value:
                assert_safe_label(str(value))
