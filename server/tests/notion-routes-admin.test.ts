// The Notion routes share one workspace connection; only the platform owner
// may list or overwrite pages through them.
//
// Run: npx tsx --test server/tests/notion-routes-admin.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { registerNotionRoutes } from "../notion/routes";
import { signJwt, inOneHour } from "./helpers/jwt";

const SECRET = "test-secret-notion";
process.env.SECRET_KEY = SECRET;
delete process.env.ADMIN_MASTER_EMAIL;

let server: Server;
let base = "";

test.before(async () => {
  const app = express();
  registerNotionRoutes(app);
  await new Promise<void>((r) => {
    server = app.listen(0, "127.0.0.1", () => r());
  });
  base = `http://127.0.0.1:${(server.address() as any).port}`;
});
test.after(() => server.close());

const userCookie = () => `auth_token=${signJwt({ sub: "42", exp: inOneHour() }, SECRET)}`;

for (const [method, path] of [
  ["GET", "/api/notion/pages"],
  ["GET", "/api/notion/databases"],
  ["POST", "/api/notion/push-report"],
] as const) {
  test(`${method} ${path} requires a session`, { timeout: 10_000 }, async () => {
    const res = await fetch(base + path, { method });
    assert.equal(res.status, 401);
  });

  test(`${method} ${path} is refused for an ordinary signed-in user`, { timeout: 10_000 }, async () => {
    const res = await fetch(base + path, {
      method,
      headers: { cookie: userCookie(), "content-type": "application/json" },
      body: method === "POST" ? JSON.stringify({ pageId: "abc" }) : undefined,
    });
    assert.ok([403, 503].includes(res.status), `expected 403/503, got ${res.status}`);
  });
}
