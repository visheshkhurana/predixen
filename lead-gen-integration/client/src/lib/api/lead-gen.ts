/**
 * Lead-gen API client.
 * Place at: client/src/lib/api/lead-gen.ts
 *
 * Matches the Python routes in server/api/lead_gen.py. Uses the same
 * authenticated fetch helper as the rest of the app — adjust the import
 * path for your existing `apiClient` / `fetch` wrapper if different.
 */

// Adjust this import to match your existing API helper in predixen:
//   e.g. import { apiFetch } from "@/lib/api/client";
// The stub below works if you don't have one yet.
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text || path}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ============================================================
// Types (mirror server/api/lead_gen.py Pydantic schemas)
// ============================================================
export interface Lead {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  linkedin_url: string | null;
  website: string | null;
  source: string;
  sector: string | null;
  stage: string | null;
  status: string;
  hunter_status: string | null;
  plan: string | null;
  summary: string | null;
  hook: string | null;
  last_email_at: string | null;
  reply_category: string | null;
  trial_signed_up_at: string | null;
  has_simulated: boolean;
  p50_survival: number | null;
  tags: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadEvent {
  id: number;
  lead_id: number;
  campaign_id: number | null;
  kind: string;
  email_subject: string | null;
  email_body_preview: string | null;
  reply_category: string | null;
  metadata: Record<string, unknown>;
  source_system: string;
  created_at: string;
}

export interface LeadDetail extends Lead {
  recent_events: LeadEvent[];
}

export interface Campaign {
  id: number;
  name: string;
  description: string | null;
  target_segment: Record<string, string[]>;
  n8n_workflow_id: string | null;
  n8n_webhook_path: string | null;
  cadence_days: number[];
  goal_metric: string;
  status: "draft" | "active" | "paused" | "archived";
  created_at: string;
}

export interface Template {
  id: number;
  key: string;
  label: string;
  category: "outbound" | "inbound" | "activation";
  system_prompt: string;
  sample_subject: string | null;
  sample_body: string | null;
  model: string | null;
  is_active: boolean;
  updated_at: string;
}

export interface Stats {
  totals: Record<string, number>;
  sources: Record<string, number>;
  last_7d_sends: number;
  last_7d_replies: number;
  reply_rate_7d: number;
  trial_signups_7d: number;
  active_campaigns: number;
  recent_events: LeadEvent[];
}

export interface Settings {
  n8n_base_url: string | null;
  n8n_api_key_set: boolean;
  outbound_webhook_url: string | null;
  activation_webhook_url: string | null;
  sending_domain: string | null;
  daily_send_limit: number;
  is_enabled: boolean;
  updated_at: string | null;
}

// ============================================================
// Client
// ============================================================
const BASE = "/api/admin/lead-gen";

export const leadGenApi = {
  // Leads
  listLeads: (params: {
    search?: string;
    status?: string;
    source?: string;
    stage?: string;
    has_replied?: boolean;
    page?: number;
    page_size?: number;
  } = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
    });
    return apiFetch<{ total: number; page: number; page_size: number; items: Lead[] }>(
      `${BASE}/leads?${q.toString()}`
    );
  },

  getLead: (id: number) => apiFetch<LeadDetail>(`${BASE}/leads/${id}`),

  createLead: (data: Partial<Lead>) =>
    apiFetch<Lead>(`${BASE}/leads`, { method: "POST", body: JSON.stringify(data) }),

  patchLead: (id: number, data: Partial<Lead>) =>
    apiFetch<Lead>(`${BASE}/leads/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  deleteLead: (id: number) =>
    apiFetch<void>(`${BASE}/leads/${id}`, { method: "DELETE" }),

  leadAction: (id: number, body: {
    action: "send_email" | "pause" | "resume" | "mark_replied" | "mark_unsubscribed";
    template_key?: string;
    campaign_id?: number;
    custom_subject?: string;
    custom_body?: string;
  }) =>
    apiFetch<{ status: string }>(`${BASE}/leads/${id}/actions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Campaigns
  listCampaigns: () => apiFetch<Campaign[]>(`${BASE}/campaigns`),
  createCampaign: (data: Partial<Campaign>) =>
    apiFetch<Campaign>(`${BASE}/campaigns`, { method: "POST", body: JSON.stringify(data) }),
  patchCampaign: (id: number, data: Partial<Campaign>) =>
    apiFetch<Campaign>(`${BASE}/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  campaignLeads: (id: number) => apiFetch<Lead[]>(`${BASE}/campaigns/${id}/leads`),

  // Templates
  listTemplates: () => apiFetch<Template[]>(`${BASE}/templates`),
  patchTemplate: (id: number, data: Partial<Template>) =>
    apiFetch<Template>(`${BASE}/templates/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Stats + settings
  stats: () => apiFetch<Stats>(`${BASE}/stats`),
  getSettings: () => apiFetch<Settings>(`${BASE}/settings`),
  patchSettings: (data: Partial<Settings> & { n8n_api_key?: string }) =>
    apiFetch<Settings>(`${BASE}/settings`, { method: "PATCH", body: JSON.stringify(data) }),
};

// React Query keys for easy cache invalidation
export const leadGenKeys = {
  all: ["lead-gen"] as const,
  leads: (params?: unknown) => ["lead-gen", "leads", params] as const,
  lead: (id: number) => ["lead-gen", "lead", id] as const,
  campaigns: () => ["lead-gen", "campaigns"] as const,
  templates: () => ["lead-gen", "templates"] as const,
  stats: () => ["lead-gen", "stats"] as const,
  settings: () => ["lead-gen", "settings"] as const,
};
