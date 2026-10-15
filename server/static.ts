import express, { type Express } from "express";
import fs from "fs";
import path from "path";
import { injectSEO, injectNotFoundShell, isNotFoundPath } from "./seo-prerender";
import { isKnownAppRoute } from "./known-routes";

export type ShellDecision =
  | { status: 200; html: string }
  | { status: 404; html: string };

/**
 * HAG-162. What the catch-all should answer for a path that is not a file.
 *
 * Exported and pure so `server/tests/unknown-routes-404.test.ts` can drive it
 * without a listening server.
 */
export function decideShellResponse(indexHtml: string, pathname: string): ShellDecision {
  // 1. A page the prerenderer knows is missing -- an unknown /blog/ slug or an
  //    unknown /runway/ vertical. Those metas already carried
  //    `noindex, follow` and a "Page not found" title; only the status was
  //    wrong, which is what made them soft 404s.
  if (isNotFoundPath(pathname)) {
    return { status: 404, html: injectSEO(indexHtml, pathname) };
  }
  // 2. A path the client router has no route for. React Router's catch-all
  //    (`<Route component={NotFound} />`, client/src/App.tsx:600) already
  //    rendered the not-found page, so the body was right and the 200 was not.
  //    `injectSEO` is deliberately NOT used here: with no `getPageMeta` entry
  //    it returns the shell untouched, which is the homepage with the
  //    homepage's canonical and `index, follow`.
  if (!isKnownAppRoute(pathname)) {
    return { status: 404, html: injectNotFoundShell(indexHtml, pathname) };
  }
  return { status: 200, html: injectSEO(indexHtml, pathname) };
}

/**
 * The pathname the router will see, so the allowlist agrees with it.
 *
 * A browser resolves `%20` before React Router reads `location.pathname`, and
 * `/pricing/` and `/pricing` are the same route to it. Comparing the raw
 * request line against the route table would 404 URLs that render perfectly.
 */
function normalisePathname(rawPathname: string): string {
  let pathname = rawPathname;
  try {
    pathname = decodeURIComponent(rawPathname);
  } catch {
    // Malformed escape. Keep the raw form; it will simply not match a route.
  }
  pathname = pathname.replace(/\/{2,}/g, "/");
  if (pathname.length > 1) {
    pathname = pathname.replace(/\/+$/, "");
  }
  return pathname === "" ? "/" : pathname;
}

export function serveStatic(app: Express) {
  const distPath = path.resolve(__dirname, "public");
  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory: ${distPath}, make sure to build the client first`,
    );
  }

  const indexHtml = fs.readFileSync(path.resolve(distPath, "index.html"), "utf-8");

  app.use("/assets", express.static(path.join(distPath, "assets"), {
    maxAge: "1y",
    immutable: true,
  }));

  app.use(express.static(distPath, {
    maxAge: 0,
    // index: false is load-bearing. serve-static defaults to index: "index.html",
    // which means a request for "/" is answered here with the raw shell and never
    // reaches the catch-all below — so the homepage was the ONE page on the site
    // getting no injectSEO treatment: no server-rendered <h1>, no FAQ block, and
    // the generic meta that happens to match the shell's defaults. Every other
    // route (/pricing, /tools/runway-calculator, /blog/*) isn't a file on disk, so
    // it fell through and got prerendered correctly. That asymmetry is why "/"
    // served 4,753 bytes while /tools/runway-calculator served 5,468.
    index: false,
    setHeaders: (res, filePath) => {
      if (filePath.endsWith("index.html")) {
        res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
      }
    },
  }));

  app.use("*", (req, res) => {
    const url = req.originalUrl;
    const pathname = url.split("?")[0].split("#")[0];
    if (pathname === "/robots.txt" || pathname === "/sitemap.xml") {
      res.status(404).end();
      return;
    }
    // Missing hashed assets must 404. Falling through to the SPA shell made
    // deploy-landed's control probe (fake /assets/index-DEPLOYMONITOR-CONTROL-MISS.js)
    // always 200 HTML → perpetual control-failed email spam every ~10 min.
    if (pathname.startsWith("/assets/")) {
      res.status(404).type("text/plain").send("Not Found");
      return;
    }
    res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
    res.setHeader("Content-Type", "text/html");

    const decision = decideShellResponse(indexHtml, normalisePathname(pathname));
    res.status(decision.status).send(decision.html);
  });
}
