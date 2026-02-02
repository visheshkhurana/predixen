import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: 'metric_update' | 'simulation_complete' | 'truth_scan_update' | 'alert' | 'ping' | 'connection';
  payload: any;
  timestamp: number;
}

export interface MetricUpdate {
  companyId: number;
  metrics: Record<string, number>;
  source: string;
}

export interface SimulationUpdate {
  scenarioId: number;
  status: 'running' | 'completed' | 'failed';
  progress?: number;
  results?: any;
}

const WS_RECONNECT_DELAY = 3000;
const WS_MAX_RECONNECT_ATTEMPTS = 5;
const WS_PING_INTERVAL = 30000;

export function useWebSocket(companyId: number | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const pingInterval = useRef<NodeJS.Timeout | null>(null);
  const listeners = useRef<Map<string, Set<(msg: WebSocketMessage) => void>>>(new Map());

  const cleanup = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (pingInterval.current) {
      clearInterval(pingInterval.current);
      pingInterval.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const notifyListeners = useCallback((type: string, message: WebSocketMessage) => {
    const typeListeners = listeners.current.get(type);
    if (typeListeners) {
      typeListeners.forEach(listener => listener(message));
    }
    const allListeners = listeners.current.get('*');
    if (allListeners) {
      allListeners.forEach(listener => listener(message));
    }
  }, []);

  const connect = useCallback(() => {
    if (!companyId) return;

    cleanup();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws?companyId=${companyId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;

        pingInterval.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          }
        }, WS_PING_INTERVAL);

        const msg: WebSocketMessage = { type: 'connection', payload: { connected: true }, timestamp: Date.now() };
        notifyListeners('connection', msg);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          if (message.type === 'metric_update') {
            const update = message.payload as MetricUpdate;
            if (update.companyId === companyId) {
              setMetrics(prev => ({ ...prev, ...update.metrics }));
            }
          }
          
          if (message.type === 'truth_scan_update') {
            const update = message.payload;
            if (update.companyId === companyId && update.metrics) {
              setMetrics(prev => ({ ...prev, ...update.metrics }));
            }
          }

          notifyListeners(message.type, message);
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }

        if (reconnectAttempts.current < WS_MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          const delay = WS_RECONNECT_DELAY * Math.pow(2, reconnectAttempts.current - 1);
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
          reconnectTimeout.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
    } catch (e) {
      console.error('[WebSocket] Failed to connect:', e);
    }
  }, [companyId, cleanup, notifyListeners]);

  const subscribe = useCallback((type: string, callback: (msg: WebSocketMessage) => void) => {
    if (!listeners.current.has(type)) {
      listeners.current.set(type, new Set());
    }
    listeners.current.get(type)!.add(callback);

    return () => {
      listeners.current.get(type)?.delete(callback);
    };
  }, []);

  const send = useCallback((message: { type: string; payload?: any }) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ ...message, timestamp: Date.now() }));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (companyId) {
      connect();
    }
    return cleanup;
  }, [companyId, connect, cleanup]);

  return {
    isConnected,
    lastMessage,
    metrics,
    subscribe,
    send,
    reconnect: connect,
  };
}

export function useMetricSubscription(
  companyId: number | null,
  metricKeys: string[],
  onUpdate: (metrics: Record<string, number>) => void
) {
  const { subscribe, metrics, isConnected } = useWebSocket(companyId);

  useEffect(() => {
    const unsubscribe = subscribe('metric_update', (msg) => {
      const update = msg.payload as MetricUpdate;
      const filteredMetrics: Record<string, number> = {};
      let hasRelevant = false;
      
      for (const key of metricKeys) {
        if (key in update.metrics) {
          filteredMetrics[key] = update.metrics[key];
          hasRelevant = true;
        }
      }
      
      if (hasRelevant) {
        onUpdate(filteredMetrics);
      }
    });

    return unsubscribe;
  }, [subscribe, metricKeys, onUpdate]);

  return { metrics, isConnected };
}

export function useSimulationSubscription(
  scenarioId: number | null,
  onUpdate: (update: SimulationUpdate) => void
) {
  const { subscribe, isConnected } = useWebSocket(null);

  useEffect(() => {
    if (!scenarioId) return;

    const unsubscribe = subscribe('simulation_complete', (msg) => {
      const update = msg.payload as SimulationUpdate;
      if (update.scenarioId === scenarioId) {
        onUpdate(update);
      }
    });

    return unsubscribe;
  }, [subscribe, scenarioId, onUpdate]);

  return { isConnected };
}
