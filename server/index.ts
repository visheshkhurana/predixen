import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { registerJarvisRoutes } from "./jarvis-routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { spawn, execSync, spawnSync, ChildProcess } from "child_process";
import { createProxyMiddleware } from "http-proxy-middleware";
import { setupWebSocketServer } from "./websocket";
import { registerTwilioRoutes } from "./twilio/routes";
import { requireAuth } from "./middleware/requireAuth";
import { registerNotionRoutes } from "./notion/routes";
import { existsSync } from "fs";
import path from "path";
import { randomUUID } from "crypto";
import compression from "compression";
import { geoRestrict } from "./middleware/geoRestrict";
import { legacyRedirects } from "./middleware/legacyRedirects";
import { securityHeaders } from "./middleware/securityHeaders";
import { finalErrorHandler, registerFaviconAlias } from "./middleware/httpHygiene";
import { originCheck } from "./middleware/originCheck";

const app = express();
app.disable("x-powered-by");
// Railway terminates TLS and forwards the real client address in
// X-Forwarded-For. Without this, req.ip is the proxy and every visitor looks
// like the same private address.
app.set("trust proxy", true);

app.use((req, res, next) => {
  const requestId = (req.headers["x-request-id"] as string) || randomUUID();
  req.headers["x-request-id"] = requestId;
  res.setHeader("X-Request-ID", requestId);
  next();
});

app.use((req, res, next) => {
  const host = req.hostname || req.headers.host || "";
  if (host === "www.founderconsole.ai") {
    return res.redirect(301, `https://founderconsole.ai${req.originalUrl}`);
  }
  next();
});

app.use(legacyRedirects());

app.use(securityHeaders());

app.use(compression());

// Country gate. Placed after the security headers (so a blocked response still
// carries them) and before every route, static asset and the SEO prerenderer.
app.use(geoRestrict());

// Cookie-authenticated writes must come from this app's own pages. Before
// every route and proxy (/api, /notifications, /email-tracking, ...).
app.use(originCheck());

const httpServer = createServer(app);

let setupComplete = false;
const appStartTime = Date.now();

const LOADING_HTML = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>FounderConsole</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a0a0a;color:#e5e7eb;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh}.loader{text-align:center}.spinner{width:40px;height:40px;border:3px solid #333;border-top-color:#6366f1;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 16px}@keyframes spin{to{transform:rotate(360deg)}}p{font-size:14px;opacity:0.7}</style></head><body><div class="loader"><div class="spinner"></div><p>Loading FounderConsole...</p></div></body></html>`;

app.get("/health", async (req, res) => {
  if (fastapiProcess && setupComplete) {
    try {
      const backendRes = await fetch("http://127.0.0.1:8001/health", {
        headers: { "x-request-id": req.headers["x-request-id"] as string || "" },
        signal: AbortSignal.timeout(3000),
      });
      if (backendRes.ok) {
        const data = await backendRes.json();
        return res.status(200).json(data);
      }
    } catch {}
  }
  res.status(200).json({ ok: true, status: setupComplete ? "ready" : "starting" });
});

registerFaviconAlias(app);

app.get("/__repl", (_req, res) => {
  res.status(200).json({ ok: true });
});

app.get("/", (_req, res, next) => {
  if (!setupComplete) {
    return res.status(200).type("html").send(LOADING_HTML);
  }
  next();
});

app.use((req, res, next) => {
  if (setupComplete) return next();
  if (req.method === "GET" && !req.path.startsWith("/api")) {
    return res.status(200).type("html").send(LOADING_HTML);
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
let workerProcess: ChildProcess | null = null;
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
  
  const nodeEnv = process.env["ENVIRONMENT"] || process.env["NODE_ENV"] || "production";
  const childEnv: Record<string, string> = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (v !== undefined) childEnv[k] = v;
  }
  childEnv.NODE_ENV = nodeEnv;
  childEnv.ENVIRONMENT = nodeEnv;
  childEnv.PYTHONUNBUFFERED = "1";
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

function startSimulationWorker(): ChildProcess {
  const pythonCommand = resolvePythonCommand();
  const workerModule = "server.workers.simulation_worker";

  console.log(`[worker] Starting simulation worker: ${pythonCommand} -u -m ${workerModule}`);

  const nodeEnv = process.env["ENVIRONMENT"] || process.env["NODE_ENV"] || "production";
  const childEnv: Record<string, string> = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (v !== undefined) childEnv[k] = v;
  }
  childEnv.NODE_ENV = nodeEnv;
  childEnv.ENVIRONMENT = nodeEnv;
  childEnv.PYTHONUNBUFFERED = "1";

  const child = spawn(pythonCommand, ["-u", "-m", workerModule], {
    stdio: ["ignore", "pipe", "pipe"],
    shell: false,
    env: childEnv,
  });

  if (child.stdout) {
    child.stdout.on("data", (data: Buffer) => {
      const lines = data.toString().trim().split("\n");
      for (const line of lines) {
        if (line) console.log(`[worker:out] ${line}`);
      }
    });
  }
  if (child.stderr) {
    child.stderr.on("data", (data: Buffer) => {
      const lines = data.toString().trim().split("\n");
      for (const line of lines) {
        if (line) console.error(`[worker:err] ${line}`);
      }
    });
  }

  console.log(`[worker] Spawned with PID: ${child.pid}`);

  child.on("error", (err) => {
    console.error("[worker] Failed to start:", err);
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      console.log(`[worker] Exited during shutdown (code: ${code}, signal: ${signal})`);
      return;
    }

    if (code !== 0 && code !== null) {
      console.error(`[worker] Exited unexpectedly with code ${code}`);
      setTimeout(() => {
        if (!shuttingDown) {
          console.log("[worker] Restarting simulation worker...");
          workerProcess = startSimulationWorker();
        }
      }, 5000);
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
  
  // Terminate simulation worker
  if (workerProcess && workerProcess.pid) {
    console.log(`[shutdown] Terminating simulation worker (PID: ${workerProcess.pid})...`);
    try {
      workerProcess.kill("SIGTERM");
    } catch (e) {
      // Process may have already exited
    }
  }

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

// Register Twilio messaging routes before the API proxy
const messagingRouter = express.Router();
messagingRouter.use(express.json());
registerTwilioRoutes(messagingRouter);
// Auth-gate all messaging routes: unauthenticated SMS/WhatsApp send is toll-fraud/PII risk.
app.use("/api/messaging", requireAuth, messagingRouter);

// Notion routes are handled by Express, not FastAPI. They share one workspace
// connection, so they are restricted to the platform owner.
registerNotionRoutes(app);

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

// Proxy lead-gen webhook receivers (/webhooks/lead-gen/{ingest,event,simulation})
// to FastAPI. Without this the paths are not matched by any route and fall
// through to the SPA catch-all, which answers 200 text/html — so n8n's POST
// never reaches the HMAC-verified receiver and the lead is silently dropped.
// The body is streamed, not parsed, so the bytes FastAPI hashes are the bytes
// n8n signed. Must stay above express.json() below, which consumes the stream.
app.use(
  "/webhooks/lead-gen",
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    timeout: 30000,
    proxyTimeout: 30000,
    pathRewrite: (path) => `/webhooks/lead-gen${path}`,
    on: {
      error: (err: Error, req, res) => {
        console.error("Lead-gen webhook proxy error:", err.message);
        if ('writeHead' in res && typeof res.writeHead === 'function') {
          res.writeHead(502, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Lead-gen webhook service unavailable", detail: "Internal proxy error" }));
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
    limit: '10mb',
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false, limit: '10mb' }));

registerJarvisRoutes(app);

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

  const isProd = process.env["NODE_ENV"] === "production" || process.env["ENVIRONMENT"] === "production";
  if (isProd) {
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

  // Registered after static/SPA serving so errors raised there (including a
  // malformed percent-encoding) are answered here, not by Express's default.
  app.use(finalErrorHandler);

  setupComplete = true;
  console.log("[startup] Application setup complete");

  waitForFastAPI(600, 2000).then((ready) => {
    if (ready) {
      log("FastAPI backend is ready");
      workerProcess = startSimulationWorker();
    } else {
      log("FastAPI backend not ready yet - API requests will be proxied when available");
    }
  });
})();
