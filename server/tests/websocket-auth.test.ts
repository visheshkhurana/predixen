// The /ws endpoint must verify the session signature, only subscribe a socket
// to a company the user may access, and scope simulation updates by company.
//
// Run: npx tsx --test server/tests/websocket-auth.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "http";
import WebSocket from "ws";
import { setupWebSocketServer, broadcastSimulationUpdate, broadcastMetricUpdate } from "../websocket";
import { signJwt, inOneHour } from "./helpers/jwt";

const SECRET = "test-secret-websocket";
process.env.SECRET_KEY = SECRET;

// user 1 owns company 10; user 2 owns company 20.
const OWNERS: Record<number, number> = { 10: 1, 20: 2 };

let server: Server;
let base = "";
const sockets = new Set<WebSocket>();

// Every test gets a hard timeout, and a test that never finishes counts as a
// failure. If something (e.g. an older server's ping timer) keeps the event
// loop alive after the run, the after() hook exits with the right status
// instead of hanging CI.
let started = 0;
let finished = 0;
const T = { timeout: 10_000 };
function wsTest(name: string, fn: () => Promise<void>) {
  test(name, T, async () => {
    started++;
    try {
      await fn();
      finished++;
    } finally {
      for (const ws of sockets) ws.terminate();
      sockets.clear();
    }
  });
}

test.before(async () => {
  server = createServer();
  setupWebSocketServer(server, {
    canAccessCompany: async (payload, companyId) => OWNERS[companyId] === Number(payload.sub),
  });
  await new Promise<void>((r) => server.listen(0, "127.0.0.1", () => r()));
  base = `ws://127.0.0.1:${(server.address() as any).port}/ws`;
});

test.after(() => {
  for (const ws of sockets) ws.terminate();
  server.closeAllConnections?.();
  server.close();
  const failed = finished !== started;
  const t = setTimeout(() => process.exit(failed ? 1 : 0), 1_000);
  t.unref();
});

function open(query: string, headers: Record<string, string> = {}): Promise<{ ws: WebSocket; messages: any[] }> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${base}${query}`, { headers });
    sockets.add(ws);
    const timer = setTimeout(() => reject(new Error("no connection message")), 3_000);
    ws.on("close", () => clearTimeout(timer));
    const messages: any[] = [];
    ws.on("message", (d) => {
      const m = JSON.parse(d.toString());
      messages.push(m);
      if (m.type === "connection") {
        clearTimeout(timer);
        resolve({ ws, messages });
      }
    });
    ws.on("unexpected-response", (_req, res) => {
      clearTimeout(timer);
      reject(new Error(`HTTP ${res.statusCode}`));
    });
    ws.on("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
  });
}

const tick = (ms = 100) => new Promise((r) => setTimeout(r, ms));

wsTest("rejects a token whose signature does not verify", async () => {
  const forged = signJwt({ sub: "1", exp: inOneHour() }, "not-the-secret");
  await assert.rejects(open(`?token=${forged}&companyId=10`), /HTTP 401/);
});

wsTest("rejects an expired token", async () => {
  const expired = signJwt({ sub: "1", exp: Math.floor(Date.now() / 1000) - 60 }, SECRET);
  await assert.rejects(open(`?token=${expired}`), /HTTP 401/);
});

wsTest("accepts the auth_token cookie and subscribes to an owned company", async () => {
  const token = signJwt({ sub: "1", exp: inOneHour() }, SECRET);
  const { ws, messages } = await open("?companyId=10", { cookie: `auth_token=${token}` });
  assert.equal(messages[0].payload.companyId, 10);
  ws.close();
});

wsTest("does not subscribe a socket to someone else's company", async () => {
  const token = signJwt({ sub: "1", exp: inOneHour() }, SECRET);
  const { ws, messages } = await open("?companyId=20", { cookie: `auth_token=${token}` });
  assert.equal(messages.find((m) => m.type === "connection").payload.companyId, null);
  ws.send(JSON.stringify({ type: "subscribe", companyId: 20 }));
  await tick();
  broadcastMetricUpdate(20, { cash: 1 });
  await tick();
  assert.equal(messages.filter((m) => m.type === "metric_update").length, 0);
  ws.close();
});

wsTest("simulation updates reach only the owning company's sockets", async () => {
  const t1 = signJwt({ sub: "1", exp: inOneHour() }, SECRET);
  const t2 = signJwt({ sub: "2", exp: inOneHour() }, SECRET);
  const a = await open("?companyId=10", { cookie: `auth_token=${t1}` });
  const b = await open("?companyId=20", { cookie: `auth_token=${t2}` });
  broadcastSimulationUpdate(10, 99, "completed", 100, { ok: true });
  await tick();
  assert.equal(a.messages.filter((m) => m.type === "simulation_complete").length, 1);
  assert.equal(b.messages.filter((m) => m.type === "simulation_complete").length, 0);
  a.ws.close();
  b.ws.close();
});
