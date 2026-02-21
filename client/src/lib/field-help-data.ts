/**
 * Field help data for financial metrics and inputs
 * Maps field names to help content including source, usage, and tips
 */

export interface FieldHelpContent {
  label: string
  description: string
  source: string | string[]
  usedFor: string[]
  tip?: string
}

export const FIELD_HELP_MAP: Record<string, FieldHelpContent> = {
  // Core Input Fields
  cashOnHand: {
    label: "Cash on Hand",
    description: "The total amount of liquid cash your company currently has in bank accounts and accessible funds.",
    source: ["Manual entry", "Bank connectors", "Accounting software"],
    usedFor: [
      "Runway calculation",
      "Burn rate analysis",
      "Cash flow projections",
      "Funding requirement estimation",
    ],
    tip: "Include all liquid cash. Exclude restricted funds, stock, and illiquid assets.",
  },

  monthlyRevenue: {
    label: "Monthly Revenue (MRR)",
    description: "Total recurring monthly revenue from all sources including subscription fees, usage-based revenue, and other recurring income streams.",
    source: ["Manual entry", "Stripe", "QuickBooks", "Salesforce"],
    usedFor: [
      "Runway calculation",
      "Growth rate metrics",
      "Profitability analysis",
      "Unit economics",
      "Fundraising projections",
    ],
    tip: "Include all recurring revenue sources. Use average of last 3 months if variable.",
  },

  totalMonthlyExpenses: {
    label: "Total Monthly Expenses",
    description: "Sum of all monthly operating expenses including payroll, marketing, infrastructure, and cost of goods sold.",
    source: ["Manual entry", "Accounting software", "Expense tracking systems"],
    usedFor: [
      "Burn rate calculation",
      "Runway analysis",
      "Profitability assessment",
      "Budget tracking",
    ],
    tip: "Use average monthly expenses for consistency. Include both fixed and variable costs.",
  },

  payrollExpenses: {
    label: "Payroll Expenses",
    description: "Total monthly cost of employee salaries, benefits, taxes, and other payroll-related expenses.",
    source: ["Manual entry", "Payroll systems", "Accounting software"],
    usedFor: [
      "Expense breakdown",
      "Burn rate calculation",
      "Headcount impact analysis",
      "Cost reduction scenarios",
    ],
    tip: "Include salaries, benefits, payroll taxes, and contractor payments.",
  },

  marketingExpenses: {
    label: "Marketing Expenses",
    description: "Monthly spending on customer acquisition, advertising, marketing campaigns, content creation, and promotional activities.",
    source: ["Manual entry", "Marketing platforms", "Accounting software"],
    usedFor: [
      "Customer acquisition cost (CAC) calculation",
      "Marketing efficiency analysis",
      "Expense optimization",
      "Growth scaling scenarios",
    ],
    tip: "Track CAC separately to measure marketing efficiency and ROI.",
  },

  operatingExpenses: {
    label: "Operating Expenses",
    description: "Monthly expenses for general business operations including rent, utilities, software subscriptions, insurance, and administrative costs.",
    source: ["Manual entry", "Accounting software", "Expense management tools"],
    usedFor: [
      "Burn rate calculation",
      "Overhead analysis",
      "Expense optimization",
      "Profitability modeling",
    ],
    tip: "Separate from COGS. Focus on fixed costs that don't scale with revenue.",
  },

  cogsExpenses: {
    label: "Cost of Goods Sold (COGS)",
    description: "Direct costs of producing goods or delivering services, including materials, hosting, payment processing fees, and direct labor.",
    source: ["Manual entry", "Accounting software", "Inventory systems"],
    usedFor: [
      "Gross margin calculation",
      "Unit economics",
      "Pricing strategy",
      "Profitability analysis",
    ],
    tip: "Only include variable costs that scale directly with revenue. Use % of revenue if absolute values vary.",
  },

  // Calculated/Derived Fields
  monthlyGrowthRate: {
    label: "Monthly Growth Rate",
    description: "The month-over-month percentage increase in revenue, calculated as (current MRR - previous MRR) / previous MRR.",
    source: ["Calculated from revenue history"],
    usedFor: [
      "Company valuation",
      "Runway predictions",
      "Unit economics assessment",
      "Growth benchmarking",
      "Funding conversations",
    ],
    tip: "Annualized growth rate is typically used: (1 + monthly growth)^12 - 1. Track last 3 months for smoothing.",
  },

  churnRate: {
    label: "Churn Rate",
    description: "The percentage of customers or revenue lost each month. Calculated as (customers lost / starting customers) or (revenue lost / starting revenue).",
    source: ["Manual entry", "Analytics platforms", "Billing systems"],
    usedFor: [
      "LTV calculation",
      "Runway projections",
      "Growth rate adjustments",
      "Unit economics",
      "Customer health assessment",
    ],
    tip: "Track both customer churn and revenue churn separately. Monthly churn compounds significantly over time.",
  },

  totalCustomers: {
    label: "Total Customers",
    description: "The current number of active customers paying for your product or service.",
    source: ["Manual entry", "CRM systems", "Billing platforms"],
    usedFor: [
      "Unit economics calculation",
      "CAC and LTV metrics",
      "Growth tracking",
      "Churn analysis",
    ],
    tip: "Define 'active customer' clearly (e.g., paying in last 30 days). Track separately from free/trial users.",
  },

  headcount: {
    label: "Headcount / Employees",
    description: "Total number of full-time employees and full-time equivalent contractors currently employed by the company.",
    source: ["Manual entry", "HR systems", "Payroll systems"],
    usedFor: [
      "Payroll expense estimation",
      "Team velocity analysis",
      "Runway calculations",
      "Fundraising metrics",
    ],
    tip: "Use FTE (full-time equivalent) for contractors. Track hiring/attrition plans in scenarios.",
  },

  // Financial Metrics
  runway: {
    label: "Runway",
    description: "The number of months your company can operate with current cash and monthly burn rate before depleting all cash reserves.",
    source: ["Calculated: Cash on Hand / Monthly Burn Rate"],
    usedFor: [
      "Funding urgency assessment",
      "Fundraising timeline",
      "Hiring/expense planning",
      "Strategic decision-making",
    ],
    tip: "Target runway of 12-18 months is typical. Include salary continuity and critical expense scenarios.",
  },

  burnRate: {
    label: "Burn Rate",
    description: "The monthly rate at which the company is spending cash. Calculated as monthly expenses minus monthly revenue.",
    source: ["Calculated: Monthly Expenses - Monthly Revenue"],
    usedFor: [
      "Runway calculation",
      "Profitability timeline",
      "Expense optimization",
      "Funding requirement",
    ],
    tip: "Negative burn rate means profitability! Track gross burn (expenses) and net burn separately.",
  },

  burnMultiple: {
    label: "Burn Multiple",
    description: "Ratio of money spent to money earned. Calculated as gross burn / MRR. Measures efficiency of growth spending.",
    source: ["Calculated: Monthly Expenses / Monthly Revenue"],
    usedFor: [
      "Efficiency benchmarking",
      "Growth sustainability",
      "Venture capital assessment",
      "Expense optimization",
    ],
    tip: "Lower burn multiple is better (1.5x is good for growth stage). Subtract payroll separately for 'magic number'.",
  },

  grossMargin: {
    label: "Gross Margin",
    description: "Percentage of revenue remaining after subtracting COGS. Calculated as (MRR - COGS) / MRR * 100.",
    source: ["Calculated from Revenue and COGS"],
    usedFor: [
      "Unit economics assessment",
      "Pricing strategy",
      "Profitability potential",
      "Scaling feasibility",
      "Venture fundability",
    ],
    tip: "Higher gross margins (70%+) are better. SaaS typically targets 80%+ gross margins.",
  },

  cac: {
    label: "Customer Acquisition Cost (CAC)",
    description: "Average cost to acquire one customer. Calculated as marketing spend / new customers acquired.",
    source: ["Calculated from Marketing Spend and New Customers"],
    usedFor: [
      "Unit economics",
      "Marketing efficiency",
      "Pricing sustainability",
      "Growth scaling",
    ],
    tip: "CAC should be significantly less than LTV (typically 3:1 or better). Include all acquisition channels.",
  },

  ltv: {
    label: "Customer Lifetime Value (LTV)",
    description: "Total profit generated from a customer over their entire relationship with the company.",
    source: ["Calculated: ARPU × (1 - Churn Rate) / Churn Rate"],
    usedFor: [
      "Unit economics",
      "Pricing decisions",
      "Profitability analysis",
      "Growth investment decisions",
    ],
    tip: "LTV should be 3-5x CAC for sustainable growth. Higher LTV justifies higher CAC.",
  },

  ltvCacRatio: {
    label: "LTV:CAC Ratio",
    description: "Relationship between lifetime value and customer acquisition cost. Calculated as LTV / CAC.",
    source: ["Calculated: LTV / CAC"],
    usedFor: [
      "Unit economics health assessment",
      "Growth sustainability check",
      "Venture capital evaluation",
    ],
    tip: "Healthy SaaS companies have 3:1 or higher ratio. Below 1:1 means unprofitable growth.",
  },

  // Data Quality Metrics
  dataConfidenceScore: {
    label: "Data Confidence Score",
    description: "Weighted score (0-100) reflecting confidence in the accuracy and completeness of your financial data.",
    source: ["Calculated from data source mix and verification status"],
    usedFor: [
      "Data quality assessment",
      "Decision-making confidence",
      "Audit readiness",
      "Stakeholder trust building",
    ],
    tip: "Manually verified data scores higher. Sync connectors regularly to maintain accuracy.",
  },

  qualityOfGrowthIndex: {
    label: "Quality of Growth Index",
    description: "Measure of how sustainable and healthy your growth is, considering unit economics, retention, and margin expansion.",
    source: ["Calculated from growth rate, churn, CAC, and LTV"],
    usedFor: [
      "Sustainable growth assessment",
      "Strategic pivoting decisions",
      "Investor confidence building",
      "Growth strategy validation",
    ],
    tip: "High quality growth has high LTV:CAC, low churn, and positive contribution margin per customer.",
  },
}

/**
 * Get help content for a specific field
 * Returns null if field is not found in map
 */
export function getFieldHelp(fieldName: string): FieldHelpContent | null {
  return FIELD_HELP_MAP[fieldName] || null
}

/**
 * Get all field names for a specific source type
 */
export function getFieldsBySource(sourceType: "manual" | "calculated" | "connector"): string[] {
  return Object.entries(FIELD_HELP_MAP)
    .filter(([, data]) => {
      const source = Array.isArray(data.source) ? data.source : [data.source]
      if (sourceType === "manual") return source.some(s => s.includes("Manual"))
      if (sourceType === "calculated") return source.some(s => s.includes("Calculated"))
      if (sourceType === "connector") return source.some(s => ["Stripe", "QuickBooks", "Salesforce", "Bank", "Accounting", "CRM", "Analytics", "Billing", "Payroll", "HR"].some(c => s.includes(c)))
      return false
    })
    .map(([key]) => key)
}
