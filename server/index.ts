import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { spawn, execSync, spawnSync, ChildProcess } from "child_process";
import { createProxyMiddleware } from "http-proxy-middleware";
import { setupWebSocketServer } from "./websocket";
import { registerTwilioRoutes } from "./twilio/routes";
import { existsSync } from "fs";
import path from "path";

const app = express();
const httpServer = createServer(app);

let setupComplete = false;

app.use((req, res, next) => {
  if (req.path === "/health" || req.path === "/__repl") {
    if (setupComplete) return next();
    return res.status(200).json({ ok: true, status: "starting", fastapi: "starting" });
  }
  if (req.path === "/" && req.method === "GET" && !setupComplete) {
    return res.status(200).send(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>FounderConsole</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a0a0a;color:#e5e7eb;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh}.loader{text-align:center}.spinner{width:40px;height:40px;border:3px solid #333;border-top-color:#6366f1;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 16px}@keyframes spin{to{transform:rotate(360deg)}}p{font-size:14px;opacity:0.7}</style></head><body><div class="loader"><div class="spinner"></div><p>Loading FounderConsole...</p></div></body></html>`);
  }
  if (setupComplete) return next();
  if (req.method === "GET" && !req.path.startsWith("/api")) {
    return res.status(200).send(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>FounderConsole</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a0a0a;color:#e5e7eb;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh}.loader{text-align:center}.spinner{width:40px;height:40px;border:3px solid #333;border-top-color:#6366f1;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 16px}@keyframes spin{to{transform:rotate(360deg)}}p{font-size:14px;opacity:0.7}</style></head><body><div class="loader"><div class="spinner"></div><p>Loading FounderConsole...</p></div></body></html>`);
  }
  next();
});

const requestedPort = parseInt(process.env.PORT || "5000", 10);
const maxPortAttempts = Math.max(parseInt(process.env.PORT_RETRY_ATTEMPTS || "10", 10), 1);

function getListenOptions(port: number): Record<string, string | number | boolean> {
  const options: Record<string, string | number | boolean> = { port, host: "0.0.0.0" };
  if (process.platform === "linux") {
    options.reusePort = true;
  }
  return options;
}

function startHttpServerWithPortFallback(startPort: number): void {
  let attempt = 0;

  const tryPort = (candidatePort: number) => {
    const onListening = () => {
      httpServer.off("error", onError);
      httpServer.off("listening", onListening);

      const address = httpServer.address();
      const boundPort =
        address && typeof address === "object" && "port" in address
          ? address.port
          : candidatePort;

      process.env.PORT = String(boundPort);
      console.log(`[startup] Port ${boundPort} open and accepting connections`);
      if (boundPort !== startPort) {
        console.log(`[startup] Requested port ${startPort} unavailable; running on ${boundPort}`);
      }
    };

    const onError = (err: NodeJS.ErrnoException) => {
      httpServer.off("error", onError);
      httpServer.off("listening", onListening);
      if (err.code === "EADDRINUSE" && attempt + 1 < maxPortAttempts) {
        attempt += 1;
        const nextPort = candidatePort + 1;
        console.warn(`[startup] Port ${candidatePort} is in use, retrying on ${nextPort}`);
        tryPort(nextPort);
        return;
      }

      console.error(`[startup] Failed to open port ${candidatePort}: ${err.message}`);
      process.exit(1);
    };

    httpServer.once("error", onError);
    httpServer.once("listening", onListening);
    httpServer.listen(getListenOptions(candidatePort));
  };

  tryPort(startPort);
}

startHttpServerWithPortFallback(requestedPort);

// Initialize WebSocket server for real-time updates
const wss = setupWebSocketServer(httpServer);

// Global state for graceful shutdown and supervision
let fastapiProcess: ChildProcess | null = null;
let shuttingDown = false;
let restartCount = 0;
const MAX_RESTARTS = 10;
const RESTART_DELAYS = [2000, 3000, 5000, 8000, 12000]; // Exponential backoff
let fastapiStatus: "starting" | "up" | "down" | "restarting" = "starting";

function killProcessOnPort(port: string): void {
  const commands = [
    `fuser -k ${port}/tcp 2>/dev/null || true`,
    `lsof -ti:${port} 2>/dev/null | xargs -r kill -9 2>/dev/null || true`,
  ];
  for (const cmd of commands) {
    try {
      const result = execSync(cmd, { encoding: "utf-8", timeout: 3000 }).trim();
      if (result) {
        console.log(`[fastapi] Port cleanup (${cmd.split(" ")[0]}): ${result}`);
      }
    } catch {
      // Command not available, try next
    }
  }
  try { execSync("sleep 1"); } catch {}
}

function getFastAPIPort(): string {
  if (process.env.FASTAPI_PORT) return process.env.FASTAPI_PORT;
  return "8001";
}

function resolvePythonCommand(): string {
  const candidates = [
    process.env.PYTHON_BIN,
    path.join(process.cwd(), ".venv313", "bin", "python"),
    path.join(process.cwd(), ".venv", "bin", "python"),
    "python3",
    "python",
  ].filter((candidate): candidate is string => Boolean(candidate));

  for (const candidate of candidates) {
    if (candidate.includes("/")) {
      if (existsSync(candidate)) {
        return candidate;
      }
      continue;
    }

    const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (probe.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    "No Python runtime found. Set PYTHON_BIN or install python3/virtualenv dependencies."
  );
}

function startFastAPIServer(): ChildProcess {
  const port = getFastAPIPort();
  const pythonCommand = resolvePythonCommand();
  
  killProcessOnPort(port);
  
  const cmd = [pythonCommand, "-u", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", port];
  
  console.log(`[fastapi] Starting uvicorn: ${cmd.join(" ")}`);
  
  const nodeEnv = process.env.NODE_ENV || process.env.ENVIRONMENT || "development";
  const childEnv = { ...process.env, NODE_ENV: nodeEnv, PYTHONUNBUFFERED: "1" };
  if (!process.env.ENVIRONMENT) {
    childEnv.ENVIRONMENT = nodeEnv;
  }
  const child = spawn(pythonCommand, ["-u", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", port], {
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
    detached: process.platform !== "win32",
    env: childEnv,
  });
  
  if (child.stdout) {
    child.stdout.on("data", (data: Buffer) => {
      const lines = data.toString().trim().split("\n");
      for (const line of lines) {
        if (line) console.log(`[fastapi:out] ${line}`);
      }
    });
  }
  if (child.stderr) {
    child.stderr.on("data", (data: Buffer) => {
      const lines = data.toString().trim().split("\n");
      for (const line of lines) {
        if (line) console.error(`[fastapi:err] ${line}`);
      }
    });
  }
  
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
    const url = process.env.FASTAPI_URL || `http://localhost:${getFastAPIPort()}`;
    const response = await fetch(`${url}/health`, { 
      signal: AbortSignal.timeout(2000) 
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForFastAPI(maxRetries = 120, retryDelay = 2000): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    if (shuttingDown) return false;
    const isUp = await probeFastAPI();
    if (isUp) {
      console.log("[fastapi] Server is ready");
      fastapiStatus = "up";
      restartCount = 0;
      return true;
    }
    if (i % 10 === 0 || i < 5) {
      console.log(`[fastapi] Waiting... (${i + 1}/${maxRetries})`);
    }
    await new Promise(resolve => setTimeout(resolve, retryDelay));
  }
  console.error("[fastapi] Server not ready after primary wait, continuing background polling...");
  fastapiStatus = "starting";
  backgroundPollFastAPI();
  return false;
}

function backgroundPollFastAPI() {
  const poll = async () => {
    while (!shuttingDown && fastapiStatus !== "up") {
      const isUp = await probeFastAPI();
      if (isUp) {
        console.log("[fastapi] Server is ready (background poll)");
        fastapiStatus = "up";
        restartCount = 0;
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  };
  poll().catch(err => console.error("[fastapi] Background poll error:", err));
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
process.on("SIGHUP", () => {
  console.log("[SIGHUP] Received SIGHUP - ignoring (let workflow manager handle restart)");
});

fastapiProcess = startFastAPIServer();

const FASTAPI_URL = process.env.FASTAPI_URL || `http://localhost:${getFastAPIPort()}`;
const startTime = Date.now();

// Node health endpoint - always returns 200 immediately
app.get("/health", (_req: Request, res: Response) => {
  const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
  
  res.status(200).json({
    ok: true,
    fastapi: fastapiStatus === "up" ? "up" : "starting",
    fastapi_status: fastapiStatus,
    uptime_seconds: uptimeSeconds,
    version: "1.0.0",
    environment: process.env.NODE_ENV || "development"
  });
});

// Register Twilio messaging routes before the API proxy
const messagingRouter = express.Router();
messagingRouter.use(express.json());
registerTwilioRoutes(messagingRouter);
app.use("/api/messaging", messagingRouter);

// Register Notion routes before the API proxy (handled by Express, not FastAPI)
import { getNotionClient, listPages, listDatabases } from "./notion/client";
app.get("/api/notion/pages", async (req, res) => {
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

app.post("/api/notion/push-report", express.json(), async (req, res) => {
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

app.get("/api/notion/databases", async (req, res) => {
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

const apiProxy = createProxyMiddleware({
  target: FASTAPI_URL,
  changeOrigin: true,
  timeout: 120000,
  proxyTimeout: 120000,
  pathRewrite: {
    "^/api": "",
  },
  on: {
    error: (err: Error, req, res) => {
      console.error("Proxy error:", err.message);
      if ('writeHead' in res && typeof res.writeHead === 'function') {
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          error: "Backend service unavailable",
          detail: "Our servers are warming up — this usually takes 2-3 minutes after a deployment. Please refresh and try again shortly.",
          status: 502,
          fastapi_status: fastapiStatus,
        }));
      }
    },
  },
});

const LOCAL_API_PREFIXES = ["/ai/", "/notion/", "/messaging/"];
app.use("/api", (req, res, next) => {
  if (LOCAL_API_PREFIXES.some((prefix) => req.path.startsWith(prefix))) {
    return next();
  }
  return apiProxy(req, res, next);
});

app.use(
  "/notifications",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    timeout: 30000,
    proxyTimeout: 30000,
    pathRewrite: (path) => `/notifications${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Notifications proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Notifications service unavailable", detail: "Internal proxy error" }));
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
    timeout: 30000,
    proxyTimeout: 30000,
    pathRewrite: (path) => `/email-tracking${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Email tracking proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Email tracking service unavailable", detail: "Internal proxy error" }));
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
      // Response body logging removed for security

      log(logLine);
    }
  });

  next();
});

(async () => {
  await registerRoutes(httpServer, app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    console.error(`[error] ${status} ${message}`, err.stack || err);
  });

  if (process.env.NODE_ENV === "production") {
    try {
      serveStatic(app);
      console.log("[startup] Static file serving configured");
    } catch (err: any) {
      console.error(`[startup] Static serving failed: ${err.message}`);
      app.use("*", (_req, res) => {
        res.status(200).send(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>FounderConsole</title></head><body style="background:#0a0a0a;color:#e5e7eb;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh"><p>FounderConsole is starting up. Please refresh in a moment.</p></body></html>`);
      });
    }
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  setupComplete = true;
  console.log("[startup] Application setup complete");

  waitForFastAPI(600, 2000).then((ready) => {
    if (ready) {
      log("FastAPI backend is ready");
    } else {
      log("FastAPI backend not ready yet - API requests will be proxied when available");
    }
  });
})();
