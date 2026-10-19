// Request correlation id: mint one if the caller (or the proxy) did not.
//
// This lived inline in `server/index.ts` until it needed a test. Every other
// middleware in this directory is its own module, and an inline middleware
// cannot be exercised without booting the whole 928-line server with a database,
// so "the cap is 64" was a claim nothing could check. Moving it here is what
// makes `server/tests/request-id.test.ts` possible.
import type { Request, Response, NextFunction } from "express";
import { randomUUID } from "crypto";

/**
 * Longest client-supplied request id we will store.
 *
 * `x-request-id` is taken straight from the request, and it is then echoed in a
 * response header AND written into every log line. Unbounded, a raw socket
 * sending 5,000 characters turns one log line into a 5,159-byte one — and it can
 * do it on every request, from a single unauthenticated connection. Capping it
 * here fixes both sinks at once, because the logger reads the id back out of
 * `req.headers` rather than re-reading the socket.
 *
 * (Numbers measured on the built bundle, not estimated: a log line's fixed
 * overhead is 159 bytes, and the id is copied into it verbatim, so 159 + 5,000 =
 * 5,159. Verified at two id lengths — 10 chars gave 169 bytes, 64 chars gave
 * 223.)
 *
 * The same discipline `UA_ECHO_LIMIT` applies to the User-Agent in
 * `middleware/aiAgentLog.ts`: the fields a stranger controls are the ones that
 * need a ceiling, and the inconsistency was that only one of the two had one.
 * 64 is longer than a UUID and longer than the trace ids any tracing library
 * emits, so a real caller is unaffected.
 */
export const REQUEST_ID_LIMIT = 64;

export function requestId() {
  return (req: Request, res: Response, next: NextFunction): void => {
    // `String(...)` before `.slice(...)`: the header can be a string[] when it is
    // sent twice, and the previous `(req.headers[...] as string) || randomUUID()`
    // passed such an array straight through on the cast's say-so — the cast said
    // `string` and nothing checked. `?? ""` covers absent.
    const supplied = String(req.headers["x-request-id"] ?? "");
    const id = supplied.slice(0, REQUEST_ID_LIMIT) || randomUUID();
    req.headers["x-request-id"] = id;
    res.setHeader("X-Request-ID", id);
    next();
  };
}
