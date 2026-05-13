export interface IndustryProfile {
  slug: string;
  name: string;
  shortName: string;
  defaultBurn: number;
  defaultRevenue: number;
  grossMargin: number;
  growthRate: number;
  benchmarkRunway: string;
  notes: string[];
  burnMultipleNotes: string;
  fundraisingNotes: string;
  primaryRiskFactors: string[];
}

export const RUNWAY_INDUSTRIES: IndustryProfile[] = [
  {
    slug: "saas",
    name: "SaaS Startup Runway Calculator",
    shortName: "SaaS",
    defaultBurn: 80000,
    defaultRevenue: 30000,
    grossMargin: 78,
    growthRate: 12,
    benchmarkRunway: "18-24 months at seed; 12-18 months at Series A",
    notes: [
      "SaaS investors expect 18+ months of runway at any given time post Series A.",
      "Net revenue retention above 110% materially extends effective runway.",
      "Target a burn multiple under 2x — anything above 3x is a hard fundraising signal.",
    ],
    burnMultipleNotes:
      "For SaaS, burn multiple = net new ARR / net burn. Top-quartile seed companies operate at 0.5x-1.5x. Above 2.5x and the next round becomes very hard.",
    fundraisingNotes:
      "Begin a Series A process when you have 9-12 months of runway, $1M+ ARR, and growing 3x year-over-year. Below those thresholds, extend runway first.",
    primaryRiskFactors: [
      "Sales-led ramps that haven't caught up to ramp time (>6 months).",
      "Net revenue retention dropping below 100%.",
      "Outsized engineering hiring before product-market fit.",
    ],
  },
  {
    slug: "ecommerce",
    name: "Ecommerce Startup Runway Calculator",
    shortName: "Ecommerce",
    defaultBurn: 60000,
    defaultRevenue: 120000,
    grossMargin: 38,
    growthRate: 8,
    benchmarkRunway: "12-18 months — inventory cycles compress runway fast",
    notes: [
      "Inventory absorbs cash before revenue lands. Treat inventory days outstanding as a runway lever.",
      "Cash conversion cycle, not just net burn, is the real runway constraint.",
      "Returns and RTO (return-to-origin) above 25% can silently double effective CAC.",
    ],
    burnMultipleNotes:
      "Ecommerce runway is dominated by working capital. A 60-day inventory cycle plus 30-day payment terms can lock 90 days of revenue away from your bank account.",
    fundraisingNotes:
      "Most ecommerce founders raise debt or revenue-based financing, not equity, to fund inventory. Equity is for brand and channel investment.",
    primaryRiskFactors: [
      "Channel concentration on a single ad platform.",
      "Rising shipping and fulfillment cost per order.",
      "COD orders with high RTO percentage in cash-on-delivery markets.",
    ],
  },
  {
    slug: "fintech",
    name: "Fintech Startup Runway Calculator",
    shortName: "Fintech",
    defaultBurn: 120000,
    defaultRevenue: 50000,
    grossMargin: 65,
    growthRate: 10,
    benchmarkRunway: "24+ months — regulatory ramps are long",
    notes: [
      "Compliance and licensing add 6-18 months before revenue. Plan runway accordingly.",
      "Float and interchange-based revenue look great on paper but tie to interest-rate cycles.",
      "Customer acquisition cost in fintech is among the highest in tech — payback often exceeds 24 months.",
    ],
    burnMultipleNotes:
      "Fintechs are usually evaluated on contribution margin per active user rather than burn multiple. Aim for positive contribution margin within 18 months.",
    fundraisingNotes:
      "Series A fintechs typically raise on a path to a banking, lending, or insurance license. Expect 30-50% more dilution than equivalent SaaS.",
    primaryRiskFactors: [
      "Regulatory delays in primary market.",
      "Loan-loss provisions exceeding underwriting model.",
      "Interchange or float compression in macro downturn.",
    ],
  },
  {
    slug: "marketplace",
    name: "Marketplace Startup Runway Calculator",
    shortName: "Marketplace",
    defaultBurn: 100000,
    defaultRevenue: 25000,
    grossMargin: 72,
    growthRate: 15,
    benchmarkRunway: "18-30 months — liquidity is the bottleneck",
    notes: [
      "Liquidity in one geography or category beats global mediocrity. Optimize for cohort liquidity not GMV.",
      "Take rate compression is the silent killer. Defend it before scaling.",
      "Most marketplace failures are supply, not demand. Track supply density per market.",
    ],
    burnMultipleNotes:
      "Marketplaces should track contribution margin after subsidies. Negative contribution margin should never be intentional past Series A.",
    fundraisingNotes:
      "Investors look for a single liquid geography or category before funding scale. A marketplace at $5M GMV in one city beats $20M spread across ten.",
    primaryRiskFactors: [
      "Demand-supply imbalance in core market.",
      "Take rate erosion driven by competition.",
      "High subsidy spend per transaction.",
    ],
  },
  {
    slug: "ai",
    name: "AI Startup Runway Calculator",
    shortName: "AI",
    defaultBurn: 150000,
    defaultRevenue: 40000,
    grossMargin: 52,
    growthRate: 18,
    benchmarkRunway: "12-18 months — inference cost moves fast",
    notes: [
      "Inference cost per query is a moving target. Lock contracts where possible.",
      "Gross margin under 50% triggers VC concern — model an aggressive cost-down path.",
      "Foundation model dependency is a real risk; plan for multi-vendor fallback.",
    ],
    burnMultipleNotes:
      "AI startups are often evaluated on revenue growth + gross margin trajectory together. 4x year-over-year growth with margins improving from 40% to 60% is fundable.",
    fundraisingNotes:
      "AI Series A rounds are uniquely sensitive to gross margin and inference cost trajectory. Expect a deeper gross margin diligence than SaaS.",
    primaryRiskFactors: [
      "Inference cost per call drifting up.",
      "Foundation model price increases or API deprecation.",
      "Fast-following competitors with similar prompts.",
    ],
  },
  {
    slug: "hardware",
    name: "Hardware Startup Runway Calculator",
    shortName: "Hardware",
    defaultBurn: 200000,
    defaultRevenue: 60000,
    grossMargin: 35,
    growthRate: 6,
    benchmarkRunway: "24-36 months — production cycles are long",
    notes: [
      "Tooling and inventory deposits are runway-killers. Build a 24-month cash plan.",
      "Customer deposits and pre-orders are the cheapest capital. Use them.",
      "BOM cost-down per unit is the only path to defensible gross margin.",
    ],
    burnMultipleNotes:
      "Hardware companies should track gross margin per unit, not blended. Investors care about path to 50%+ at scale.",
    fundraisingNotes:
      "Hardware Series A typically requires a working prototype, signed letters of intent, and a manufacturing partner. Expect a longer process than software.",
    primaryRiskFactors: [
      "BOM cost increases from supply chain.",
      "Production yield issues from contract manufacturers.",
      "Inventory write-down risk from version churn.",
    ],
  },
  {
    slug: "biotech",
    name: "Biotech Startup Runway Calculator",
    shortName: "Biotech",
    defaultBurn: 350000,
    defaultRevenue: 0,
    grossMargin: 0,
    growthRate: 0,
    benchmarkRunway: "24-36 months between value-inflection milestones",
    notes: [
      "Biotech runway is measured by milestones, not months. Plan to the next value inflection.",
      "Non-dilutive grants (NIH, SBIR) materially extend runway.",
      "Tranched financings are normal — model worst-case tranche release.",
    ],
    burnMultipleNotes:
      "Biotech burn is judged by milestone risk-adjusted: cost per IND, cost per Phase I readout, cost per pivotal trial.",
    fundraisingNotes:
      "Series A biotech rounds typically fund to the next value inflection point (preclinical -> IND, IND -> Phase I) with 6 months of buffer.",
    primaryRiskFactors: [
      "Trial timeline slippage.",
      "Regulatory feedback delays.",
      "CRO cost overruns.",
    ],
  },
  {
    slug: "devtools",
    name: "Developer Tools Startup Runway Calculator",
    shortName: "Devtools",
    defaultBurn: 90000,
    defaultRevenue: 20000,
    grossMargin: 80,
    growthRate: 14,
    benchmarkRunway: "18-24 months with strong PLG motion",
    notes: [
      "Bottom-up adoption and weekly active developers matter more than ARR in early stage.",
      "Self-serve to enterprise expansion is the runway extender — design for it from day one.",
      "Open-source contributor community has a measurable revenue impact at Series A.",
    ],
    burnMultipleNotes:
      "Devtools are evaluated on weekly active developers, free-to-paid conversion, and self-serve ARR percentage. Burn multiple targets are similar to SaaS (under 2x).",
    fundraisingNotes:
      "Investors want to see signs of bottom-up adoption: GitHub stars, npm/PyPI downloads, free-to-paid conversion above 2%.",
    primaryRiskFactors: [
      "Single-platform dependency (e.g., GitHub-only).",
      "Free user growth without paid conversion.",
      "Enterprise sales cycle longer than expected.",
    ],
  },
];

export function getIndustry(slug: string): IndustryProfile | undefined {
  return RUNWAY_INDUSTRIES.find((i) => i.slug === slug);
}
