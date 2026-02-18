import type { Express, Request, Response, NextFunction } from "express";
import type { Server } from "http";
import { registerChatRoutes } from "./replit_integrations/chat";
import { broadcastMetricUpdate, broadcastSimulationUpdate, broadcastTruthScanUpdate, getConnectedClientsCount } from "./websocket";
import { registerAiGovernanceRoutes } from "./ai-governance/routes";

function requireInternalAuth(req: Request, res: Response, next: NextFunction) {
  const secret = process.env.INTERNAL_API_SECRET;
  if (!secret) {
    if (process.env.NODE_ENV !== "production") return next();
    return res.status(503).json({ error: "Internal routes not configured" });
  }
  const provided = req.headers["x-internal-secret"];
  if (provided !== secret) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  registerChatRoutes(app);
  registerAiGovernanceRoutes(app);

  app.post("/internal/broadcast/metrics", requireInternalAuth, (req: Request, res: Response) => {
    const { companyId, metrics, source } = req.body;
    if (!companyId || !metrics) {
      return res.status(400).json({ error: "Missing companyId or metrics" });
    }
    broadcastMetricUpdate(companyId, metrics, source || "api");
    res.json({ success: true, clients: getConnectedClientsCount() });
  });

  app.post("/internal/broadcast/simulation", requireInternalAuth, (req: Request, res: Response) => {
    const { scenarioId, status, progress, results } = req.body;
    if (!scenarioId || !status) {
      return res.status(400).json({ error: "Missing scenarioId or status" });
    }
    broadcastSimulationUpdate(scenarioId, status, progress, results);
    res.json({ success: true, clients: getConnectedClientsCount() });
  });

  app.post("/internal/broadcast/truth-scan", requireInternalAuth, (req: Request, res: Response) => {
    const { companyId, metrics, status } = req.body;
    if (!companyId) {
      return res.status(400).json({ error: "Missing companyId" });
    }
    broadcastTruthScanUpdate(companyId, metrics || {}, status || "updated");
    res.json({ success: true, clients: getConnectedClientsCount() });
  });

  app.get("/internal/ws/status", requireInternalAuth, (_req: Request, res: Response) => {
    res.json({ clients: getConnectedClientsCount() });
  });

  return httpServer;
}
