// Guard: the Google Fonts CDN stylesheet must not sit on the HTML critical
// path. It was a Lighthouse "Eliminate render-blocking resources" hit
// (~770 ms wasted on live founderconsole.ai). Fonts are self-hosted.
import { existsSync, readFileSync } from "fs";
import assert from "assert";

const html = readFileSync("client/index.html", "utf8");
const fontsCss = readFileSync("client/src/styles/fonts.css", "utf8");
const indexCss = readFileSync("client/src/index.css", "utf8");

assert.doesNotMatch(
  html,
  /fonts\.googleapis\.com/,
  "client/index.html must not load Google Fonts CSS (render-blocking)",
);
assert.doesNotMatch(
  html,
  /fonts\.gstatic\.com/,
  "client/index.html must not preconnect to fonts.gstatic.com",
);

assert.match(
  indexCss,
  /@import\s+['"]\.\/styles\/fonts\.css['"]/,
  "app CSS must import the self-hosted font faces",
);

for (const family of ["Inter", "Bricolage Grotesque", "IBM Plex Mono"]) {
  assert.match(
    fontsCss,
    new RegExp(`font-family:\\s*"${family}"`),
    `fonts.css must declare ${family} so existing CSS variables keep matching`,
  );
}
assert.match(
  fontsCss,
  /font-display:\s*swap/,
  "self-hosted faces must use font-display: swap (do not block first paint)",
);

if (existsSync("dist/public/index.html")) {
  const built = readFileSync("dist/public/index.html", "utf8");
  assert.doesNotMatch(
    built,
    /fonts\.googleapis\.com/,
    "built dist/public/index.html must not contain Google Fonts CSS",
  );
  assert.doesNotMatch(
    built,
    /fonts\.gstatic\.com/,
    "built dist/public/index.html must not preconnect to fonts.gstatic.com",
  );
}

console.log("PASS  no render-blocking Google Fonts stylesheet on the HTML path");
