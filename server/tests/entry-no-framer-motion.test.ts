// Guard: framer-motion must not be a static import on the entry path.
// A Vite production build (see PR) put ~331KB of it into index-*.js because
// App.tsx imported AnimatePresence and DashboardBackground imported
// useReducedMotion — paid for by signup → onboarding → first insight.
import { readFileSync } from "fs";
import assert from "assert";

const app = readFileSync("client/src/App.tsx", "utf8");
const background = readFileSync("client/src/components/DashboardBackground.tsx", "utf8");
const main = readFileSync("client/src/main.tsx", "utf8");

for (const [name, src] of [
  ["client/src/App.tsx", app],
  ["client/src/components/DashboardBackground.tsx", background],
  ["client/src/main.tsx", main],
] as const) {
  assert.doesNotMatch(
    src,
    /from\s+["']framer-motion["']/,
    `${name} must not statically import framer-motion (entry-bundle leak)`,
  );
}

assert.match(
  app,
  /className="fc-route-enter"/,
  "authenticated route wrapper must use the CSS enter class, not AnimatePresence",
);

assert.match(
  background,
  /fc-drift1/,
  "DashboardBackground must keep the CSS drift class (reduced-motion is in CSS)",
);

console.log("PASS  entry path does not statically import framer-motion");
