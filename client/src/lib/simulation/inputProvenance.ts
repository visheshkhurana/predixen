export type ProvenanceKind = "entered" | "synced" | "assumed";

export interface ProvenanceEntry {
  kind?: string;
  source?: string;
  synced_at?: string;
}

export type InputProvenanceMap = Record<string, ProvenanceEntry>;

export interface ProvenanceGroups {
  entered: string[];
  synced: string[];
  assumed: string[];
}

const FIELD_ORDER = [
  "monthly_revenue",
  "monthly_burn",
  "cash_balance",
  "growth_rate",
  "customers",
  "churn_rate",
  "team_size",
  "total_rounds",
  "funding_climate",
  "market_growth",
  "market_volatility",
  "team_morale",
  "product_quality",
  "market_fit",
  "brand_reputation",
  "investor_confidence",
];

export const FIELD_LABELS: Record<string, string> = {
  monthly_revenue: "Monthly revenue",
  monthly_burn: "Monthly burn",
  cash_balance: "Cash on hand",
  growth_rate: "Monthly growth",
  customers: "Customers",
  churn_rate: "Churn",
  team_size: "Headcount",
  total_rounds: "Simulation months",
  funding_climate: "Funding climate",
  market_growth: "Market growth",
  market_volatility: "Market volatility",
  team_morale: "Team morale",
  product_quality: "Product quality",
  market_fit: "Market fit",
  brand_reputation: "Brand reputation",
  investor_confidence: "Investor confidence",
};

const MONEY_FIELDS = new Set(["monthly_revenue", "monthly_burn", "cash_balance"]);
const RATE_FIELDS = new Set([
  "growth_rate",
  "churn_rate",
  "funding_climate",
  "market_growth",
  "market_volatility",
  "team_morale",
  "product_quality",
  "market_fit",
  "brand_reputation",
  "investor_confidence",
]);

function sortFields(names: string[]): string[] {
  return [...names].sort((a, b) => {
    const ia = FIELD_ORDER.indexOf(a);
    const ib = FIELD_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib) || a.localeCompare(b);
  });
}

export function fieldLabel(name: string): string {
  return FIELD_LABELS[name] ?? name.replace(/_/g, " ");
}

/**
 * Group only fields the response actually classified.
 * Missing provenance, an empty map, and unknown kinds produce nothing —
 * an unknown field is never treated as entered.
 */
export function groupInputProvenance(
  provenance: InputProvenanceMap | null | undefined,
): ProvenanceGroups | null {
  if (!provenance || typeof provenance !== "object" || Array.isArray(provenance)) return null;

  const entered: string[] = [];
  const synced: string[] = [];
  const assumed: string[] = [];

  for (const [name, entry] of Object.entries(provenance)) {
    if (!entry || typeof entry !== "object") continue;
    if (entry.kind === "entered") entered.push(name);
    else if (entry.kind === "synced") synced.push(name);
    else if (entry.kind === "assumed") assumed.push(name);
  }

  if (entered.length + synced.length + assumed.length === 0) return null;
  return {
    entered: sortFields(entered),
    synced: sortFields(synced),
    assumed: sortFields(assumed),
  };
}

export function formatInputValue(name: string, value: number): string {
  if (MONEY_FIELDS.has(name)) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (RATE_FIELDS.has(name)) {
    const pct = Math.round(value * 1000) / 10;
    const text = Number.isInteger(pct) ? String(pct) : pct.toFixed(1);
    return `${text}%`;
  }
  if (name === "total_rounds") return `${value} mo`;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}

/** Format a sync timestamp in the viewer's local timezone. */
export function formatSyncedAtLocal(
  iso: string,
  locale?: string,
  timeZone?: string,
): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone,
  }).format(date);
}

export function valuesFromSimulationResult(
  result: {
    initial_state?: Record<string, number> | null;
    total_rounds?: number;
  },
  controls?: {
    fundingClimate?: number;
    marketGrowth?: number;
    marketVolatility?: number;
  },
): Record<string, number> {
  const state = result.initial_state || {};
  const values: Record<string, number> = {};
  const assign = (name: string, value: unknown) => {
    if (typeof value === "number" && Number.isFinite(value)) values[name] = value;
  };
  assign("monthly_revenue", state.mrr);
  assign("monthly_burn", state.burn_rate);
  assign("cash_balance", state.cash);
  assign("customers", state.customers);
  assign("churn_rate", state.churn_rate);
  assign("team_size", state.team_size);
  assign("growth_rate", state.growth_rate);
  assign("team_morale", state.team_morale);
  assign("product_quality", state.product_quality);
  assign("market_fit", state.market_fit);
  assign("brand_reputation", state.brand_reputation);
  assign("investor_confidence", state.investor_confidence);
  assign("total_rounds", result.total_rounds);
  assign("funding_climate", controls?.fundingClimate);
  assign("market_growth", controls?.marketGrowth);
  assign("market_volatility", controls?.marketVolatility);
  return values;
}
