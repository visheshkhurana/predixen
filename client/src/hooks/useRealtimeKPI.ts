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
  
  const onUpdateRef = useRef(options.onUpdate);
  const onErrorRef = useRef(options.onError);
  
  useEffect(() => {
    onUpdateRef.current = options.onUpdate;
    onErrorRef.current = options.onError;
  }, [options.onUpdate, options.onError]);

  const disconnect = useCallback(() => {
    setIsConnected(false);
  }, []);

  const fetchKPIData = useCallback(async () => {
    if (!companyId) return;
    
    try {
      const response = await fetch(`/api/realtime/kpi/${companyId}/snapshot`, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const update: KPIUpdate = await response.json();
      setData(update);
      setIsConnected(true);
      setError(null);
      onUpdateRef.current?.(update);
    } catch (e) {
      const err = e instanceof Error ? e : new Error('Failed to fetch KPI data');
      setError(err);
      onErrorRef.current?.(err);
    }
  }, [companyId, getToken]);

  useEffect(() => {
    if (!companyId || !enabled) {
      disconnect();
      return;
    }

    const token = getToken();
    if (!token) {
      setError(new Error('Not authenticated'));
      return;
    }

    fetchKPIData();
    
    const intervalId = setInterval(fetchKPIData, 10000);
    setIsConnected(true);

    return () => {
      clearInterval(intervalId);
      setIsConnected(false);
    };
  }, [companyId, enabled, getToken, fetchKPIData, disconnect]);

  const connect = useCallback(() => {
    fetchKPIData();
  }, [fetchKPIData]);

  return {
    data,
    isConnected,
    error,
    connect,
    disconnect
  };
}
