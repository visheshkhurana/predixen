"""Record the TCP peer before proxy headers rewrite it.

Uvicorn's ProxyHeadersMiddleware replaces scope["client"] with an
X-Forwarded-For address when the socket peer is loopback. A loopback check
on request.client.host then fails for every Railway request that carries
X-Forwarded-For, and the lead bucket falls through to the two-hop math on a
chain whose edge hop has already been overwritten.

Production starts `uvicorn server.main:asgi_app --no-proxy-headers`. This
wrapper stashes the peer, then applies the same rewrite Uvicorn used to
apply itself, so the rest of the app still sees the forwarded scheme and
client. The rate limiter reads extensions["peer_host"] and trusts X-Real-IP
only when that peer is loopback. Express forwards the edge-supplied header
and does not replace it with req.ip.
"""

from __future__ import annotations

import os

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from server.middleware.rate_limiter import PEER_HOST_KEY


class RecordPeer:
    def __init__(self, app, trusted_hosts: str | None = None):
        if trusted_hosts is None:
            trusted_hosts = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1,::1")
        self.inner = ProxyHeadersMiddleware(app, trusted_hosts=trusted_hosts)

    async def __call__(self, scope, receive, send):
        if scope.get("type") in ("http", "websocket"):
            client = scope.get("client")
            if client and client[0]:
                extensions = scope.get("extensions")
                if not isinstance(extensions, dict):
                    extensions = {}
                    scope["extensions"] = extensions
                extensions.setdefault(PEER_HOST_KEY, client[0])
        await self.inner(scope, receive, send)
