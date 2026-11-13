// Signed-in email must not be sent to Google Analytics.
// user_id on gtag('config', ...) stays; that privacy call is separate.
//
// Run: npx tsx --test server/tests/no-gtag-user-email.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

function walk(dir: string, acc: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === "dist") continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.(ts|tsx|js|jsx|html)$/.test(name)) acc.push(p);
  }
  return acc;
}

function gtagCallBodies(src: string): string[] {
  const bodies: string[] = [];
  const re = /gtag\s*\(/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(src))) {
    let i = match.index + match[0].length;
    let depth = 1;
    const start = i;
    while (i < src.length && depth > 0) {
      const ch = src[i];
      if (ch === "(") depth++;
      else if (ch === ")") depth--;
      i++;
    }
    bodies.push(src.slice(start, Math.max(start, i - 1)));
  }
  return bodies;
}

test("no source file passes user_email to gtag", () => {
  const offenders: string[] = [];
  for (const file of walk("client")) {
    const src = readFileSync(file, "utf8");
    for (const body of gtagCallBodies(src)) {
      if (/\buser_email\b/.test(body)) {
        offenders.push(file);
        break;
      }
    }
  }
  assert.deepEqual(offenders, []);
});
