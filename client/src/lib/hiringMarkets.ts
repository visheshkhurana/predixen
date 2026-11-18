/**
 * Hiring-planner salary markets.
 *
 * The planner's role library holds US (San Francisco) salary bands in USD.
 * Most FounderConsole companies are not in San Francisco: the primary user is
 * an Indian D2C brand. So the market (locations, salary level, currency) is
 * picked from the company's currency instead of always defaulting to SF/USD.
 *
 * `salaryFactor` turns a US band into the local band in the local currency.
 * These are rough market midpoints, not FX conversions (a Bengaluru engineer
 * is not paid a San Francisco salary times the rupee rate).
 */

export interface HiringLocation {
  id: string;
  label: string;
  multiplier: number;
}

export interface HiringMarket {
  /** Currency the salaries are shown and saved in. */
  currency: string;
  /** Multiplier from the US (USD) role bands to this market's bands. */
  salaryFactor: number;
  /** Equipment + onboarding per hire, in `currency`. */
  oneTimePerHire: number;
  oneTimeLabel: string;
  locations: HiringLocation[];
  /** True when the company's currency had no market and the US one is shown. */
  fallback?: boolean;
  /**
   * Annual pay bands per role id in this market's currency, where we have
   * them. Used instead of `salaryFactor`, which overstates junior roles
   * (a US SDR × 18 is ₹10.8L; Indian SDRs are typically ₹4–7L).
   */
  roleBands?: Record<string, [number, number]>;
  /** Short note on where the bands come from, shown in the planner. */
  bandsNote?: string;
}

const L = 100_000; // one lakh

/**
 * Indicative annual CTC at Indian startups (Bengaluru, 2026), from public
 * salary reports and job postings. Ranges, not offers: the planner says so.
 */
const INR_ROLE_BANDS: Record<string, [number, number]> = {
  "senior-engineer": [25 * L, 40 * L],
  "staff-engineer": [40 * L, 65 * L],
  "engineering-manager": [40 * L, 60 * L],
  cto: [60 * L, 100 * L],
  sdr: [4 * L, 7 * L],
  ae: [8 * L, 15 * L],
  "sales-manager": [15 * L, 25 * L],
  "vp-sales": [40 * L, 70 * L],
  "marketing-manager": [15 * L, 25 * L],
  "content-marketer": [5 * L, 9 * L],
  "growth-marketer": [10 * L, 18 * L],
  "performance-marketer": [8 * L, 16 * L],
  "creative-designer": [5 * L, 10 * L],
  pm: [20 * L, 35 * L],
  "product-designer": [12 * L, 24 * L],
  "category-manager": [10 * L, 18 * L],
  "office-manager": [4 * L, 7 * L],
  "hr-manager": [10 * L, 18 * L],
  "finance-manager": [12 * L, 22 * L],
  "supply-chain-manager": [12 * L, 20 * L],
  "warehouse-associate": [2.4 * L, 3.6 * L],
  csm: [6 * L, 10 * L],
  "support-rep": [3 * L, 4.5 * L],
  "cx-executive": [2.8 * L, 4 * L],
  "vp-cs": [30 * L, 50 * L],
  "head-of-ops": [25 * L, 40 * L],
};

const US: HiringMarket = {
  currency: "USD",
  salaryFactor: 1,
  oneTimePerHire: 3000,
  oneTimeLabel: "Equipment $2K + onboarding $1K per hire",
  locations: [
    { id: "sf", label: "San Francisco", multiplier: 1.0 },
    { id: "ny", label: "New York", multiplier: 0.95 },
    { id: "remote-us", label: "Remote US", multiplier: 0.85 },
    { id: "international", label: "International", multiplier: 0.7 },
  ],
};

const MARKETS: Record<string, HiringMarket> = {
  USD: US,
  INR: {
    currency: "INR",
    // Only used for a role with no band below.
    salaryFactor: 18,
    roleBands: INR_ROLE_BANDS,
    bandsNote: "Indicative Bengaluru startup CTC ranges for 2026, not offers. Edit the monthly cost if you know the real figure.",
    oneTimePerHire: 150000,
    oneTimeLabel: "Laptop ₹1L + onboarding ₹50K per hire",
    locations: [
      { id: "bengaluru", label: "Bengaluru", multiplier: 1.0 },
      { id: "mumbai", label: "Mumbai", multiplier: 1.0 },
      { id: "delhi-ncr", label: "Delhi NCR", multiplier: 0.95 },
      { id: "pune-hyderabad", label: "Pune / Hyderabad", multiplier: 0.9 },
      { id: "remote-india", label: "Remote India", multiplier: 0.8 },
    ],
  },
  AED: {
    currency: "AED",
    salaryFactor: 2,
    oneTimePerHire: 11000,
    oneTimeLabel: "Equipment + onboarding about AED 11K per hire",
    locations: [
      { id: "dubai", label: "Dubai", multiplier: 1.0 },
      { id: "abu-dhabi", label: "Abu Dhabi", multiplier: 0.95 },
      { id: "remote-uae", label: "Remote UAE", multiplier: 0.85 },
    ],
  },
  SGD: {
    currency: "SGD",
    salaryFactor: 0.85,
    oneTimePerHire: 4000,
    oneTimeLabel: "Equipment + onboarding about S$4K per hire",
    locations: [
      { id: "singapore", label: "Singapore", multiplier: 1.0 },
      { id: "remote-sea", label: "Remote SE Asia", multiplier: 0.6 },
    ],
  },
  GBP: {
    currency: "GBP",
    salaryFactor: 0.5,
    oneTimePerHire: 2500,
    oneTimeLabel: "Equipment + onboarding about £2.5K per hire",
    locations: [
      { id: "london", label: "London", multiplier: 1.0 },
      { id: "uk-other", label: "Rest of UK", multiplier: 0.85 },
      { id: "remote-uk", label: "Remote UK", multiplier: 0.85 },
    ],
  },
  EUR: {
    currency: "EUR",
    salaryFactor: 0.45,
    oneTimePerHire: 2800,
    oneTimeLabel: "Equipment + onboarding about €2.8K per hire",
    locations: [
      { id: "berlin", label: "Berlin", multiplier: 1.0 },
      { id: "amsterdam", label: "Amsterdam", multiplier: 1.05 },
      { id: "remote-eu", label: "Remote EU", multiplier: 0.85 },
    ],
  },
};

/** The salary market for a company currency; unknown currencies get the US market in USD. */
export function hiringMarketFor(currency: string | null | undefined): HiringMarket {
  const code = (currency || "USD").trim().toUpperCase();
  const market = MARKETS[code];
  if (market) return market;
  return { ...US, fallback: true };
}

/** A US (USD) annual salary converted to the market's local band. */
export function localSalary(usdAnnual: number, market: HiringMarket): number {
  return Math.round(usdAnnual * market.salaryFactor);
}

/** Monthly cost of one hire at a location in the market. */
export function monthlySalaryFor(
  usdMin: number,
  usdMax: number,
  market: HiringMarket,
  locationId: string,
): number {
  const loc = market.locations.find((l) => l.id === locationId) ?? market.locations[0];
  const avg = localSalary((usdMin + usdMax) / 2, market);
  return Math.round((avg * loc.multiplier) / 12);
}

export interface RoleLike {
  id: string;
  salaryMin: number;
  salaryMax: number;
}

/** Annual band for a role in the market: a local band when we have one, else the US band scaled. */
export function roleBand(role: RoleLike, market: HiringMarket): [number, number] {
  const local = market.roleBands?.[role.id];
  if (local) return [Math.round(local[0]), Math.round(local[1])];
  return [localSalary(role.salaryMin, market), localSalary(role.salaryMax, market)];
}

/** Monthly cost of one hire of `role` at a location in the market. */
export function monthlyCostForRole(role: RoleLike, market: HiringMarket, locationId: string): number {
  const loc = market.locations.find((l) => l.id === locationId) ?? market.locations[0];
  const [min, max] = roleBand(role, market);
  return Math.round((((min + max) / 2) * loc.multiplier) / 12);
}
