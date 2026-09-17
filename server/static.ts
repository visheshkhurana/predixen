import express, { type Express } from "express";
import fs from "fs";
import path from "path";
import { injectSEO } from "./seo-prerender";

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

    const enrichedHtml = injectSEO(indexHtml, pathname);
    res.send(enrichedHtml);
  });
}
