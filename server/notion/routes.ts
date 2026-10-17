// Notion routes (Express-handled). They use a single shared Notion connection,
// and push-report replaces a page's content, so only the platform owner may
// call them.
import express, { type Express } from "express";
import { getNotionClient, listPages, listDatabases } from "./client";
import { requirePlatformAdmin } from "../middleware/requireAuth";

export function registerNotionRoutes(app: Express): void {
  app.get("/api/notion/pages", requirePlatformAdmin, async (req, res) => {
    try {
      const pages = await listPages();
      const simplified = pages.map((p: any) => ({
        id: p.id,
        title: p.properties?.title?.title?.[0]?.plain_text
          || p.properties?.Name?.title?.[0]?.plain_text
          || "Untitled",
        url: p.url,
        created_time: p.created_time,
        last_edited_time: p.last_edited_time,
      }));
      res.json({ pages: simplified });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post("/api/notion/push-report", requirePlatformAdmin, express.json(), async (req, res) => {
    try {
      const notion = await getNotionClient();
      const { pageId } = req.body;
      if (!pageId) {
        return res.status(400).json({ error: "pageId is required" });
      }

      const fs = await import("fs");
      const path = await import("path");
      const reportPath = path.default.join(process.cwd(), "qa-lab/latest-report.md");
      const reportContent = fs.default.readFileSync(reportPath, "utf-8");

      const lines = reportContent.split("\n");

      const blocks: any[] = [];

      let inTable = false;
      let tableRows: string[][] = [];

      const flushTable = () => {
        if (tableRows.length > 0) {
          const header = tableRows[0];
          const dataRows = tableRows.slice(1);

          blocks.push({
            object: "block",
            type: "heading_3",
            heading_3: {
              rich_text: [{ type: "text", text: { content: header.join(" | ") } }],
            },
          });

          for (const row of dataRows) {
            const rowText = row.map((cell, i) => `${header[i]}: ${cell}`).join(" | ");
            blocks.push({
              object: "block",
              type: "paragraph",
              paragraph: {
                rich_text: [{ type: "text", text: { content: rowText.substring(0, 2000) } }],
              },
            });
          }
          tableRows = [];
        }
        inTable = false;
      }

      for (const line of lines) {
        const trimmed = line.trim();

        if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
          const cells = trimmed.split("|").filter(c => c.trim()).map(c => c.trim());
          if (cells.every(c => /^[-:]+$/.test(c))) {
            continue;
          }
          inTable = true;
          tableRows.push(cells);
          continue;
        }

        if (inTable) {
          flushTable();
        }

        if (trimmed === "") continue;

        if (trimmed.startsWith("# ")) {
          blocks.push({
            object: "block",
            type: "heading_1",
            heading_1: {
              rich_text: [{ type: "text", text: { content: trimmed.replace(/^# /, "") } }],
            },
          });
        } else if (trimmed.startsWith("## ")) {
          blocks.push({
            object: "block",
            type: "heading_2",
            heading_2: {
              rich_text: [{ type: "text", text: { content: trimmed.replace(/^## /, "") } }],
            },
          });
        } else if (trimmed.startsWith("### ")) {
          blocks.push({
            object: "block",
            type: "heading_3",
            heading_3: {
              rich_text: [{ type: "text", text: { content: trimmed.replace(/^### /, "") } }],
            },
          });
        } else if (trimmed.startsWith("- ")) {
          blocks.push({
            object: "block",
            type: "bulleted_list_item",
            bulleted_list_item: {
              rich_text: [{ type: "text", text: { content: trimmed.replace(/^- /, "").replace(/\*\*(.*?)\*\*/g, "$1") } }],
            },
          });
        } else if (trimmed.startsWith("**") || trimmed.startsWith("*")) {
          blocks.push({
            object: "block",
            type: "paragraph",
            paragraph: {
              rich_text: [{ type: "text", text: { content: trimmed.replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1") } }],
            },
          });
        } else if (trimmed === "---") {
          blocks.push({
            object: "block",
            type: "divider",
            divider: {},
          });
        } else {
          blocks.push({
            object: "block",
            type: "paragraph",
            paragraph: {
              rich_text: [{ type: "text", text: { content: trimmed.substring(0, 2000) } }],
            },
          });
        }
      }

      if (inTable) flushTable();

      const existingBlocks = await notion.blocks.children.list({ block_id: pageId, page_size: 100 });
      for (const block of existingBlocks.results) {
        try {
          await notion.blocks.delete({ block_id: (block as any).id });
        } catch (e) {}
      }

      const BATCH_SIZE = 100;
      for (let i = 0; i < blocks.length; i += BATCH_SIZE) {
        const batch = blocks.slice(i, i + BATCH_SIZE);
        await notion.blocks.children.append({
          block_id: pageId,
          children: batch,
        });
      }

      res.json({ success: true, blocksAdded: blocks.length });
    } catch (err: any) {
      console.error("Notion push error:", err);
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/notion/databases", requirePlatformAdmin, async (req, res) => {
    try {
      const dbs = await listDatabases();
      const simplified = dbs.map((d: any) => ({
        id: d.id,
        title: d.title?.[0]?.plain_text || "Untitled",
        url: d.url,
      }));
      res.json({ databases: simplified });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });
}
