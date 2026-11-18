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
}

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
    // Senior engineer US midpoint $175K -> about ₹31.5L in Bengaluru.
    salaryFactor: 18,
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
