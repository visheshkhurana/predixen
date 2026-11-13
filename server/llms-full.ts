import type { Express } from "express";
import fs from "fs";
import path from "path";
import { blogPosts } from "./seo-data";

/**
 * /llms-full.txt: llms.txt followed by the full text of every blog post, as
 * markdown, for language models and AI answer engines that prefer one plain
 * document to crawling 20+ HTML pages.
 *
 * Generated per request from the same `blogPosts` list the blog, the prerender
 * and the sitemap read, so a new post appears here with no second edit and a
 * removed post disappears. llms.txt itself is read from disk (dist/public in
 * production, client/public in development), so its pinned facts stay in one
 * file (server/tests/test_published_facts_1019.py guards them).
 */

const SITE_URL = "https://founderconsole.ai";

/** Turns the blog's inline markdown into plain markdown with absolute links. */
function absolutiseLinks(text: string): string {
  return text.replace(/\]\((\/[^)]*)\)/g, (_m, href) => `](${SITE_URL}${href})`);
}

export function buildLlmsFull(llmsTxt: string): string {
  const posts = blogPosts.map((p) => {
    const body = (p.content || []).map((para) => absolutiseLinks(para)).join("\n\n");
    return [
      `## ${p.title}`,
      "",
      `URL: ${SITE_URL}/blog/${p.slug}`,
      `Published: ${p.date} | Author: ${p.author}, ${p.authorRole} | Category: ${p.category}`,
      "",
      `> ${p.excerpt}`,
      "",
      body.replace(/^## /gm, "### "),
    ].join("\n");
  });
  return [
    llmsTxt.trimEnd(),
    "",
    "---",
    "",
    "# Full text of FounderConsole blog posts",
    "",
    `${blogPosts.length} posts. Each is also published as HTML at the URL shown.`,
    "",
    posts.join("\n\n---\n\n"),
    "",
  ].join("\n");
}

function readLlmsTxt(): string | null {
  // __dirname exists in the esbuild CJS bundle (dist/index.cjs) but not under tsx's ESM
  // loader in development, so it is optional here.
  const here = typeof __dirname === "string" ? [path.resolve(__dirname, "public", "llms.txt")] : [];
  const candidates = [
    ...here,
    path.resolve(process.cwd(), "dist", "public", "llms.txt"),
    path.resolve(process.cwd(), "client", "public", "llms.txt"),
  ];
  for (const file of candidates) {
    try {
      return fs.readFileSync(file, "utf-8");
    } catch {
      // try the next location
    }
  }
  return null;
}

export function registerLlmsFull(app: Express): void {
  app.get("/llms-full.txt", (_req, res) => {
    const llms = readLlmsTxt();
    if (llms === null) {
      res.status(404).type("text/plain").send("Not Found");
      return;
    }
    res.setHeader("Cache-Control", "public, max-age=3600");
    res.type("text/plain; charset=utf-8").send(buildLlmsFull(llms));
  });
}
