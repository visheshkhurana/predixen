// Logout writes revoked_access_tokens / user_session_cutoffs. Express
// requireAuth must read them, or /api/ai/* stays valid until the JWT expires.
// Run: npx tsx --test server/tests/express-session-revocation.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import express from "express";
import type { Server } from "node:http";
import {
  requireAuth,
  setRevocationQueryForTests,
} from "../middleware/requireAuth";
import {
  isAccessTokenRevoked,
  type RevocationQuery,
} from "../middleware/sessionRevocation";

const SECRET = "express-revocation-test-secret";
process.env.SECRET_KEY = SECRET;
delete process.env.DATABASE_URL;

function signJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = crypto.createHmac("sha256", SECRET).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${sig}`;
}

function token(extra: Record<string, unknown> = {}): string {
  return signJwt({
    sub: "7",
    jti: "jti-live",
    iat: 1_700_000_000,
    exp: Math.floor(Date.now() / 1000) + 3600,
    ...extra,
  });
}

function queryFrom(rowsFor: (sql: string) => Array<Record<string, unknown>>): RevocationQuery {
  return async (sql) => ({ rows: rowsFor(sql) });
}

function start(): Promise<{ base: string; server: Server }> {
  const app = express();
  app.get("/api/ai/ping", requireAuth, (_req, res) => {
    res.json({ ok: true });
  });
  return new Promise((resolve) => {
    const server = app.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      resolve({ base: `http://127.0.0.1:${port}`, server });
    });
  });
}

test("a logged-out jti is revoked", async () => {
  const revoked = await isAccessTokenRevoked(
    { sub: "7", jti: "jti-logged-out", iat: 1_700_000_000 },
    queryFrom((sql) => (sql.includes("revoked_access_tokens") ? [{ revoked: 1 }] : [])),
  );
  assert.equal(revoked, true);
});

test("a token issued before the session cutoff is revoked", async () => {
  const revoked = await isAccessTokenRevoked(
    { sub: "7", jti: "jti-old", iat: 1_000 },
    queryFrom((sql) => (sql.includes("user_session_cutoffs") ? [{ cutoff: "2000" }] : [])),
  );
  assert.equal(revoked, true);
});

test("a token issued after the cutoff is still valid", async () => {
  const revoked = await isAccessTokenRevoked(
    { sub: "7", jti: "jti-new", iat: 3_000 },
    queryFrom((sql) => (sql.includes("user_session_cutoffs") ? [{ cutoff: 2000 }] : [])),
  );
  assert.equal(revoked, false);
});

test("a cutoff rejects a token that has no iat", async () => {
  const revoked = await isAccessTokenRevoked(
    { sub: "7", jti: "jti-no-iat" },
    queryFrom((sql) => (sql.includes("user_session_cutoffs") ? [{ cutoff: 2000 }] : [])),
  );
  assert.equal(revoked, true);
});

test("requireAuth rejects a revoked bearer and accepts a live one", async (t) => {
  const revokedJtis = new Set(["jti-logged-out"]);
  setRevocationQueryForTests(async (sql, params) => {
    if (sql.includes("revoked_access_tokens") && revokedJtis.has(String(params[0]))) {
      return { rows: [{ revoked: 1 }] };
    }
    if (sql.includes("user_session_cutoffs") && String(params[0]) === "9") {
      return { rows: [{ cutoff: 1_700_000_100 }] };
    }
    return { rows: [] };
  });

  const { base, server } = await start();
  t.after(() => {
    setRevocationQueryForTests(null);
    server.close();
  });

  const live = await fetch(base + "/api/ai/ping", {
    headers: { authorization: `Bearer ${token({ jti: "jti-live" })}` },
  });
  assert.equal(live.status, 200);

  const loggedOut = await fetch(base + "/api/ai/ping", {
    headers: { authorization: `Bearer ${token({ jti: "jti-logged-out" })}` },
  });
  assert.equal(loggedOut.status, 401);
  assert.match(await loggedOut.text(), /Session has ended/);

  const reset = await fetch(base + "/api/ai/ping", {
    headers: {
      authorization: `Bearer ${token({ sub: "9", jti: "jti-reset", iat: 1_700_000_000 })}`,
    },
  });
  assert.equal(reset.status, 401);

  const cookie = await fetch(base + "/api/ai/ping", {
    headers: { cookie: `auth_token=${token({ jti: "jti-logged-out" })}` },
  });
  assert.equal(cookie.status, 401);
});
