const API_BASE = '/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('predixen-token');
  
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
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(response.status, error.detail || error.message || 'Request failed');
  }
  
  return response.json();
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ access_token: string; user_id: number; email: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string; user_id: number; email: string }>('/auth/login', {
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
  },
  
  datasets: {
    upload: async (companyId: number, type: string, file: File) => {
      const token = localStorage.getItem('predixen-token');
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE}/companies/${companyId}/datasets/upload?dataset_type=${type}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new ApiError(response.status, error.detail);
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
    }) =>
      request<any>(`/companies/${companyId}/datasets/manual_baseline`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
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
    run: (scenarioId: number, nSims = 1000) =>
      request<any>(`/scenarios/${scenarioId}/simulate`, {
        method: 'POST',
        body: JSON.stringify({ n_sims: nSims }),
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
  },
  
  decisions: {
    generate: (runId: number) =>
      request<any>(`/simulation/${runId}/decisions/generate`, { method: 'POST' }),
    latest: (companyId: number) =>
      request<any>(`/companies/${companyId}/decisions/latest`),
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
};
