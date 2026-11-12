// /internal/broadcast/* must require x-internal-secret wherever
// INTERNAL_API_SECRET is set, and fail closed outside dev/test when it is not.
// Run: npx tsx --test server/tests/internal-broadcast-auth.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { requireInternalAuth } from "../middleware/internalAuth";

const ORIGINAL = { secret: process.env.INTERNAL_API_SECRET, env: process.env.NODE_ENV };

async function withServer(fn: (base: string) => Promise<void>) {
  const app = express();
  app.post("/internal/broadcast/metrics", requireInternalAuth, (_req, res) => res.json({ ok: true }));
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
  try {
    const { port } = server.address() as AddressInfo;
    await fn(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((r) => server.close(r));
  }
}

function set(secret: string | undefined, nodeEnv: string | undefined) {
  if (secret === undefined) delete process.env.INTERNAL_API_SECRET;
  else process.env.INTERNAL_API_SECRET = secret;
  if (nodeEnv === undefined) delete process.env.NODE_ENV;
  else process.env.NODE_ENV = nodeEnv;
}

async function post(base: string, header?: string): Promise<number> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (header !== undefined) headers["x-internal-secret"] = header;
  const res = await fetch(`${base}/internal/broadcast/metrics`, { method: "POST", headers, body: "{}" });
  return res.status;
}

test.after(() => set(ORIGINAL.secret, ORIGINAL.env));

for (const nodeEnv of ["production", "development", "test", "staging", undefined]) {
  test(`secret set (NODE_ENV=${nodeEnv}): header required and must match`, async () => {
    set("s3cret-value", nodeEnv);
    await withServer(async (base) => {
      assert.equal(await post(base), 401);
      assert.equal(await post(base, "wrong"), 401);
      assert.equal(await post(base, "s3cret-valu"), 401);
      assert.equal(await post(base, "s3cret-value-and-more"), 401);
      assert.equal(await post(base, "s3cret-value"), 200);
    });
  });
}

for (const nodeEnv of ["production", "staging", undefined]) {
  test(`secret unset (NODE_ENV=${nodeEnv}): fails closed`, async () => {
    set(undefined, nodeEnv);
    await withServer(async (base) => {
      assert.equal(await post(base), 503);
      assert.equal(await post(base, "anything"), 503);
    });
  });
}

for (const nodeEnv of ["development", "test"]) {
  test(`secret unset (NODE_ENV=${nodeEnv}): open for local work`, async () => {
    set(undefined, nodeEnv);
    await withServer(async (base) => {
      assert.equal(await post(base), 200);
    });
  });
}

test("empty-string secret counts as unset", async () => {
  set("", "production");
  await withServer(async (base) => {
    assert.equal(await post(base, ""), 503);
  });
});
