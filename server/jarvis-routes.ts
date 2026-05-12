import type { Express, Request, Response } from "express";
import crypto from "crypto";
import { ACTIONS, getActionNames, type ActionParams } from "./jarvis-actions";

interface RpcRequestBody {
  action?: unknown;
  params?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  try {
    return JSON.stringify(err);
  } catch {
    return String(err);
  }
}

export function registerJarvisRoutes(app: Express): void {
  app.get("/__jarvis/health", (_req: Request, res: Response) => {
    res.json({
      ok: true,
      workspace: "founderconsole",
      actions: getActionNames(),
      ts: new Date().toISOString(),
    });
  });

  app.post("/__jarvis/rpc", async (req: Request, res: Response) => {
    const expected = process.env.WORKSPACE_RPC_SECRET;
    if (!expected) {
      return res.status(500).json({
        ok: false,
        error: "WORKSPACE_RPC_SECRET not configured",
      });
    }

    const provided = req.header("x-jarvis-rpc-secret") ?? "";
    const expectedBuf = Buffer.from(expected, "utf8");
    const providedBuf = Buffer.from(provided, "utf8");
    if (
      expectedBuf.length !== providedBuf.length ||
      !crypto.timingSafeEqual(expectedBuf, providedBuf)
    ) {
      return res.status(401).json({ ok: false, error: "unauthorized" });
    }

    const body = (isRecord(req.body) ? req.body : {}) as RpcRequestBody;
    const action = typeof body.action === "string" ? body.action : "";
    const params: ActionParams = isRecord(body.params) ? body.params : {};

    if (!action) {
      return res.status(400).json({ ok: false, error: "action required" });
    }

    const handler = ACTIONS[action];
    if (!handler) {
      return res.status(404).json({
        ok: false,
        error: `unknown action: ${action}`,
        available: getActionNames(),
      });
    }

    try {
      const result = await handler(params);
      return res.json(result);
    } catch (err: unknown) {
      return res.json({ ok: false, error: getErrorMessage(err) });
    }
  });
}
