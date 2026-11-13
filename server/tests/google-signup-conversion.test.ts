// Google is the main signup path, but the OAuth callback fired no GA4 sign_up
// and no Meta CompleteRegistration, and the Google button dropped the
// first-touch campaign. The server now marks a brand-new account with new_user=1.
import assert from "assert";
import { readFileSync } from "fs";

const callback = readFileSync("client/src/pages/auth-callback.tsx", "utf8");
const auth = readFileSync("client/src/pages/auth.tsx", "utf8");
const oauth = readFileSync("server/api/oauth.py", "utf8");

assert.match(callback, /params\.get\('new_user'\) === '1'/, "callback reads the server's new-account flag");
const gated = callback.slice(callback.indexOf("if (isNewUser) {"));
assert.match(gated, /metaTrack\('CompleteRegistration'/, "Meta sees Google signups");
assert.match(gated, /trackFunnel\('sign_up'/, "GA4 sign_up fires for Google signups");
assert.match(gated, /trackFunnel\('signup_completed'/);
assert.match(auth, /readFirstTouchAttribution\(\)/, "Google button forwards first-touch UTMs");
assert.match(oauth, /new_user/, "server sets new_user on account creation");
assert.ok(!/= asyncio\.get_event_loop\(\)/.test(oauth), "no event-loop lookup in the sync OAuth route");

console.log("PASS  google-signup-conversion");
