import { apiRequest } from "@/lib/queryClient";

export interface ConnectorMetadata {
  id: string;
  name: string;
  category: string;
  logoUrl?: string;
  description: string;
  longDescription?: string;
  authType: string;
  supportsWebhooks: boolean;
  supportsPolling: boolean;
  supportsIncremental: boolean;
  typicalRefresh: string;
  native: boolean;
  beta: boolean;
  popularityRank: number;
  setupComplexity: string;
  documentationUrl?: string;
  implemented: boolean;
  adapterKey?: string;
  metricsUnlocked: string[];
  requiredPermissions: string[];
  dataCollected: string[];
}

export interface ConnectorStatus {
  connectorId: string;
  status: "active" | "error" | "paused" | "not_installed";
  lastSync: string | null;
  nextSync: string | null;
  errorSummary: string | null;
  recordCount: number;
}

export interface CatalogConnector extends ConnectorMetadata {
  installStatus?: ConnectorStatus | null;
}

export interface Category {
  name: string;
  count: number;
}

function snakeToCamel(obj: any): any {
  if (obj === null || obj === undefined) return obj;
  if (Array.isArray(obj)) return obj.map(snakeToCamel);
  if (typeof obj !== 'object') return obj;
  
  const result: any = {};
  for (const key of Object.keys(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    result[camelKey] = snakeToCamel(obj[key]);
  }
  return result;
}

export async function fetchConnectorCatalog(params?: {
  category?: string;
  nativeOnly?: boolean;
  implementedOnly?: boolean;
  companyId?: number;
}): Promise<CatalogConnector[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.nativeOnly) searchParams.set("native_only", "true");
  if (params?.implementedOnly) searchParams.set("implemented_only", "true");
  if (params?.companyId) searchParams.set("company_id", String(params.companyId));
  
  const url = `/api/connectors/catalog${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
  const token = localStorage.getItem("predixen-token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error("Failed to fetch connector catalog");
  const data = await response.json();
  return snakeToCamel(data);
}

export async function fetchConnectorDetail(connectorId: string): Promise<CatalogConnector> {
  const token = localStorage.getItem("predixen-token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(`/api/connectors/catalog/${connectorId}`, { headers });
  if (!response.ok) throw new Error(`Failed to fetch connector ${connectorId}`);
  const data = await response.json();
  return snakeToCamel(data);
}

export async function fetchCategories(): Promise<Category[]> {
  const token = localStorage.getItem("predixen-token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch("/api/connectors/categories", { headers });
  if (!response.ok) throw new Error("Failed to fetch categories");
  return response.json();
}
