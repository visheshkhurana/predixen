import type { Express } from "express";
import type { Server } from "http";
import { registerChatRoutes } from "./replit_integrations/chat";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  registerChatRoutes(app);
  return httpServer;
}
