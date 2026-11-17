/**
 * One list of industries and stages for onboarding, the Data page and
 * Settings → Company. Values must stay keys of INDUSTRY_ALIASES /
 * STAGE_ALIASES in server/core/taxonomy.py (or benchmark keys themselves).
 */
export const INDUSTRY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "general_saas", label: "SaaS" },
  { value: "ai", label: "AI / ML products" },
  { value: "fintech", label: "Fintech" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "d2c", label: "D2C / Consumer" },
  { value: "marketplace", label: "Marketplace" },
  { value: "healthcare", label: "Healthcare / BioTech" },
  { value: "edtech", label: "EdTech" },
  { value: "agritech", label: "AgriTech" },
  { value: "deeptech", label: "DeepTech / Hardware" },
  { value: "climate", label: "Climate / CleanTech" },
  { value: "media", label: "Media / Entertainment" },
  { value: "logistics", label: "Logistics / Supply Chain" },
  { value: "real_estate", label: "Real Estate / PropTech" },
  { value: "food", label: "Food / CPG" },
  { value: "agency", label: "Agency / services" },
  { value: "startup", label: "Early-stage / pre-revenue" },
  { value: "other", label: "Other" },
];

export const STAGE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "bootstrapped", label: "Bootstrapped" },
  { value: "pre_seed", label: "Pre-seed" },
  { value: "seed", label: "Seed" },
  { value: "pre_series_a", label: "Pre-Series A" },
  { value: "series_a", label: "Series A" },
  { value: "series_b", label: "Series B+" },
  { value: "growth", label: "Growth Stage" },
  { value: "pre_ipo", label: "Pre-IPO" },
  { value: "public", label: "Public / Listed" },
];

export const CURRENCY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "INR", label: "₹ Indian Rupee (INR)" },
  { value: "USD", label: "$ US Dollar (USD)" },
  { value: "AED", label: "AED UAE Dirham" },
  { value: "SGD", label: "S$ Singapore Dollar (SGD)" },
  { value: "GBP", label: "£ British Pound (GBP)" },
  { value: "EUR", label: "€ Euro (EUR)" },
];
