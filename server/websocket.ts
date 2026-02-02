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

export function setupWebSocketServer(httpServer: Server): WebSocketServer {
  const wss = new WebSocketServer({ 
    server: httpServer, 
    path: '/ws',
    verifyClient: (info, callback) => {
      callback(true);
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

    ws.send(JSON.stringify({
      type: 'connection',
      payload: { connected: true, companyId },
      timestamp: Date.now(),
    }));

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        
        if (message.type === 'ping') {
          client.lastPing = Date.now();
          ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
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
      clients.delete(ws);
    });
  });

  setInterval(() => {
    const now = Date.now();
    clients.forEach((client, ws) => {
      if (now - client.lastPing > PING_INTERVAL + PING_TIMEOUT) {
        console.log('[WebSocket] Client timed out, closing connection');
        ws.terminate();
        clients.delete(ws);
      } else if (ws.readyState === WebSocket.OPEN) {
        ws.ping();
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

  clients.forEach((client) => {
    if (client.ws.readyState === WebSocket.OPEN && client.companyId === companyId) {
      client.ws.send(messageStr);
      sentCount++;
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast metric update to ${sentCount} clients (companyId: ${companyId})`);
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

  clients.forEach((client) => {
    if (client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(messageStr);
      sentCount++;
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast simulation update to ${sentCount} clients (scenarioId: ${scenarioId}, status: ${status})`);
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

  clients.forEach((client) => {
    if (client.ws.readyState === WebSocket.OPEN && client.companyId === companyId) {
      client.ws.send(messageStr);
      sentCount++;
    }
  });

  if (sentCount > 0) {
    console.log(`[WebSocket] Broadcast truth scan update to ${sentCount} clients (companyId: ${companyId})`);
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
