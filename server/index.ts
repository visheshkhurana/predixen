import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { spawn, ChildProcess } from "child_process";
import { createProxyMiddleware } from "http-proxy-middleware";
import { setupWebSocketServer } from "./websocket";

const app = express();
const httpServer = createServer(app);

// Initialize WebSocket server for real-time updates
const wss = setupWebSocketServer(httpServer);

// Global state for graceful shutdown and supervision
let fastapiProcess: ChildProcess | null = null;
let shuttingDown = false;
let restartCount = 0;
const MAX_RESTARTS = 5;
const RESTART_DELAYS = [1000, 2000, 4000, 8000, 16000]; // Exponential backoff
let fastapiStatus: "starting" | "up" | "down" | "restarting" = "starting";

function startFastAPIServer(): ChildProcess {
  const port = process.env.FASTAPI_PORT || "8001";
  const cmd = ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", port];
  
  console.log(`[fastapi] Starting uvicorn: ${cmd.join(" ")}`);
  
  const child = spawn("python", ["-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", port], {
    stdio: "inherit",
    shell: true,
    detached: process.platform !== "win32", // Use process group on Unix
  });
  
  console.log(`[fastapi] Spawned with PID: ${child.pid}`);
  fastapiStatus = "starting";
  
  child.on("error", (err) => {
    console.error("[fastapi] Failed to start:", err);
    fastapiStatus = "down";
  });
  
  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      console.log(`[fastapi] Exited during shutdown (code: ${code}, signal: ${signal})`);
      return;
    }
    
    fastapiStatus = "down";
    
    if (code !== 0 && code !== null) {
      console.error(`[fastapi] Exited unexpectedly with code ${code}`);
      
      // Attempt restart with exponential backoff
      if (restartCount < MAX_RESTARTS) {
        const delay = RESTART_DELAYS[Math.min(restartCount, RESTART_DELAYS.length - 1)];
        restartCount++;
        console.log(`[fastapi] Restarting in ${delay}ms (attempt ${restartCount}/${MAX_RESTARTS})...`);
        fastapiStatus = "restarting";
        
        setTimeout(() => {
          if (!shuttingDown) {
            fastapiProcess = startFastAPIServer();
          }
        }, delay);
      } else {
        console.error(`[fastapi] Max restart attempts (${MAX_RESTARTS}) reached. Giving up.`);
      }
    }
  });
  
  return child;
}

async function probeFastAPI(): Promise<boolean> {
  try {
    const url = process.env.FASTAPI_URL || "http://localhost:8001";
    const response = await fetch(`${url}/health`, { 
      signal: AbortSignal.timeout(2000) 
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForFastAPI(maxRetries = 30, retryDelay = 1000): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    const isUp = await probeFastAPI();
    if (isUp) {
      console.log("[fastapi] Server is ready");
      fastapiStatus = "up";
      restartCount = 0; // Reset restart counter on successful start
      return true;
    }
    console.log(`[fastapi] Waiting... (${i + 1}/${maxRetries})`);
    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }
  console.error("[fastapi] Server failed to start within timeout");
  fastapiStatus = "down";
  return false;
}

// Graceful shutdown handler
async function gracefulShutdown(signal: string) {
  if (shuttingDown) return;
  shuttingDown = true;
  
  console.log(`\n[shutdown] Received ${signal}, shutting down gracefully...`);
  
  // Stop accepting new connections
  httpServer.close(() => {
    console.log("[shutdown] HTTP server closed");
  });
  
  // Terminate FastAPI process
  if (fastapiProcess && fastapiProcess.pid) {
    console.log(`[shutdown] Terminating FastAPI (PID: ${fastapiProcess.pid})...`);
    
    try {
      // On Unix, kill the process group
      if (process.platform !== "win32") {
        process.kill(-fastapiProcess.pid, "SIGTERM");
      } else {
        fastapiProcess.kill("SIGTERM");
      }
      
      // Wait up to 5 seconds for graceful shutdown
      const killTimeout = setTimeout(() => {
        console.log("[shutdown] FastAPI did not exit in time, sending SIGKILL...");
        try {
          if (process.platform !== "win32" && fastapiProcess?.pid) {
            process.kill(-fastapiProcess.pid, "SIGKILL");
          } else {
            fastapiProcess?.kill("SIGKILL");
          }
        } catch (e) {
          // Process may have already exited
        }
      }, 5000);
      
      fastapiProcess.on("exit", () => {
        clearTimeout(killTimeout);
        console.log("[shutdown] FastAPI terminated");
      });
    } catch (e) {
      console.error("[shutdown] Error terminating FastAPI:", e);
    }
  }
  
  // Give time for cleanup
  setTimeout(() => {
    console.log("[shutdown] Exiting process");
    process.exit(0);
  }, 6000);
}

// Register signal handlers
process.on("SIGINT", () => gracefulShutdown("SIGINT"));
process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGHUP", () => gracefulShutdown("SIGHUP"));

fastapiProcess = startFastAPIServer();

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8001";
const startTime = Date.now();

// Node health endpoint - returns status of both Node and FastAPI
app.get("/health", async (_req: Request, res: Response) => {
  const fastApiUp = await probeFastAPI();
  const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
  
  res.json({
    ok: true,
    fastapi: fastApiUp ? "up" : "down",
    fastapi_status: fastapiStatus,
    uptime_seconds: uptimeSeconds,
    version: "1.0.0",
    environment: process.env.NODE_ENV || "development"
  });
});

app.use(
  "/api",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    pathRewrite: {
      "^/api": "",
    },
    on: {
      error: (err: Error, req, res) => {
        console.error("Proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Backend service unavailable", detail: err.message }));
        }
      },
    },
  })
);

app.use(
  "/notifications",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    pathRewrite: (path) => `/notifications${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Notifications proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Notifications service unavailable", detail: err.message }));
        }
      },
    },
  })
);

// Proxy email-tracking routes (pixel, click, webhook, analytics) to FastAPI
app.use(
  "/email-tracking",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    pathRewrite: (path) => `/email-tracking${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Email tracking proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Email tracking service unavailable", detail: err.message }));
        }
      },
    },
  })
);


declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

app.use(
  express.json({
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false }));

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  // Wait for FastAPI to be ready before serving requests
  await waitForFastAPI();
  
  await registerRoutes(httpServer, app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (process.env.NODE_ENV === "production") {
    serveStatic(app);
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      log(`serving on port ${port}`);
    },
  );
})();
