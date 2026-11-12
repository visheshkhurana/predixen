// Notion routes use the platform workspace's integration, so only the platform owner may call them.
// Run: npx tsx --test server/tests/notion-admin-gate.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const src = readFileSync(path.join(process.cwd(), "server/index.ts"), "utf8");

test("every /api/notion route is gated by the platform-admin check", () => {
  const routes = [...src.matchAll(/app\.(get|post|put|patch|delete|use)\(\s*"(\/api\/notion[^"]*)"\s*,\s*([A-Za-z]+)/g)];
  assert.ok(routes.length >= 3, "expected the Notion routes to be found");
  for (const [, , route, guard] of routes) {
    assert.equal(guard, "requireNotionAdmin", `${route} must use the platform-admin gate`);
  }
  assert.match(src, /import \{ requirePlatformAdmin as requireNotionAdmin \} from "\.\/middleware\/requireAuth";/);
});
