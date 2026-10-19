/**
 * FastAPI redirect_slashes builds an absolute Location from the request host.
 * The Express proxy strips /api and sets changeOrigin, so that host is the
 * internal bind (https://localhost:8001/templates/) and the public prefix is
 * gone. Rewrite only those upstream locations. Anything else — Google OAuth,
 * /auth/callback, email click targets — is left alone.
 *
 * The public origin is APP_BASE_URL. The request Host and X-Forwarded-Host
 * are not used: a client can set either and turn this into an open redirect.
 */
import type { IncomingHttpHeaders } from "http";

const LOOPBACK = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

export interface RedirectHeaders {
  headers: IncomingHttpHeaders;
  statusCode?: number;
}

export interface RedirectRequest {
  headers: IncomingHttpHeaders;
  protocol?: string;
}

export interface UpstreamRedirectOptions {
  upstreamOrigin: string;
  /** Restored when the proxy stripped it. Empty when the path already includes the mount. */
  publicPrefix?: string;
}

function normalizeHost(hostname: string): string {
  return hostname.toLowerCase().replace(/^\[|\]$/g, "");
}

function isLoopback(hostname: string): boolean {
  return LOOPBACK.has(normalizeHost(hostname));
}

function portOf(url: URL): string {
  if (url.port) return url.port;
  return url.protocol === "https:" ? "443" : "80";
}

function locationTargetsUpstream(url: URL, upstream: URL): boolean {
  const host = normalizeHost(url.hostname);
  const upstreamHost = normalizeHost(upstream.hostname);
  const sameBind = host === upstreamHost || (isLoopback(host) && isLoopback(upstreamHost));
  if (!sameBind) return false;
  // Port must match so https://localhost:8001 (the leaked bind) is rewritten
  // and http://localhost:5000 (the public dev server) is not treated as upstream.
  return portOf(url) === portOf(upstream);
}

function prefixPath(pathname: string, search: string, hash: string, publicPrefix: string | undefined): string {
  const prefix = (publicPrefix || "").replace(/\/$/, "");
  let path = pathname || "/";
  if (!path.startsWith("/")) path = `/${path}`;
  if (prefix && path !== prefix && !path.startsWith(`${prefix}/`)) {
    path = `${prefix}${path}`;
  }
  return `${path}${search}${hash}`;
}

/** Origin of the rewritten Location. Never the request Host. */
function publicOriginFromAppBase(): { host: string; protocol: string } {
  const raw = (process.env.APP_BASE_URL || "").trim();
  if (!raw) return { host: "", protocol: "https" };
  try {
    const url = new URL(raw);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return { host: "", protocol: "https" };
    }
    return { host: url.host, protocol: url.protocol.replace(/:$/, "") };
  } catch {
    return { host: "", protocol: "https" };
  }
}

export function rewriteUpstreamLocation(
  location: string,
  options: UpstreamRedirectOptions & { publicHost: string; publicProtocol: string },
): string {
  const trimmed = location.trim();
  if (!trimmed) return location;

  if (trimmed.startsWith("/") && !trimmed.startsWith("//")) {
    let parsed: URL;
    try {
      parsed = new URL(trimmed, "http://rewrite.local");
    } catch {
      return location;
    }
    return prefixPath(parsed.pathname, parsed.search, parsed.hash, options.publicPrefix);
  }

  let absolute: URL;
  try {
    absolute = new URL(trimmed.startsWith("//") ? `https:${trimmed}` : trimmed);
  } catch {
    return location;
  }

  let upstream: URL;
  try {
    upstream = new URL(options.upstreamOrigin);
  } catch {
    return location;
  }

  if (!locationTargetsUpstream(absolute, upstream)) return location;

  const path = prefixPath(absolute.pathname, absolute.search, absolute.hash, options.publicPrefix);
  const publicHost = options.publicHost.trim();
  if (!publicHost) return path;
  const protocol = options.publicProtocol === "http" ? "http" : "https";
  return `${protocol}://${publicHost}${path}`;
}

export function applyUpstreamRedirectRewrite(
  proxyRes: RedirectHeaders,
  req: RedirectRequest,
  options: UpstreamRedirectOptions,
): void {
  // req is part of the proxy callback shape. Its Host is intentionally unread.
  void req;
  const status = proxyRes.statusCode ?? 0;
  if (status < 300 || status >= 400) return;

  const current = proxyRes.headers.location;
  if (!current) return;
  const values = Array.isArray(current) ? current : [current];
  const origin = publicOriginFromAppBase();
  const publicHost = origin.host;
  const publicProtocol = origin.protocol;
  const rewritten = values.map((value) =>
    rewriteUpstreamLocation(value, {
      ...options,
      publicHost,
      publicProtocol,
    }),
  );
  // Node's header type is a single string. A duplicate Location is not a
  // slash-redirect we need to preserve; the first value is the one clients use.
  proxyRes.headers.location = rewritten[0];
}
