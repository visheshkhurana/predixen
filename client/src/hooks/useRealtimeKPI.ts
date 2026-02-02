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
  const { enabled = true, onUpdate, onError } = options;
  const [data, setData] = useState<KPIUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!companyId || !enabled) return;

    const token = localStorage.getItem('auth_token');
    if (!token) {
      setError(new Error('Not authenticated'));
      return;
    }

    const url = `/api/realtime/kpi/${companyId}`;
    
    try {
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
          onUpdate?.(update);
        } catch (e) {
          console.error('Failed to parse KPI update:', e);
        }
      });

      eventSource.addEventListener('error', (event) => {
        try {
          const errorData = JSON.parse((event as any).data || '{}');
          const err = new Error(errorData.error || 'SSE connection error');
          setError(err);
          onError?.(err);
        } catch {
          const err = new Error('SSE connection error');
          setError(err);
          onError?.(err);
        }
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
        setTimeout(() => {
          if (enabled) connect();
        }, 5000);
      };

      eventSourceRef.current = eventSource;
    } catch (e) {
      const err = e instanceof Error ? e : new Error('Failed to connect');
      setError(err);
      onError?.(err);
    }
  }, [companyId, enabled, onUpdate, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    if (enabled && companyId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [companyId, enabled, connect, disconnect]);

  return {
    data,
    isConnected,
    error,
    connect,
    disconnect
  };
}
