// Naive UTC timestamps from the API must not be read as local time.
import assert from "assert";
import { parseServerDate } from "../../client/src/lib/serverDate";

assert.equal(parseServerDate("2026-11-16T21:40:44").toISOString(), "2026-11-16T21:40:44.000Z");
assert.equal(parseServerDate("2026-11-16T21:40:44.000537").toISOString(), "2026-11-16T21:40:44.000Z");
assert.equal(parseServerDate("2026-11-16 21:40:44").toISOString(), "2026-11-16T21:40:44.000Z");
assert.equal(parseServerDate("2026-11-16T21:40:44Z").toISOString(), "2026-11-16T21:40:44.000Z");
assert.equal(parseServerDate("2026-11-17T03:10:44+05:30").toISOString(), "2026-11-16T21:40:44.000Z");
assert.equal(parseServerDate(0).getTime(), 0);
console.log("server-date: ok");
