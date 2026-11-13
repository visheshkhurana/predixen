/**
 * Server-rendered blog metadata and bodies come from the same module the
 * React pages and the sitemap generator read (`client/src/data/blog-posts.ts`).
 *
 * This file used to keep a second, hand-shortened copy. Posts added only to
 * the client list shipped in sitemap.xml and then prerendered as
 * "Article not found" + noindex. Re-exporting the client list is the shared
 * source: a new post cannot be in the sitemap and missing from SSR.
 */
export { blogPosts } from "../client/src/data/blog-posts";
