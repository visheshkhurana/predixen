// /ws upgrade must carry a real session and only deliver a company's events to its members.
// Run: npx tsx --test server/tests/ws-auth.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { createServer, type Server, type IncomingMessage } from "node:http";
import type { AddressInfo } from "node:net";
import { WebSocket } from "ws";

const SECRET = "ws-auth-test-secret";
process.env.SECRET_KEY = SECRET;
delete process.env.DATABASE_URL;

import {
  authenticateUpgrade,
  canAccessCompany,
  isAllowedUpgradeOrigin,
  setWsQueryForTests,
} from "../wsAuth";
import {
  setupWebSocketServer,
  broadcastMetricUpdate,
  broadcastSimulationUpdate,
} from "../websocket";

function b64(obj: unknown): string {
  return Buffer.from(JSON.stringify(obj)).toString("base64url");
}

function sign(payload: Record<string, unknown>, secret = SECRET): string {
  const header = b64({ alg: "HS256", typ: "JWT" });
  const body = b64(payload);
  const sig = crypto.createHmac("sha256", secret).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${sig}`;
}

function live(sub: string, extra: Record<string, unknown> = {}): string {
  return sign({ sub, jti: `jti-${sub}`, iat: 1_700_000_000, exp: Math.floor(Date.now() / 1000) + 3600, ...extra });
}

// user 7 owns company 5; scenario 11 belongs to company 5; company 9 is someone else's.
setWsQueryForTests(async (sql: string, params: unknown[]) => {
  if (sql.includes("revoked_access_tokens")) {
    return { rows: params[0] === "jti-revoked" ? [{ revoked: 1 }] : [] };
  }
  if (sql.includes("user_session_cutoffs")) return { rows: [] };
  if (sql.includes("FROM companies")) {
    return { rows: params[0] === 5 && params[1] === 7 ? [{ ok: 1 }] : [] };
  }
  if (sql.includes("FROM scenarios")) {
    return { rows: params[0] === 11 ? [{ company_id: 5 }] : [] };
  }
  return { rows: [] };
});

function fakeReq(headers: Record<string, string>, url = "/ws"): IncomingMessage {
  return { headers, url } as unknown as IncomingMessage;
}

test("an unsigned or wrongly signed token is refused", async () => {
  const forged = `${b64({ alg: "none" })}.${b64({ sub: "7", exp: 9_999_999_999 })}.x`;
  assert.equal(await authenticateUpgrade(fakeReq({}, `/ws?token=${forged}`)), null);
  const wrongKey = sign({ sub: "7", exp: 9_999_999_999 }, "other-secret");
  assert.equal(await authenticateUpgrade(fakeReq({ cookie: `auth_token=${wrongKey}` })), null);
});

test("a revoked token is refused; a live cookie session is accepted", async () => {
  assert.equal(await authenticateUpgrade(fakeReq({ cookie: `auth_token=${live("7", { jti: "jti-revoked" })}` })), null);
  const user = await authenticateUpgrade(fakeReq({ cookie: `a=b; auth_token=${live("7")}` }));
  assert.deepEqual(user, { sub: "7", isMaster: false });
});

test("cross-site upgrade origins are refused", () => {
  assert.equal(isAllowedUpgradeOrigin(fakeReq({ host: "app.test", origin: "https://app.test" })), true);
  assert.equal(isAllowedUpgradeOrigin(fakeReq({ host: "app.test", origin: "https://evil.test" })), false);
  assert.equal(isAllowedUpgradeOrigin(fakeReq({ host: "app.test" })), true);
});

test("company access requires ownership or membership", async () => {
  assert.equal(await canAccessCompany({ sub: "7", isMaster: false }, 5), true);
  assert.equal(await canAccessCompany({ sub: "7", isMaster: false }, 9), false);
  assert.equal(await canAccessCompany({ sub: "7", isMaster: false }, "5 OR 1=1"), false);
});

async function startServer(): Promise<{ server: Server; port: number }> {
  const server = createServer();
  setupWebSocketServer(server);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { server, port: (server.address() as AddressInfo).port };
}

function open(port: number, query: string, headers: Record<string, string> = {}): Promise<{ ws: WebSocket; messages: any[] } | { status: number }> {
  return new Promise((resolve) => {
    const ws = new WebSocket(`ws://127.0.0.1:${port}/ws${query}`, { headers });
    const messages: any[] = [];
    ws.on("message", (data) => messages.push(JSON.parse(data.toString())));
    ws.on("unexpected-response", (_req, res) => resolve({ status: res.statusCode || 0 }));
    ws.on("error", () => {});
    ws.on("open", () => resolve({ ws, messages }));
  });
}

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

test("socket: forged session rejected; events reach only the company's members", async () => {
  const { server, port } = await startServer();
  try {
    const forged = await open(port, `?companyId=9&token=${b64({ alg: "none" })}.${b64({ sub: "1" })}.x`);
    assert.ok("status" in forged && forged.status === 401);

    const own = await open(port, "?companyId=5", { cookie: `auth_token=${live("7")}` });
    const other = await open(port, "?companyId=9", { cookie: `auth_token=${live("7")}` });
    assert.ok("ws" in own && "ws" in other);
    await wait(100);

    // Subscribing to a foreign company afterwards is refused too.
    other.ws.send(JSON.stringify({ type: "subscribe", companyId: 9 }));
    await wait(100);

    broadcastMetricUpdate(5, { mrr: 1 });
    broadcastMetricUpdate(9, { mrr: 2 });
    await broadcastSimulationUpdate(11, "completed", 100, { p50: 3 });
    await wait(100);

    const ownTypes = own.messages.map((m) => m.type);
    assert.ok(ownTypes.includes("metric_update"));
    assert.ok(ownTypes.includes("simulation_complete"));
    assert.ok(!own.messages.some((m) => m.type === "metric_update" && m.payload.companyId === 9));
    assert.ok(!other.messages.some((m) => m.type === "metric_update" || m.type === "simulation_complete"));

    const crossSite = await open(port, "?companyId=5", { cookie: `auth_token=${live("7")}`, origin: "https://evil.test" });
    assert.ok("status" in crossSite && crossSite.status === 403);

    own.ws.close();
    other.ws.close();
  } finally {
    server.close();
  }
});
