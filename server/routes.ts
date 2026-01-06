import type { Express } from "express";
import { createServer, type Server } from "http";
import { createProxyMiddleware } from "http-proxy-middleware";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8001";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  app.use(
    "/api",
    createProxyMiddleware({
      target: FASTAPI_URL,
      changeOrigin: true,
      pathRewrite: {
        "^/api": "",
      },
      onError: (err, req, res) => {
        console.error("Proxy error:", err.message);
        if (res.writeHead) {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Backend service unavailable", detail: err.message }));
        }
      },
      logLevel: "warn",
    })
  );

  return httpServer;
}
