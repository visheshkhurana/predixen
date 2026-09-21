// Guard: posthog-js must not be a static import on the entry path.
// A Vite production build inlined it into index-*.js (~240KB) because
// client/src/lib/posthog.ts used `import posthog from 'posthog-js'`.
// Call sites go through that module's public API only.
import assert from "assert";
import { existsSync, readdirSync, readFileSync, statSync } from "fs";
import { join } from "path";

const posthogLib = readFileSync("client/src/lib/posthog.ts", "utf8");
const app = readFileSync("client/src/App.tsx", "utf8");
const funnel = readFileSync("client/src/lib/funnel.ts", "utf8");
const main = readFileSync("client/src/main.tsx", "utf8");
const indexHtml = readFileSync("client/index.html", "utf8");

assert.doesNotMatch(
  posthogLib,
  /^import\s+posthog\s+from\s+['"]posthog-js['"]/m,
  "client/src/lib/posthog.ts must not statically import posthog-js",
);
assert.match(
  posthogLib,
  /import\(\s*["']posthog-js["']\s*\)/,
  "posthog-js must be loaded via import() so Vite splits it out of the entry",
);

for (const [name, src] of [
  ["client/src/App.tsx", app],
  ["client/src/lib/funnel.ts", funnel],
  ["client/src/main.tsx", main],
] as const) {
  assert.doesNotMatch(
    src,
    /from\s+['"]posthog-js['"]/,
    `${name} must not import posthog-js (public API is @/lib/posthog)`,
  );
  assert.doesNotMatch(
    src,
    /import\(\s*['"]posthog-js['"]\s*\)/,
    `${name} must not dynamic-import posthog-js (single loader in posthog.ts)`,
  );
}

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.(ts|tsx|js|html)$/.test(name)) acc.push(p);
  }
  return acc;
}

for (const p of walk("client/src")) {
  if (p.endsWith("lib/posthog.ts") || p.endsWith("lib/posthog-queue.ts")) continue;
  const src = readFileSync(p, "utf8");
  assert.doesNotMatch(
    src,
    /from\s+['"]posthog-js['"]/,
    `${p} must not statically import posthog-js`,
  );
}

const billing = readFileSync("client/src/pages/billing.tsx", "utf8");
assert.doesNotMatch(
  billing,
  /window.*posthog/,
  "billing checkout success must go through trackEvent so it queues before init",
);
assert.match(billing, /trackEvent\(\s*['"]purchase_subscription['"]/);
assert.doesNotMatch(indexHtml, /<script[^>]+array\.js/i, "no second inline PostHog snippet");
assert.doesNotMatch(indexHtml, /<script[^>]+posthog/i, "no second inline PostHog snippet");
assert.doesNotMatch(indexHtml, /cdn\.posthog/, "no second inline PostHog snippet");

if (existsSync("dist/public/index.html")) {
  const built = readFileSync("dist/public/index.html", "utf8");
  const m = built.match(/src="(\/assets\/index-[^"]+\.js)"/);
  assert.ok(m, "production index.html must reference an entry module");
  const entryName = m[1].slice("/assets/".length);
  const entry = readFileSync(join("dist/public/assets", entryName), "utf8");
  assert.doesNotMatch(
    entry,
    /PostHogPersistence/,
    "posthog-js SDK must not be inlined in the entry chunk",
  );
  const assets = readdirSync("dist/public/assets").filter((f) => f.endsWith(".js"));
  const sdkChunk = assets.find((f) => {
    if (f === entryName) return false;
    return readFileSync(join("dist/public/assets", f), "utf8").includes("PostHogPersistence");
  });
  assert.ok(sdkChunk, "posthog-js must land in its own lazy chunk, not the entry");
  console.log(`PASS  posthog-js deferred to ${sdkChunk}`);
} else {
  console.log("PASS  posthog-js is not statically imported on the entry path (dist not built)");
}
