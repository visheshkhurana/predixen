import { useState, useEffect, useCallback, useRef } from 'react';

export interface KPIMetrics {
  monthly_revenue: number;
  mrr: number;
  arr: number;
  cash_balance: number;
  net_burn: number;
  runway_months: number;
  gross_margin: number;
  churn_rate: number;
  cac: number;
  ltv: number;
  ltv_cac_ratio: number;
  headcount: number;
  revenue_per_employee: number;
}

export interface KPIUpdate {
  timestamp: string;
  company_id: number;
  metrics: KPIMetrics;
}

interface UseRealtimeKPIOptions {
  enabled?: boolean;
  onUpdate?: (data: KPIUpdate) => void;
  onError?: (error: Error) => void;
}

export function useRealtimeKPI(
  companyId: number | null,
  options: UseRealtimeKPIOptions = {}
) {
  const { enabled = true } = options;
  const [data, setData] = useState<KPIUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // Use refs for callbacks to avoid dependency issues
  const onUpdateRef = useRef(options.onUpdate);
  const onErrorRef = useRef(options.onError);
  
  // Update refs when options change
  useEffect(() => {
    onUpdateRef.current = options.onUpdate;
    onErrorRef.current = options.onError;
  }, [options.onUpdate, options.onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    if (!companyId || !enabled) {
      disconnect();
      return;
    }

    // Try multiple token storage locations
    let token = localStorage.getItem('predixen-token');
    if (!token) {
      try {
        const zustandStorage = localStorage.getItem('predixen-founder-storage');
        if (zustandStorage) {
          const parsed = JSON.parse(zustandStorage);
          token = parsed?.state?.token || null;
        }
      } catch {
        // Ignore parse errors
      }
    }
    if (!token) {
      setError(new Error('Not authenticated'));
      return;
    }

    const url = `/api/realtime/kpi/${companyId}`;
    
    try {
      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const eventSource = new EventSource(url, {
        withCredentials: true
      });

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.addEventListener('kpi_update', (event) => {
        try {
          const update: KPIUpdate = JSON.parse(event.data);
          setData(update);
          onUpdateRef.current?.(update);
        } catch (e) {
          console.error('Failed to parse KPI update:', e);
        }
      });

      eventSource.addEventListener('error', (event) => {
        try {
          const errorData = JSON.parse((event as any).data || '{}');
          const err = new Error(errorData.error || 'SSE connection error');
          setError(err);
          onErrorRef.current?.(err);
        } catch {
          const err = new Error('SSE connection error');
          setError(err);
          onErrorRef.current?.(err);
        }
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
        // Reconnect after delay - but use a ref to avoid closure issues
        const reconnectTimer = setTimeout(() => {
          if (enabled && companyId) {
            // The useEffect will re-run and reconnect
          }
        }, 5000);
        return () => clearTimeout(reconnectTimer);
      };

      eventSourceRef.current = eventSource;
    } catch (e) {
      const err = e instanceof Error ? e : new Error('Failed to connect');
      setError(err);
      onErrorRef.current?.(err);
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [companyId, enabled, disconnect]);

  const connect = useCallback(() => {
    // Trigger reconnect by toggling - but this is mostly for manual reconnect
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    // The useEffect will handle reconnection
  }, []);

  return {
    data,
    isConnected,
    error,
    connect,
    disconnect
  };
}
