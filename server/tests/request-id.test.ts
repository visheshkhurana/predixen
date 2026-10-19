// The `x-request-id` header is attacker-controlled input with two sinks.
//
// `server/index.ts` takes whatever the caller sends in `x-request-id`, echoes it
// back in a response header, and — because `middleware/aiAgentLog.ts` reads the
// id back out of `req.headers` — writes it into every AI-agent log line. Every
// other field in that log line is bounded: the path is a path, the method is one
// of a handful of verbs, and the User-Agent is capped at `UA_ECHO_LIMIT`. The id
// was not, so a single unauthenticated request carrying 5,000 characters
// inflates one log line to 5,159 bytes, repeatable on every connection. (Line
// overhead is 159 bytes, measured on the built bundle at two id lengths —
// 10 chars gave 169 bytes, 64 gave 223. The figures here were 167/5,164 when
// this file was written and could not be reproduced, so they were replaced.)
//
// Run: npx tsx --test server/tests/request-id.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "http";
import { requestId, REQUEST_ID_LIMIT } from "../middleware/requestId";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Boot the middleware on a bare app and return what the caller sees. */
async function roundTrip(
  headers: Record<string, string>,
): Promise<{ status: number; echoed: string | null; seenByHandler: string | undefined }> {
  const app = express();
  app.use(requestId());
  let seenByHandler: string | undefined;
  app.get("/", (req, res) => {
    // What `aiAgentLog.ts` would read when it logs. This is the sink that made
    // the missing cap a log-inflation bug rather than a cosmetic one.
    seenByHandler = req.headers["x-request-id"] as string | undefined;
    res.status(200).send("ok");
  });

  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  try {
    const port = (server.address() as any).port;
    const res = await fetch(`http://127.0.0.1:${port}/`, { headers });
    return { status: res.status, echoed: res.headers.get("x-request-id"), seenByHandler };
  } finally {
    server.close();
  }
}

test("a caller-supplied id is echoed back unchanged when it is short", async () => {
  const { status, echoed, seenByHandler } = await roundTrip({ "x-request-id": "abc-123" });
  assert.equal(status, 200);
  assert.equal(echoed, "abc-123", "a normal caller's id must survive untouched");
  assert.equal(seenByHandler, "abc-123");
});

test("an absent id is minted as a UUID", async () => {
  const { echoed, seenByHandler } = await roundTrip({});
  assert.ok(echoed, "no id was set on the response");
  assert.match(echoed, UUID_RE, "a minted id must be a UUID");
  assert.equal(seenByHandler, echoed, "the handler and the client must see the same id");
});

test("a 5,000-character id is capped, in BOTH sinks", async () => {
  // The regression this exists for. `seenByHandler` is asserted separately from
  // `echoed` on purpose: the response header is the visible sink, but the log
  // line is the one that actually grew, and a fix that only trimmed the header
  // would leave the log inflatable while looking correct here.
  const { echoed, seenByHandler } = await roundTrip({ "x-request-id": "A".repeat(5000) });
  assert.equal(echoed?.length, REQUEST_ID_LIMIT, "the echoed header was not capped");
  assert.equal(seenByHandler?.length, REQUEST_ID_LIMIT, "the value the logger reads was not capped");
  assert.equal(echoed, "A".repeat(REQUEST_ID_LIMIT));
});

test("an array-valued header is coerced to a string, not passed through", async () => {
  // Called directly rather than over HTTP, and the reason is worth recording:
  // Node JOINS duplicate headers into one comma-separated string, so a real
  // request never delivers an array here and an HTTP round-trip would pass
  // whether or not the middleware handles one. (This test was written as a
  // round-trip first and did exactly that — passed under the old cast that it
  // was supposed to catch.) The branch is still live: the old code cast the
  // value to `string` and used it as-is, so a cast nothing had checked. This
  // asserts the contract directly.
  const req = {
    headers: { "x-request-id": ["first", "second"] } as Record<string, unknown>,
  };
  const set: Record<string, string> = {};
  const res = { setHeader: (k: string, v: string) => { set[k] = v; } };
  let called = false;

  requestId()(req as any, res as any, () => { called = true; });

  assert.ok(called, "the middleware must call next()");
  assert.equal(
    typeof req.headers["x-request-id"],
    "string",
    `the id must always be a string, got ${typeof req.headers["x-request-id"]}`,
  );
  assert.equal(
    set["X-Request-ID"],
    "first,second",
    "an array header must be coerced to a single string",
  );
});

test("an empty id is treated as absent, not as a valid empty id", async () => {
  // An empty response header is worse than none: a client correlating logs on
  // `X-Request-ID: ""` gets every request that sent an empty value.
  const { echoed } = await roundTrip({ "x-request-id": "" });
  assert.match(String(echoed), UUID_RE, "an empty id must be replaced with a minted one");
});
