import { WebSocketServer, WebSocket } from 'ws';
import type { Server } from 'http';
import type { IncomingMessage } from 'http';

interface WSClient {
  ws: WebSocket;
  companyId: number | null;
  lastPing: number;
}

interface MetricUpdate {
  type: 'metric_update';
  payload: {
    companyId: number;
    metrics: Record<string, number>;
    source: string;
  };
  timestamp: number;
}

interface SimulationUpdate {
  type: 'simulation_complete';
  payload: {
    scenarioId: number;
    status: 'running' | 'completed' | 'failed';
    progress?: number;
    results?: any;
  };
  timestamp: number;
}

interface TruthScanUpdate {
  type: 'truth_scan_update';
  payload: {
    companyId: number;
    metrics: Record<string, any>;
    status: string;
  };
  timestamp: number;
}

type WSMessage = MetricUpdate | SimulationUpdate | TruthScanUpdate;

const clients = new Map<WebSocket, WSClient>();
const PING_INTERVAL = 30000;
const PING_TIMEOUT = 10000;

/**
 * Safely sends a message to a WebSocket client.
 * Checks connection state before sending and handles errors gracefully.
 *
 * @param ws WebSocket connection
 * @param data Data to send (will be JSON stringified if not already a string)
 * @param label Optional label for logging context
 * @returns true if send was attempted, false if socket was not open
 */
function safeSend(ws: WebSocket, data: string | object, label: string = 'message'): boolean {
  try {
    // Check if WebSocket is in OPEN state before attempting to send
    if (ws.readyState !== WebSocket.OPEN) {
      console.warn(`[WebSocket] Cannot send ${label}: socket not open (state: ${ws.readyState})`);
      return false;
    }

    const messageStr = typeof data === 'string' ? data : JSON.stringify(data);
    ws.send(messageStr, (err) => {
      if (err) {
        console.error(`[WebSocket] Failed to send ${label}:`, err.message);
      }
    });

    return true;
  } catch (error) {
    console.error(`[WebSocket] Exception while sending ${label}:`, error instanceof Error ? error.message : error);
    return false;
  }
}

export function setupWebSocketServer(httpServer: Server): WebSocketServer {
  const wss = new WebSocketServer({ 
    server: httpServer, 
    path: '/ws',
    verifyClient: (info, callback) => {
      try {
        const url = new URL(info.req.url || '', `http://${info.req.headers.host}`);
        const token = url.searchParams.get('token');
        if (!token) {
          console.log('[WebSocket] Rejected: no token provided');
          callback(false, 401, 'Authentication required');
          return;
        }
        if (token.length < 10) {
          console.log('[WebSocket] Rejected: invalid token format');
          callback(false, 401, 'Invalid token');
          return;
        }
        const parts = token.split('.');
        if (parts.length !== 3) {
          console.log('[WebSocket] Rejected: malformed JWT');
          callback(false, 401, 'Invalid token format');
          return;
        }
        try {
          const payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
          const payload = JSON.parse(Buffer.from(payloadB64, 'base64').toString());
          if (!payload.sub) {
            console.log('[WebSocket] Rejected: JWT missing sub claim');
            callback(false, 401, 'Invalid token');
            return;
          }
          if (payload.exp && payload.exp * 1000 < Date.now()) {
            console.log('[WebSocket] Rejected: JWT expired');
            callback(false, 401, 'Token expired');
            return;
          }
        } catch {
          console.log('[WebSocket] Rejected: could not decode JWT payload');
          callback(false, 401, 'Invalid token');
          return;
        }
        callback(true);
      } catch (e) {
        console.error('[WebSocket] Auth error:', e);
        callback(false, 500, 'Internal error');
      }
    }
  });

  console.log('[WebSocket] Server initialized on /ws');

  wss.on('connection', (ws: WebSocket, req: IncomingMessage) => {
    const url = new URL(req.url || '', `http://${req.headers.host}`);
    const companyIdParam = url.searchParams.get('companyId');
    const companyId = companyIdParam ? parseInt(companyIdParam, 10) : null;

    const client: WSClient = {
      ws,
      companyId,
      lastPing: Date.now(),
    };

    clients.set(ws, client);
    console.log(`[WebSocket] Client connected (companyId: ${companyId}, total: ${clients.size})`);

    // Send connection confirmation message
    safeSend(ws, {
      type: 'connection',
      payload: { connected: true, companyId },
      timestamp: Date.now(),
    }, 'connection-confirmation');

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());

        if (message.type === 'ping') {
          client.lastPing = Date.now();
          safeSend(ws, { type: 'pong', timestamp: Date.now() }, 'pong-response');
        } else if (message.type === 'subscribe') {
          if (message.companyId) {
            client.companyId = message.companyId;
            console.log(`[WebSocket] Client subscribed to companyId: ${message.companyId}`);
          }
        }
      } catch (e) {
        console.error('[WebSocket] Failed to parse message:', e);
      }
    });

    ws.on('close', () => {
      clients.delete(ws);
      console.log(`[WebSocket] Client disconnected (total: ${clients.size})`);
    });

    ws.on('error', (error) => {
      console.error('[WebSocket] Client error:', error);
      // Ensure client is removed from tracking
      if (clients.has(ws)) {
        clients.delete(ws);
      }
      // Attempt to close the connection gracefully
      try {
        if (ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
          ws.close();
        }
      } catch (e) {
        console.warn('[WebSocket] Error closing socket after error:', e);
      }
    });
  });

  setInterval(() => {
    const now = Date.now();
    clients.forEach((client, ws) => {
      if (now - client.lastPing > PING_INTERVAL + PING_TIMEOUT) {
        console.log('[WebSocket] Client timed out, closing connection');
        try {
          ws.terminate();
        } catch (e) {
          console.warn('[WebSocket] Error terminating timed-out connection:', e);
        }
        clients.delete(ws);
      } else if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.ping((err?: Error) => {
            if (err) {
              console.error('[WebSocket] Ping error:', err.message);
            }
          });
        } catch (e) {
          console.error('[WebSocket] Error sending ping:', e);
        }
      }
    });
  }, PING_INTERVAL);

  return wss;
}

export function broadcastMetricUpdate(companyId: number, metrics: Record<string, number>, source: string = 'system'): void {
  const message: MetricUpdate = {
    type: 'metric_update',
    payload: { companyId, metrics, source },
    timestamp: Date.now(),
  };

  const messageStr = JSON.stringify(message);
  let sentCount = 0;
  let failedCount = 0;

  clients.forEach((client) => {
    if (client.companyId === companyId) {
      if (safeSend(client.ws, messageStr, `metric-update-companyId-${companyId}`)) {
        sentCount++;
      } else {
        failedCount++;
      }
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast metric update to ${sentCount} clients (companyId: ${companyId})`);
  }
  if (failedCount > 0) {
    console.warn(`[WebSocket] Failed to send metric update to ${failedCount} clients (companyId: ${companyId})`);
  }
}

export function broadcastSimulationUpdate(scenarioId: number, status: 'running' | 'completed' | 'failed', progress?: number, results?: any): void {
  const message: SimulationUpdate = {
    type: 'simulation_complete',
    payload: { scenarioId, status, progress, results },
    timestamp: Date.now(),
  };

  const messageStr = JSON.stringify(message);
  let sentCount = 0;
  let failedCount = 0;

  clients.forEach((client) => {
    if (safeSend(client.ws, messageStr, `simulation-update-scenarioId-${scenarioId}`)) {
      sentCount++;
    } else {
      failedCount++;
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast simulation update to ${sentCount} clients (scenarioId: ${scenarioId}, status: ${status})`);
  }
  if (failedCount > 0) {
    console.warn(`[WebSocket] Failed to send simulation update to ${failedCount} clients (scenarioId: ${scenarioId}, status: ${status})`);
  }
}

export function broadcastTruthScanUpdate(companyId: number, metrics: Record<string, any>, status: string): void {
  const message: TruthScanUpdate = {
    type: 'truth_scan_update',
    payload: { companyId, metrics, status },
    timestamp: Date.now(),
  };

  const messageStr = JSON.stringify(message);
  let sentCount = 0;
  let failedCount = 0;

  clients.forEach((client) => {
    if (client.companyId === companyId) {
      if (safeSend(client.ws, messageStr, `truth-scan-update-companyId-${companyId}`)) {
        sentCount++;
      } else {
        failedCount++;
      }
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast truth scan update to ${sentCount} clients (companyId: ${companyId})`);
  }
  if (failedCount > 0) {
    console.warn(`[WebSocket] Failed to send truth scan update to ${failedCount} clients (companyId: ${companyId})`);
  }
}

export function getConnectedClientsCount(): number {
  return clients.size;
}

export function getClientsForCompany(companyId: number): number {
  let count = 0;
  clients.forEach((client) => {
    if (client.companyId === companyId && client.ws.readyState === WebSocket.OPEN) {
      count++;
    }
  });
  return count;
}
