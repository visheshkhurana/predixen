import { ApiError } from '@/lib/errors';
export { ApiError };

const API_BASE = '/api';

// Helper to get token from localStorage or Zustand persisted storage
function getAuthToken(): string | null {
  // First try direct localStorage key
  let token = localStorage.getItem('founderconsole-token');
  
  // Fallback: try to get from Zustand persisted storage
  if (!token) {
    try {
      const zustandStorage = localStorage.getItem('founderconsole-founder-storage');
      if (zustandStorage) {
        const parsed = JSON.parse(zustandStorage);
        token = parsed?.state?.token || null;
        // Sync back to direct key if found
        if (token) {
          localStorage.setItem('founderconsole-token', token);
        }
      }
    } catch {
      // Ignore JSON parse errors
    }
  }
  
  return token;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    let errorMessage = 'Request failed';
    let detail: any = null;
    
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const error = await response.json();
        detail = error.detail || error;
        if (typeof detail === 'object') {
          errorMessage = detail.message || error.message || `Request failed (${response.status})`;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
          detail = null;
        } else {
          errorMessage = error.message || `Request failed (${response.status})`;
        }
      } else {
        const text = await response.text();
        errorMessage = text || `Request failed (${response.status})`;
      }
    } catch {
      errorMessage = `Request failed (${response.status})`;
    }
    console.error(`API Error: ${response.status} ${endpoint}`, errorMessage);
    throw new ApiError(response.status, errorMessage, detail);
  }
  
  return response.json();
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ access_token: string; user_id: number; email: string; role: string; is_platform_admin: boolean }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string; user_id: number; email: string; role: string; is_platform_admin: boolean }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    adminLogin: (email: string, password: string) =>
      request<{ access_token: string; user_id: number; email: string; role: string; is_platform_admin: boolean }>('/auth/admin/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
  },
  
  companies: {
    list: () => request<any[]>('/companies'),
    get: (id: number) => request<any>(`/companies/${id}`),
    create: (data: { name: string; website?: string; industry?: string; stage?: string; currency?: string }) =>
      request<any>('/companies', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: { name?: string; website?: string; industry?: string; stage?: string; currency?: string }) =>
      request<any>(`/companies/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ message: string }>(`/companies/${id}`, {
        method: 'DELETE',
      }),
  },
  
  datasets: {
    upload: async (companyId: number, type: string, file: File) => {
      const token = getAuthToken();
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE}/companies/${companyId}/datasets/upload?dataset_type=${type}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        const detail = error.detail;
        const message = typeof detail === 'object' ? (detail.message || 'Upload failed') : (detail || 'Upload failed');
        throw new ApiError(response.status, message, typeof detail === 'object' ? detail : null);
      }
      
      return response.json();
    },
    manualBaseline: (companyId: number, data: {
      monthly_revenue: number;
      gross_margin_pct: number;
      opex: number;
      payroll: number;
      other_costs: number;
      cash_balance: number;
      headcount?: number;
    }) =>
      request<any>(`/companies/${companyId}/datasets/manual_baseline`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    uploadTerminaPdf: async (companyId: number, file: File, saveAsBaseline = true) => {
      const token = getAuthToken();
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(
        `${API_BASE}/companies/${companyId}/datasets/termina-pdf?save_as_baseline=${saveAsBaseline}`, 
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        const detail = error.detail;
        const message = typeof detail === 'object' ? (detail.message || 'Upload failed') : (detail || 'Upload failed');
        throw new ApiError(response.status, message, typeof detail === 'object' ? detail : null);
      }
      
      return response.json();
    },
    uploadTerminaExcel: async (companyId: number, file: File, saveAsBaseline = true) => {
      const token = getAuthToken();
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(
        `${API_BASE}/companies/${companyId}/datasets/termina-excel?save_as_baseline=${saveAsBaseline}`, 
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        const detail = error.detail;
        const message = typeof detail === 'object' ? (detail.message || 'Upload failed') : (detail || 'Upload failed');
        throw new ApiError(response.status, message, typeof detail === 'object' ? detail : null);
      }
      
      return response.json();
    },
  },
  
  metrics: {
    computed: (companyId: number) =>
      request<any>(`/companies/${companyId}/metrics/computed`),
  },

  truth: {
    run: (companyId: number) =>
      request<any>(`/companies/${companyId}/truth/run`, { method: 'POST' }),
    latest: (companyId: number) =>
      request<any>(`/companies/${companyId}/truth/latest`),
  },
  
  scenarios: {
    list: (companyId: number) => request<any[]>(`/companies/${companyId}/scenarios`),
    create: (companyId: number, data: any) =>
      request<any>(`/companies/${companyId}/scenarios`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  
  simulations: {
    run: (scenarioId: number, nSims = 500, seed?: number) =>
      request<any>(`/scenarios/${scenarioId}/simulate`, {
        method: 'POST',
        body: JSON.stringify({ n_sims: nSims, ...(seed !== undefined ? { seed } : {}) }),
      }),
    latest: (scenarioId: number) =>
      request<any>(`/scenarios/${scenarioId}/simulation/latest`),
    runMulti: (companyId: number, options?: { 
      n_sims?: number; 
      horizon_months?: number; 
      scenario_keys?: string[];
      seed?: number;
    }) =>
      request<any>(`/companies/${companyId}/simulate-multi`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),
    getDefaultScenarios: (companyId: number) =>
      request<any>(`/companies/${companyId}/default-scenarios`),
    runEnhanced: (companyId: number, options: {
      n_sims?: number;
      horizon_months?: number;
      starting_regime?: string;
      enable_regime_transitions?: boolean;
      churn_rate?: number;
      cac?: number;
      dso?: number;
      conversion_rate?: number;
      headcount?: number;
      total_customers?: number;
      arpu?: number;
      pipeline_value?: number;
      seed?: number;
    }) =>
      request<any>(`/companies/${companyId}/simulate-enhanced`, {
        method: 'POST',
        body: JSON.stringify(options),
      }),
    runEnhancedMulti: (companyId: number, options: {
      n_sims?: number;
      horizon_months?: number;
      starting_regime?: string;
      enable_regime_transitions?: boolean;
      churn_rate?: number;
      cac?: number;
      dso?: number;
      scenarios?: Array<{
        name: string;
        description?: string;
        events?: Array<{
          event_type: string;
          start_month: number;
          end_month?: number;
          params?: Record<string, any>;
          description?: string;
        }>;
        starting_regime?: string;
        regime_override?: string;
      }>;
      include_sensitivity?: boolean;
      seed?: number;
    }) =>
      request<any>(`/companies/${companyId}/simulate-scenarios-enhanced`, {
        method: 'POST',
        body: JSON.stringify(options),
      }),
    runSensitivityAnalysis: (companyId: number, targetRunway = 18, targetProbability = 0.7) =>
      request<any>(`/companies/${companyId}/sensitivity-analysis?target_runway=${targetRunway}&target_probability=${targetProbability}`, {
        method: 'POST',
      }),
    counterMoves: (scenarioId: number) =>
      request<{
        scenario_id: number;
        counter_moves: Array<{
          id: string;
          name: string;
          description: string;
          icon: string;
          overrides_applied: Record<string, number>;
          runway: { p10: number; p50: number; p90: number };
          survival: Record<string, number>;
          survivalProbability: Record<string, number>;
          breakEvenMonth: { p10: number; p50: number; p90: number };
          summary: any;
        }>;
      }>(`/scenarios/${scenarioId}/counter-moves`, {
        method: 'POST',
      }),
    getTimeseries: (scenarioId: number) =>
      request<{
        scenario_id: number;
        scenario_name: string;
        timeseries: Array<{
          month: number;
          cashBalance: number;
          monthlyBurn: number;
          monthlyRevenue: number;
          runwayRemaining: number;
          headcount?: number;
        }>;
        fundingEvents: Array<{
          month: number;
          amount: number;
          label?: string;
        }>;
        summary: any;
        runway: any;
        survival: any;
      }>(`/scenarios/${scenarioId}/timeseries`),
  },
  
  decisions: {
    generate: (runId: number) =>
      request<any>(`/simulation/${runId}/decisions/generate`, { method: 'POST' }),
    latest: (companyId: number) =>
      request<any>(`/companies/${companyId}/decisions/latest`),
    strategicDiagnosis: (companyId: number) =>
      request<any>(`/companies/${companyId}/strategic-diagnosis`),
  },
  
  copilot: {
    context: (companyId: number) =>
      request<any>(`/companies/${companyId}/context`),
    simulate: (companyId: number, deltas: any) =>
      request<any>(`/companies/${companyId}/simulate`, {
        method: 'POST',
        body: JSON.stringify(deltas),
      }),
    compare: (companyId: number, actionIds: string[]) =>
      request<any>(`/companies/${companyId}/decision/compare`, {
        method: 'POST',
        body: JSON.stringify({ action_ids: actionIds }),
      }),
  },
  
  admin: {
    dashboard: () => request<{
      total_users: number;
      active_users: number;
      total_companies: number;
      total_subscriptions: number;
      mrr: number;
      active_simulations: number;
      truth_scans_today: number;
    }>('/admin/dashboard'),
    
    users: {
      list: () => request<Array<{
        id: number;
        email: string;
        role: string;
        is_active: boolean;
        created_at: string;
        company_count: number;
      }>>('/admin/users'),
      get: (userId: number) => request<{
        id: number;
        email: string;
        role: string;
        is_active: boolean;
        created_at: string;
        company_count: number;
        companies: Array<{ id: number; name: string }>;
        last_login: {
          timestamp: string | null;
          ip_address: string | null;
          device_type: string | null;
          browser: string | null;
        } | null;
        total_logins: number;
      }>(`/admin/users/${userId}/details`),
      update: (userId: number, data: { role?: string; is_active?: boolean }) =>
        request<any>(`/admin/users/${userId}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),
      suspend: (userId: number) =>
        request<any>(`/admin/users/${userId}/suspend`, { method: 'POST' }),
      activate: (userId: number) =>
        request<any>(`/admin/users/${userId}/activate`, { method: 'POST' }),
    },
    
    companies: {
      list: () => request<Array<{
        id: number;
        name: string;
        industry: string | null;
        stage: string | null;
        user_email: string;
        created_at: string;
      }>>('/admin/companies'),
      get: (companyId: number) => request<any>(`/admin/companies/${companyId}`),
    },
    
    subscriptions: {
      list: () => request<Array<{
        id: number;
        user_email: string | null;
        company_name: string | null;
        plan: string;
        status: string;
        seats: number;
        monthly_price: number;
        current_period_end: string | null;
        created_at: string;
      }>>('/admin/subscriptions'),
      update: (subscriptionId: number, data: { plan?: string; seats?: number; status?: string }) =>
        request<any>(`/admin/subscriptions/${subscriptionId}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),
    },
    
    metrics: () => request<{
      financial: {
        total_revenue: number;
        avg_burn: number;
        avg_runway_months: number;
      };
      users_by_role: Record<string, number>;
      companies_by_stage: Record<string, number>;
    }>('/admin/metrics/aggregate'),
    
    auditLogs: (limit = 50, actionType?: string, userId?: number) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (actionType) params.append('action_type', actionType);
      if (userId) params.append('user_id', String(userId));
      return request<Array<{
        id: number;
        user_email: string | null;
        action: string;
        resource_type: string | null;
        resource_id: number | null;
        details: any;
        ip_address: string | null;
        created_at: string;
      }>>(`/admin/audit-logs?${params}`);
    },
    
    loginHistory: (limit = 100, successOnly?: boolean, userId?: number) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (successOnly !== undefined) params.append('success_only', String(successOnly));
      if (userId) params.append('user_id', String(userId));
      return request<Array<{
        id: number;
        user_id: number | null;
        email: string;
        ip_address: string | null;
        user_agent: string | null;
        device_type: string | null;
        browser: string | null;
        os: string | null;
        country: string | null;
        city: string | null;
        success: boolean;
        failure_reason: string | null;
        created_at: string;
      }>>(`/admin/login-history?${params}`);
    },
    
    notifications: (limit = 50) => request<Array<{
      id: number;
      user_id: number | null;
      company_id: number | null;
      type: string;
      severity: string;
      title: string;
      message: string | null;
      read: boolean;
      created_at: string;
    }>>(`/admin/notifications?limit=${limit}`),
    
    activityStats: (days = 30) => request<{
      logins_by_date: Record<string, number>;
      new_users_by_date: Record<string, number>;
    }>(`/admin/stats/activity?days=${days}`),
    
    me: () => request<{
      id: number;
      email: string;
      role: string;
      is_admin: boolean;
    }>('/admin/me'),
    
    invites: {
      list: () => request<Array<{
        id: number;
        email: string;
        role: string;
        invited_by_email: string;
        accepted: boolean;
        expires_at: string;
        created_at: string;
        is_expired: boolean;
      }>>('/admin/invites'),
      create: (email: string, role: string) =>
        request<{ message: string; invite_id: number; token: string; expires_at: string; email_sent: boolean; email_error?: string }>('/admin/invites', {
          method: 'POST',
          body: JSON.stringify({ email, role }),
        }),
      revoke: (inviteId: number) =>
        request<{ message: string }>(`/admin/invites/${inviteId}`, { method: 'DELETE' }),
      resend: (inviteId: number) =>
        request<{ message: string; expires_at: string; email_sent: boolean; email_error?: string }>(`/admin/invites/${inviteId}/resend`, { method: 'POST' }),
    },
    
    emailTemplates: {
      status: () => request<{
        configured: boolean;
        from_email: string | null;
      }>('/email-templates/status'),
      list: () => request<Array<{
        id: string;
        name: string;
        description: string;
        variables: string[];
        subject: string;
      }>>('/email-templates/templates'),
      preview: (templateType: string) => request<{
        template_type: string;
        name: string;
        subject: string;
        html: string;
        variables: string[];
      }>(`/email-templates/templates/${templateType}/preview`),
      sendTest: (templateType: string, toEmail: string) =>
        request<{ success: boolean; message: string; template_type: string }>('/email-templates/test', {
          method: 'POST',
          body: JSON.stringify({ template_type: templateType, to_email: toEmail }),
        }),
    },
    
    llmAudit: {
      list: (page = 1, perPage = 20, piiMode?: string) => {
        const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
        if (piiMode && piiMode !== 'all') params.append('pii_mode', piiMode);
        return request<{
          logs: Array<{
            id: string;
            company_id: number | null;
            user_id: number | null;
            endpoint: string;
            model: string;
            pii_mode: string;
            prompt_hash: string;
            input_chars_original: number;
            input_chars_redacted: number;
            pii_findings_json: Array<{
              type: string;
              count: number;
              examples: string[];
              confidence: string;
            }> | null;
            redacted_prompt_preview: string | null;
            redacted_output_preview: string | null;
            tokens_in: number | null;
            tokens_out: number | null;
            latency_ms: number | null;
            created_at: string;
          }>;
          total: number;
          page: number;
          per_page: number;
        }>(`/admin/llm-audit?${params}`);
      },
      stats: () => request<{
        period_days: number;
        total_requests: number;
        total_tokens_in: number;
        total_tokens_out: number;
        avg_latency_ms: number;
        pii_mode_breakdown: Record<string, number>;
        requests_with_pii_detected: number;
      }>('/admin/llm-audit/stats/summary'),
    },
    
    evals: {
      suites: () => request<{
        suites: Array<{
          name: string;
          description: string;
          metrics: string[];
        }>;
      }>('/admin/evals/suites'),
      runs: (page = 1, perPage = 10) => {
        const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
        return request<{
          runs: Array<{
            id: string;
            suite_name: string;
            inputs_json: Record<string, any> | null;
            outputs_json: Record<string, any> | null;
            scores_json: Record<string, {
              score: number;
              max_score: number;
              percentage: number;
              details: Record<string, any>;
            }> | null;
            overall_score: number | null;
            status: string;
            error_message: string | null;
            created_at: string;
            completed_at: string | null;
          }>;
          total: number;
          page: number;
          per_page: number;
        }>(`/admin/evals/runs?${params}`);
      },
      run: (suiteName: string) =>
        request<{ run_id: string; status: string }>('/admin/evals/run', {
          method: 'POST',
          body: JSON.stringify({ suite_name: suiteName }),
        }),
    },
  },
  
  benchmarks: {
    search: (industry: string, stage: string) =>
      request<{
        industry: string;
        stage: string;
        benchmarks: Array<{
          metric_name: string;
          p25: number;
          p50: number;
          p75: number;
          direction: string;
          source: string | null;
          confidence: string;
        }>;
        sources: string[];
        last_updated: string;
        is_cached: boolean;
      }>('/benchmarks/search', {
        method: 'POST',
        body: JSON.stringify({ industry, stage }),
      }),
    industries: () =>
      request<{
        industries: Array<{ id: string; name: string }>;
        stages: Array<{ id: string; name: string }>;
      }>('/benchmarks/industries'),
    clearCache: () =>
      request<{ message: string; cleared_at: string }>('/benchmarks/cache', {
        method: 'DELETE',
      }),
  },
};
