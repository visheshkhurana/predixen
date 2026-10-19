// GET /api/templates (no slash) used to 307 to https://localhost:8001/templates/.
// FastAPI redirect_slashes builds that Location from the internal bind, and the
// proxy has already stripped /api. Rewrites must use the public host and put
// /api back. OAuth and other external redirects stay untouched.
//
// Run: npx tsx --test server/tests/upstream-redirect-rewrite.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "fs";
import http from "http";
import type { Server } from "http";
import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import {
  applyUpstreamRedirectRewrite,
  rewriteUpstreamLocation,
} from "../proxy/rewriteUpstreamLocation.ts";

const UPSTREAM = "http://localhost:8001";
const PUBLIC = {
  publicHost: "founderconsole.ai",
  publicProtocol: "https",
  upstreamOrigin: UPSTREAM,
  publicPrefix: "/api",
};

test("internal slash redirects use the public host and /api prefix", () => {
  assert.equal(
    rewriteUpstreamLocation("https://localhost:8001/templates/", PUBLIC),
    "https://founderconsole.ai/api/templates/",
  );
  assert.equal(
    rewriteUpstreamLocation("http://127.0.0.1:8001/companies?x=1", PUBLIC),
    "https://founderconsole.ai/api/companies?x=1",
  );
  assert.equal(
    rewriteUpstreamLocation("https://localhost:8001/api/templates/", PUBLIC),
    "https://founderconsole.ai/api/templates/",
  );
  assert.equal(
    rewriteUpstreamLocation("//localhost:8001/templates/", PUBLIC),
    "https://founderconsole.ai/api/templates/",
  );
});

test("relative api redirects gain /api and external redirects are unchanged", () => {
  assert.equal(rewriteUpstreamLocation("/templates/", PUBLIC), "/api/templates/");
  assert.equal(rewriteUpstreamLocation("/api/templates/", PUBLIC), "/api/templates/");
  assert.equal(
    rewriteUpstreamLocation(
      "https://accounts.google.com/o/oauth2/v2/auth?client_id=x",
      PUBLIC,
    ),
    "https://accounts.google.com/o/oauth2/v2/auth?client_id=x",
  );
  assert.equal(
    rewriteUpstreamLocation("https://founderconsole.ai/auth/callback?user_id=1", PUBLIC),
    "https://founderconsole.ai/auth/callback?user_id=1",
  );
});

test("a loopback public host that is not the upstream port is kept", () => {
  assert.equal(
    rewriteUpstreamLocation("https://localhost:8001/templates/", {
      ...PUBLIC,
      publicHost: "localhost:5000",
      publicProtocol: "http",
    }),
    "http://localhost:5000/api/templates/",
  );
});

test("when APP_BASE_URL is unset, the location stays relative", () => {
  const previous = process.env.APP_BASE_URL;
  delete process.env.APP_BASE_URL;
  try {
    const headers: { location?: string } = { location: "https://localhost:8001/templates/" };
    applyUpstreamRedirectRewrite(
      { statusCode: 307, headers },
      { headers: { host: "evil.example" }, protocol: "http" },
      { upstreamOrigin: UPSTREAM, publicPrefix: "/api" },
    );
    assert.equal(headers.location, "/api/templates/");
  } finally {
    if (previous === undefined) delete process.env.APP_BASE_URL;
    else process.env.APP_BASE_URL = previous;
  }
});

test("an evil Host header cannot choose the redirect origin", () => {
  const previous = process.env.APP_BASE_URL;
  process.env.APP_BASE_URL = "https://founderconsole.ai";
  try {
    const headers: { location?: string } = { location: "https://localhost:8001/templates/" };
    applyUpstreamRedirectRewrite(
      { statusCode: 307, headers },
      {
        headers: {
          host: "evil.example",
          "x-forwarded-host": "evil.example",
          "x-forwarded-proto": "http",
        },
        protocol: "http",
      },
      { upstreamOrigin: UPSTREAM, publicPrefix: "/api" },
    );
    assert.equal(headers.location, "https://founderconsole.ai/api/templates/");
    assert.equal(headers.location.includes("evil.example"), false);
  } finally {
    if (previous === undefined) delete process.env.APP_BASE_URL;
    else process.env.APP_BASE_URL = previous;
  }
});

test("non-redirects and other proxies are not prefixed twice", () => {
  const headers: { location?: string } = { location: "https://localhost:8001/templates/" };
  applyUpstreamRedirectRewrite(
    { statusCode: 200, headers },
    { headers: { host: "founderconsole.ai" } },
    { upstreamOrigin: UPSTREAM, publicPrefix: "/api" },
  );
  assert.equal(headers.location, "https://localhost:8001/templates/");

  assert.equal(
    rewriteUpstreamLocation("https://localhost:8001/notifications/track/abc", {
      ...PUBLIC,
      publicPrefix: "",
    }),
    "https://founderconsole.ai/notifications/track/abc",
  );
});

test("the api proxy rewrites a leaked Location before the browser sees it", async () => {
  const previous = process.env.APP_BASE_URL;
  process.env.APP_BASE_URL = "https://founderconsole.ai";
  const upstream = http.createServer((req, res) => {
    const path = req.url || "/";
    if (path.startsWith("/external")) {
      res.writeHead(302, { Location: "https://accounts.google.com/o/oauth2/v2/auth?x=1" });
      res.end();
      return;
    }
    res.writeHead(307, { Location: "https://localhost:8001/templates/" });
    res.end();
  });
  await listen(upstream);
  const upstreamPort = (upstream.address() as { port: number }).port;

  const app = express();
  app.set("trust proxy", true);
  app.use(
    "/api",
    createProxyMiddleware({
      target: `http://127.0.0.1:${upstreamPort}`,
      changeOrigin: true,
      pathRewrite: { "^/api": "" },
      logger: { info() {}, warn() {}, error() {} },
      on: {
        proxyRes: (proxyRes, req) => {
          applyUpstreamRedirectRewrite(proxyRes, req, {
            upstreamOrigin: UPSTREAM,
            publicPrefix: "/api",
          });
        },
      },
    }),
  );
  const proxy = await listen(app);

  try {
    const leaked = await request(proxy, "/api/templates", {
      host: "evil.example",
      "x-forwarded-host": "evil.example",
      "x-forwarded-proto": "http",
    });
    assert.equal(leaked.status, 307);
    assert.equal(leaked.location, "https://founderconsole.ai/api/templates/");
    assert.equal(leaked.location.includes("localhost"), false);
    assert.equal(leaked.location.includes("8001"), false);
    assert.equal(leaked.location.includes("evil.example"), false);

    const oauth = await request(proxy, "/api/external", {
      host: "evil.example",
      "x-forwarded-proto": "http",
    });
    assert.equal(oauth.status, 302);
    assert.equal(oauth.location, "https://accounts.google.com/o/oauth2/v2/auth?x=1");
  } finally {
    proxy.close();
    upstream.close();
    if (previous === undefined) delete process.env.APP_BASE_URL;
    else process.env.APP_BASE_URL = previous;
  }
});

test("index.ts wires the rewrite onto the /api proxy", () => {
  const index = readFileSync("server/index.ts", "utf8");
  assert.match(index, /applyUpstreamRedirectRewrite/);
  assert.match(index, /publicPrefix:\s*"\/api"/);
});

function listen(server: Server | express.Express): Promise<Server> {
  const httpServer = "listen" in server && typeof (server as Server).address === "function"
    ? (server as Server)
    : http.createServer(server as express.Express);
  return new Promise((resolve) => {
    httpServer.listen(0, "127.0.0.1", () => resolve(httpServer));
  });
}

function request(
  server: Server,
  path: string,
  headers: Record<string, string>,
): Promise<{ status: number; location: string | undefined }> {
  const address = server.address() as { port: number };
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: "127.0.0.1",
        port: address.port,
        path,
        method: "GET",
        headers,
      },
      (res) => {
        res.resume();
        const location = res.headers.location;
        resolve({
          status: res.statusCode || 0,
          location: Array.isArray(location) ? location[0] : location,
        });
      },
    );
    req.on("error", reject);
    req.end();
  });
}
