import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { trackEvent } from "@/lib/posthog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FadeIn } from '@/components/ui/motion-primitives';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RefreshCw,
  Link2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Database,
  Shield,
  ArrowRight,
  FileText,
  Users,
  DollarSign,
  AlertTriangle,
  Loader2,
  Zap,
  TrendingUp,
  Settings,
  Briefcase,
  Bell,
  Truck,
  CreditCard,
  Megaphone,
  KeyRound,
  Download,
} from "lucide-react";
import { SiQuickbooks, SiXero, SiHubspot, SiStripe } from "react-icons/si";
import { FaSalesforce } from "react-icons/fa"; // simple-icons dropped the Salesforce mark in react-icons 5.7
import { apiRequest } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/errors";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";
import { parseServerDate } from "@/lib/serverDate";

import { IntegrationCard, ApiKeyConnectModal, StripeConnectModal, SlackLinkCard } from "@/components/integrations";
import { useFounderStore } from "@/store/founderStore";
import { SoftwareSpendCard } from "@/components/SoftwareSpendCard";
import { CrmPipelineCard } from "@/components/CrmPipelineCard";
import { WebTrafficCard } from "@/components/WebTrafficCard";
import { 
  IntegrationConfig, 
  getIntegrationsByCategory,
} from "@/lib/integrations";

interface IntegrationProvider {
  id: string;
  name: string;
  description: string;
  features: string[];
  comingSoon?: boolean;
}

interface SyncDetails {
  records_synced: number;
  last_error: string | null;
}

interface IntegrationStatus {
  available: string[];
  connected: string | null;
  last_sync: string | null;
  sync_details?: SyncDetails;
}

interface ConnectorMetadata extends IntegrationProvider {
  setupTime: "~5 min" | "~10 min" | "~15 min";
  category: "recommended" | "revenue" | "accounting" | "hr" | "analytics" | "crm" | "captable" | "security" | "other";
  isRecommended?: boolean;
}

type ConnectorCategory = "all" | "recommended" | "revenue" | "accounting" | "hr" | "analytics" | "crm" | "captable" | "security" | "other";

// Catalog id first. razorpayx_payroll is the old id; connections saved under it still resolve.
const RAZORPAYX_IDS = ["razorpayx", "razorpayx_payroll"];

const providerIcons: Record<string, React.ReactNode> = {
  quickbooks: <SiQuickbooks className="h-6 w-6" />,
  xero: <SiXero className="h-6 w-6" />,
  salesforce: <FaSalesforce className="h-6 w-6" />,
  hubspot: <SiHubspot className="h-6 w-6" />,
  stripe: <SiStripe className="h-6 w-6" />,
  plaid: <Link2 className="h-6 w-6" />,
  gusto: <DollarSign className="h-6 w-6" />,
  netsuite: <Database className="h-6 w-6" />,
  pipedrive: <Users className="h-6 w-6" />,
  zoho_crm: <Briefcase className="h-6 w-6" />,
  zoho: <Users className="h-6 w-6" />,
  zoho_books: <FileText className="h-6 w-6" />,
  tally: <Database className="h-6 w-6" />,
  shiprocket: <Truck className="h-6 w-6" />,
  razorpay: <CreditCard className="h-6 w-6" />,
  meta_ads: <Megaphone className="h-6 w-6" />,
  google_ads: <Megaphone className="h-6 w-6" />,
  google_analytics: <TrendingUp className="h-6 w-6" />,
  onepassword: <KeyRound className="h-6 w-6" />,
  razorpayx: <DollarSign className="h-6 w-6" />,
  greythr: <Users className="h-6 w-6" />,
  keka: <Users className="h-6 w-6" />,
  bamboohr: <Users className="h-6 w-6" />,
  peoplestrong: <Users className="h-6 w-6" />,
  quikchex: <DollarSign className="h-6 w-6" />,
  deskera: <Database className="h-6 w-6" />,
  sap_b1: <Database className="h-6 w-6" />,
  odoo: <Database className="h-6 w-6" />,
  marg: <Database className="h-6 w-6" />,
};

const integrationBenefits: Record<string, { dataImported: string[]; permissions: string[] }> = {
  razorpay: {
    dataImported: [
      "Captured payments for the last full month (India time)",
      "Gateway fees, excluding the GST on them",
      "Refunds and payment-method mix (UPI, card, netbanking, wallet)",
    ],
    permissions: [
      "Read access to payments with your key id and secret",
      "FounderConsole only reads payments; it never creates refunds or payouts",
    ],
  },
  meta_ads: {
    dataImported: [
      "Monthly ad spend per ad account (last 3 full months)",
      "Impressions and clicks",
      "Purchases and purchase value as Meta reports them (shown as platform-reported, not revenue)",
    ],
    permissions: [
      "ads_read on the ad accounts you list",
      "Read-only: cannot create, change or pause ads",
    ],
  },
  google_ads: {
    dataImported: [
      "Monthly ad spend per Google Ads account (last 3 full months)",
      "Impressions and clicks",
      "Conversions and conversion value as Google reports them (shown as platform-reported, not revenue)",
    ],
    permissions: [
      "Google's Google Ads access (it has no read-only option)",
      "FounderConsole only reads reports: it never creates, changes or pauses campaigns",
    ],
  },
  google_analytics: {
    dataImported: [
      "Monthly sessions, users and new users from one GA4 property",
      "Key events (GA4's conversions) per month",
      "If you can see several properties, the busiest one is picked",
    ],
    permissions: [
      "Google Analytics read-only access (analytics.readonly)",
      "FounderConsole never changes Analytics settings, properties or users",
    ],
  },
  onepassword: {
    dataImported: [
      "Active users in the last 30 days (people who signed in)",
      "Sign-ins and failed sign-ins by reason (wrong password, MFA, firewall)",
      "Seat utilization and monthly seat cost, if you enter your seat price",
    ],
    permissions: [
      "An Events Reporting token with sign-in attempts access",
      "Read-only: FounderConsole never sees vault items or passwords",
    ],
  },
  quickbooks: {
    dataImported: [
      "Revenue & expense transactions",
      "Chart of accounts",
      "Invoice & payment history",
      "Bank account balances",
      "Profit & loss statements",
    ],
    permissions: [
      "Read financial reports",
      "Access transaction history",
      "View company information",
    ],
  },
  xero: {
    dataImported: [
      "Bank transactions",
      "Invoices & bills",
      "Expense claims",
      "Financial reports",
      "Contact information",
    ],
    permissions: [
      "Read bank transactions",
      "Access invoices",
      "View financial reports",
    ],
  },
  salesforce: {
    dataImported: [
      "Opportunity pipeline",
      "Account & contact data",
      "Revenue forecasts",
      "Deal stage history",
      "Win/loss analytics",
    ],
    permissions: [
      "Read CRM data",
      "Access opportunity records",
      "View account information",
    ],
  },
  hubspot: {
    dataImported: [
      "Deal pipeline",
      "Contact & company records",
      "Revenue attribution",
      "Sales activities",
      "Marketing analytics",
    ],
    permissions: [
      "Read CRM data",
      "Access deal records",
      "View contact information",
    ],
  },
  netsuite: {
    dataImported: [
      "Financial statements",
      "Revenue recognition",
      "Multi-subsidiary data",
      "Budget vs actuals",
      "Cash flow analysis",
    ],
    permissions: [
      "Read financial data",
      "Access reports",
      "View company records",
    ],
  },
  pipedrive: {
    dataImported: [
      "Deal pipeline",
      "Contact database",
      "Activity history",
      "Revenue projections",
      "Sales metrics",
    ],
    permissions: [
      "Read deals",
      "Access contacts",
      "View activities",
    ],
  },
  zoho_crm: {
    dataImported: [
      "Open pipeline by stage, and weighted pipeline",
      "Deals won and lost in the last 30 days, 90-day win rate",
      "Deals won this month (as this month's revenue from Zoho CRM)",
      "Account and contact counts",
    ],
    permissions: [
      "Sign in with Zoho: read-only access to deals, accounts, contacts and org settings",
      "FounderConsole never creates or edits CRM records",
    ],
  },
  stripe: {
    dataImported: [
      "Subscription revenue (MRR/ARR)",
      "Payment transactions",
      "Customer billing data",
      "Churn & retention metrics",
      "Invoice history",
    ],
    permissions: [
      "Read payment data",
      "Access subscription info",
      "View customer records",
    ],
  },
  plaid: {
    dataImported: [
      "Bank account balances",
      "Transaction history (30+ days)",
      "Cash inflow & outflow",
      "Account types & institutions",
      "Real-time balance updates",
    ],
    permissions: [
      "Read account balances",
      "Access transaction history",
      "View account information",
    ],
  },
  gusto: {
    dataImported: [
      "Employee headcount & roles",
      "Payroll run amounts",
      "Total compensation costs",
      "Employer tax obligations",
      "Benefits & deductions",
    ],
    permissions: [
      "Read employee data",
      "Access payroll records",
      "View company information",
    ],
  },
  razorpayx: {
    dataImported: [
      "Processed salary payouts (INR)",
      "Active employee contacts",
    ],
    permissions: [
      "Read RazorpayX contacts",
      "Read RazorpayX payouts",
    ],
  },
  greythr: {
    dataImported: [
      "Employee directory",
      "Leave & attendance",
      "Salary structures",
      "Payroll history",
      "Expense claims",
    ],
    permissions: [
      "Read employee records",
      "Access payroll data",
      "View attendance logs",
    ],
  },
  bamboohr: {
    dataImported: [
      "Headcount, by department and employment type",
      "Hires and exits in the last 30 and 90 days, and 90-day attrition",
      "Monthly salary run-rate from current pay rates (salaried staff)",
    ],
    permissions: [
      "A BambooHR API key: it reads what its user can see",
      "Read-only: FounderConsole never changes employee records",
    ],
  },
  keka: {
    dataImported: [
      "Employee profiles",
      "Payroll runs",
      "Time tracking data",
      "Performance data",
      "Expense management",
    ],
    permissions: [
      "Read employee data",
      "Access payroll info",
      "View time logs",
    ],
  },
  zoho_books: {
    dataImported: [
      "Chart of accounts",
      "Invoices & bills",
      "Ledger entries",
      "Bank transactions",
      "GST reports",
    ],
    permissions: [
      "Read accounting data",
      "Access invoices",
      "View reports",
    ],
  },
  tally: {
    dataImported: [
      "Ledger accounts",
      "Voucher entries",
      "Stock items",
      "Financial reports",
      "GST data",
    ],
    permissions: [
      "Read accounting data",
      "Access vouchers",
      "View reports",
    ],
  },
  woocommerce: {
    dataImported: [
      "Order history & revenue",
      "Product catalog",
      "Customer records",
      "COD/Prepaid split analysis",
      "Shipping & refund data",
    ],
    permissions: [
      "Read orders & products",
      "Access customer data",
      "View sales analytics",
    ],
  },
};

const connectorMetadata: Record<string, { setupTime: "~5 min" | "~10 min" | "~15 min"; category: ConnectorCategory; isRecommended?: boolean }> = {
  stripe: { setupTime: "~5 min", category: "revenue", isRecommended: true },
  quickbooks: { setupTime: "~10 min", category: "accounting", isRecommended: true },
  xero: { setupTime: "~10 min", category: "accounting" },
  gusto: { setupTime: "~10 min", category: "hr", isRecommended: true },
  rippling: { setupTime: "~15 min", category: "hr" },
  deel: { setupTime: "~10 min", category: "hr" },
  salesforce: { setupTime: "~15 min", category: "crm" },
  hubspot: { setupTime: "~10 min", category: "crm" },
  pipedrive: { setupTime: "~10 min", category: "crm" },
  zoho_crm: { setupTime: "~5 min", category: "crm" },
  plaid: { setupTime: "~5 min", category: "revenue" },
  chargebee: { setupTime: "~10 min", category: "revenue" },
  paddle: { setupTime: "~10 min", category: "revenue" },
  shopify: { setupTime: "~10 min", category: "revenue" },
  woocommerce: { setupTime: "~10 min", category: "revenue" },
  shiprocket: { setupTime: "~5 min", category: "revenue" },
  razorpay: { setupTime: "~5 min", category: "revenue" },
  meta_ads: { setupTime: "~10 min", category: "analytics" },
  google_ads: { setupTime: "~5 min", category: "analytics" },
  google_analytics: { setupTime: "~5 min", category: "analytics" },
  onepassword: { setupTime: "~5 min", category: "security" },
  brex: { setupTime: "~5 min", category: "revenue" },
  netsuite: { setupTime: "~15 min", category: "accounting" },
  wave: { setupTime: "~10 min", category: "accounting" },
  freshbooks: { setupTime: "~10 min", category: "accounting" },
  mercury: { setupTime: "~5 min", category: "revenue" },
  ramp: { setupTime: "~5 min", category: "revenue" },
  recurly: { setupTime: "~5 min", category: "revenue" },
  profitwell: { setupTime: "~5 min", category: "revenue" },
  close_crm: { setupTime: "~5 min", category: "crm" },
  zoho_books: { setupTime: "~10 min", category: "accounting" },
  tally: { setupTime: "~15 min", category: "accounting" },
  razorpayx: { setupTime: "~10 min", category: "hr" },
  greythr: { setupTime: "~10 min", category: "hr" },
  keka: { setupTime: "~10 min", category: "hr" },
  bamboohr: { setupTime: "~5 min", category: "hr" },
  peoplestrong: { setupTime: "~15 min", category: "hr" },
  quikchex: { setupTime: "~10 min", category: "hr" },
  deskera: { setupTime: "~15 min", category: "accounting" },
  sap_b1: { setupTime: "~15 min", category: "accounting" },
  odoo: { setupTime: "~15 min", category: "accounting" },
  marg: { setupTime: "~15 min", category: "accounting" },
  carta: { setupTime: "~10 min", category: "captable" },
  pulley: { setupTime: "~10 min", category: "captable" },
  angellist_stack: { setupTime: "~10 min", category: "captable" },
  shareworks: { setupTime: "~15 min", category: "captable" },
  ledgy: { setupTime: "~10 min", category: "captable" },
};

const categoryLabels: Record<ConnectorCategory, { label: string; description: string; icon: React.ReactNode }> = {
  all: { label: "All Connectors", description: "All available integrations", icon: <Link2 className="h-4 w-4" /> },
  recommended: { label: "Recommended", description: "Best for getting started quickly", icon: <Zap className="h-4 w-4" /> },
  revenue: { label: "Revenue & Payments", description: "Payment processing and revenue tracking", icon: <DollarSign className="h-4 w-4" /> },
  accounting: { label: "Accounting", description: "Financial and accounting software", icon: <Database className="h-4 w-4" /> },
  hr: { label: "HR & Payroll", description: "Payroll and HR management systems", icon: <Users className="h-4 w-4" /> },
  analytics: { label: "Analytics", description: "Product and business analytics", icon: <TrendingUp className="h-4 w-4" /> },
  crm: { label: "CRM & Sales", description: "Customer relationship management", icon: <Briefcase className="h-4 w-4" /> },
  captable: { label: "Cap Table", description: "Cap table and equity management platforms", icon: <FileText className="h-4 w-4" /> },
  security: { label: "Security & IT", description: "Seat usage and security signals next to your software spend", icon: <Shield className="h-4 w-4" /> },
  other: { label: "Other", description: "Additional data sources", icon: <Link2 className="h-4 w-4" /> },
};

const additionalAccountingProviders: IntegrationProvider[] = [
  {
    id: "freshbooks",
    name: "FreshBooks",
    description: "Invoicing, expenses and payments for service businesses",
    features: ["Invoices", "Expenses", "Payments", "Read-only"],
  },
  {
    id: "wave",
    name: "Wave",
    description: "Invoices, accounts and transactions from Wave (Pro or Advisor plan)",
    features: ["Invoices", "Chart of Accounts", "Transactions", "Read-only"],
  },
  {
    id: "netsuite",
    name: "NetSuite",
    description: "Oracle NetSuite ERP for enterprise accounting",
    features: ["Multi-subsidiary", "Revenue Recognition", "Advanced Reporting"],
  },
  {
    id: "zoho_books",
    name: "Zoho Books",
    description: "Cloud accounting for growing businesses",
    features: ["Invoices & Payments", "Expenses", "Ledger & Journal Entries", "GST Compliance"],
  },
  {
    id: "tally",
    name: "Tally ERP",
    description: "On-premise accounting and ERP for Indian businesses",
    features: ["Ledger Accounts", "Vouchers", "Stock Items", "GST Reports"],
  },
];

const additionalCrmProviders: IntegrationProvider[] = [
  {
    id: "close_crm",
    name: "Close",
    description: "Leads and opportunities from Close CRM",
    features: ["Opportunities", "Won Revenue", "Leads", "Read-only"],
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    description: "Deal pipeline from Pipedrive: open pipeline by stage, win rate, and deals won",
    features: ["Pipeline by Stage", "Win Rate", "Won Deals", "Read-only"],
  },
  {
    id: "zoho_crm",
    name: "Zoho CRM",
    description: "Deal pipeline from Zoho CRM: open pipeline by stage, win rate, and deals won this month",
    features: ["Pipeline by Stage", "Win Rate", "Won Deals", "Read-only"],
  },
];

const payrollProviders: IntegrationProvider[] = [
  {
    id: "rippling",
    name: "Rippling",
    description: "Workers, departments and compensation from Rippling",
    features: ["Headcount", "Departments", "Compensation", "Read-only"],
  },
  {
    id: "deel",
    name: "Deel",
    description: "Contractors and employees worldwide, with what Deel invoices you",
    features: ["Headcount", "Worker Pay", "Deel Fees", "Read-only"],
  },
  {
    id: "gusto",
    name: "Gusto",
    description: "US payroll, benefits, and HR platform for modern businesses",
    features: ["Employee Costs", "Payroll Runs", "Headcount Tracking", "Tax Obligations"],
  },
  {
    id: "razorpayx",
    name: "RazorpayX Payroll",
    description: "Salary payouts and employee contacts from RazorpayX",
    features: ["Processed salary payouts", "Employee headcount", "INR payroll cost"],
  },
  {
    id: "greythr",
    name: "GreytHR",
    description: "Full-suite HRMS and payroll management",
    features: ["Employee Data", "Leave & Attendance", "Salary Structures", "Payroll Processing"],
  },
  {
    id: "bamboohr",
    name: "BambooHR",
    description: "Headcount, hires and exits, and salary run-rate from BambooHR",
    features: ["Headcount", "Hires & Exits", "Attrition", "Salary Run-rate"],
  },
  {
    id: "keka",
    name: "Keka HR",
    description: "Modern HR and payroll platform",
    features: ["Employee Management", "Payroll Runs", "Time Tracking", "Expense Management"],
  },
  {
    id: "peoplestrong",
    name: "PeopleStrong",
    description: "Enterprise HR and talent management",
    features: ["HR Analytics", "Payroll", "Talent Acquisition", "Workforce Management"],
    comingSoon: true,
  },
  {
    id: "quikchex",
    name: "QuikChex",
    description: "Cloud payroll for Indian SMEs",
    features: ["Payroll Processing", "Statutory Compliance", "Employee Self-Service"],
    comingSoon: true,
  },
];

const erpProviders: IntegrationProvider[] = [
  {
    id: "deskera",
    name: "Deskera",
    description: "All-in-one business management software",
    features: ["Accounting", "Inventory", "CRM", "Payroll"],
    comingSoon: true,
  },
  {
    id: "sap_b1",
    name: "SAP Business One",
    description: "Enterprise ERP for small and midsize businesses",
    features: ["Financial Management", "Supply Chain", "Operations", "Analytics"],
    comingSoon: true,
  },
  {
    id: "odoo",
    name: "Odoo",
    description: "Open-source business applications suite",
    features: ["Accounting", "Inventory", "Sales", "Manufacturing"],
    comingSoon: true,
  },
  {
    id: "marg",
    name: "Marg ERP",
    description: "GST-ready business software for India",
    features: ["Billing", "Inventory", "GST Filing", "Financial Reports"],
    comingSoon: true,
  },
];

const paymentsProviders: IntegrationProvider[] = [
  {
    id: "mercury",
    name: "Mercury",
    description: "Startup bank balances and transactions from Mercury",
    features: ["Cash Balance", "Transactions", "Multi-Account", "Read-only"],
  },
  {
    id: "brex",
    name: "Brex",
    description: "Cash balances, card spend and transfers from Brex",
    features: ["Cash Balance", "Card Spend", "Software Spend", "Read-only"],
  },
  {
    id: "ramp",
    name: "Ramp",
    description: "Card transactions, reimbursements and bills from Ramp",
    features: ["Card Spend", "Reimbursements", "Bills", "Software Spend"],
  },
  {
    id: "chargebee",
    name: "Chargebee",
    description: "Subscription MRR and invoices from Chargebee",
    features: ["MRR", "Paid Invoices", "Subscriptions", "Read-only"],
  },
  {
    id: "recurly",
    name: "Recurly",
    description: "Subscriptions, invoices and collections from Recurly",
    features: ["Subscriptions", "Collections", "Refunds", "Read-only"],
  },
  {
    id: "profitwell",
    name: "ProfitWell",
    description: "MRR, churn and subscriber metrics from ProfitWell (Paddle)",
    features: ["MRR", "Churn", "Customers", "Read-only"],
  },
  {
    id: "stripe",
    name: "Stripe",
    description: "Payment processing and subscription billing data",
    features: ["MRR/ARR Tracking", "Churn Analytics", "Payment History", "Revenue Recognition"],
  },
  {
    id: "plaid",
    name: "Plaid",
    description: "Bank account connections for real-time balances and transactions",
    features: ["Bank Balances", "Transaction History", "Cash Flow Analysis", "Multi-Account Support"],
  },
  {
    id: "shopify",
    name: "Shopify",
    description: "E-commerce platform for online stores and retail",
    features: ["Order Revenue", "COD/Prepaid Split", "Product Catalog", "Shipping & Refund Tracking"],
  },
  {
    id: "woocommerce",
    name: "WooCommerce",
    description: "WordPress e-commerce for D2C brands and online stores",
    features: ["Order Revenue", "COD/Prepaid Split", "Customer Data", "Return Rate Analysis"],
  },
  {
    id: "shiprocket",
    name: "Shiprocket",
    description: "Shipping for Indian D2C: what shipped, what came back (RTO), and what freight cost",
    features: ["RTO Rate", "Freight per Order", "COD Share", "Customer Returns"],
  },
  {
    id: "razorpay",
    name: "Razorpay",
    description: "Payment gateway fees for Indian D2C: what Razorpay kept from last month's prepaid orders, for CM2 on the Profit screen",
    features: ["Gateway Fee %", "Fees ex-GST", "Refunds", "UPI/Card Mix"],
  },
  {
    id: "meta_ads",
    name: "Meta Ads",
    description: "Facebook and Instagram ad spend per month, for CM3 and MER on the Profit screen. Meta's own purchase numbers are shown as platform-reported, not as revenue.",
    features: ["Monthly Ad Spend", "MER vs Platform ROAS", "Multiple Ad Accounts", "Read-only"],
  },
  {
    id: "google_ads",
    name: "Google Ads",
    description: "Search, Shopping, Performance Max and YouTube ad spend per month, for CM3 and MER. Google's own conversion numbers are shown as platform-reported, not as revenue.",
    features: ["Monthly Ad Spend", "All Accounts You Can Access", "Sign in with Google", "Read-only"],
  },
  {
    id: "google_analytics",
    name: "Google Analytics",
    description: "Monthly sessions, users and key events from your GA4 property, shown next to revenue and ad spend. Read-only.",
    features: ["Sessions & Users", "Key Events", "Busiest Property Picked", "Read-only"],
  },
];

const securityProviders: IntegrationProvider[] = [
  {
    id: "onepassword",
    name: "1Password",
    description: "1Password Business seat usage and sign-in security: who's active, failed sign-ins, and what unused seats cost.",
    features: ["Active Users", "Failed Sign-ins", "Seat Utilization", "Read-only"],
  },
];

const capTableProviders: IntegrationProvider[] = [
  {
    id: "carta",
    name: "Carta",
    description: "Leading cap table management and equity platform",
    features: ["Shareholders", "Equity Plans", "409A Valuations", "Waterfall Analysis"],
  },
  {
    id: "pulley",
    name: "Pulley",
    description: "Modern cap table management for startups",
    features: ["Cap Table", "Equity Grants", "Scenario Modeling", "Tax Optimization"],
  },
  {
    id: "angellist_stack",
    name: "AngelList Stack",
    description: "Equity management and fund administration",
    features: ["Equity Management", "Fund Admin", "SAFEs & Convertibles", "Investor Updates"],
  },
  {
    id: "shareworks",
    name: "Shareworks (Morgan Stanley)",
    description: "Enterprise equity compensation management",
    features: ["Equity Compensation", "RSUs & Options", "Compliance", "Global Plans"],
  },
  {
    id: "ledgy",
    name: "Ledgy",
    description: "Equity management platform for European startups",
    features: ["Cap Table", "ESOP Management", "Scenario Modeling", "Investor Relations"],
  },
];

function getConnectorCategory(providerId: string): ConnectorCategory {
  return connectorMetadata[providerId]?.category || "other";
}

function getConnectorSetupTime(providerId: string): "~5 min" | "~10 min" | "~15 min" {
  return connectorMetadata[providerId]?.setupTime || "~10 min";
}

function shouldShowConnector(provider: IntegrationProvider, selectedCategory: ConnectorCategory): boolean {
  if (selectedCategory === "all") return true;
  const connectorCategory = getConnectorCategory(provider.id);
  if (selectedCategory === "recommended") {
    return connectorMetadata[provider.id]?.isRecommended || false;
  }
  return connectorCategory === selectedCategory;
}

function getProviderType(providerId: string): "accounting" | "crm" | "payments" | "payroll" | "erp" | "captable" {
  if (capTableProviders.some(p => p.id === providerId)) return "captable";
  if (payrollProviders.some(p => p.id === providerId)) return "payroll";
  if (erpProviders.some(p => p.id === providerId)) return "erp";
  if (paymentsProviders.some(p => p.id === providerId)) return "payments";
  if (additionalCrmProviders.some(p => p.id === providerId)) return "crm";
  return "accounting";
}

export default function IntegrationsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const companyId = useFounderStore((s) => s.currentCompany?.id) ?? 0;
  // The Slack card always uses the signed-in user's current company.
  const slackCompanyId = companyId;
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);
  const [selectedConnectorCategory, setSelectedConnectorCategory] = useState<ConnectorCategory>("all");
  
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationConfig | null>(null);
  const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false);
  const [stripeModalOpen, setStripeModalOpen] = useState(false);
  const [googleAdsStarting, setGoogleAdsStarting] = useState(false);

  // Google Ads connects through Google sign-in, not a pasted key, and only
  // once the server has its developer token and OAuth client.
  const { data: googleAdsConfig } = useQuery<{ configured: boolean }>({
    queryKey: ["/api/connectors/google-ads/config"],
    staleTime: 5 * 60_000,
  });
  const googleAdsConfigured = !!googleAdsConfig?.configured;

  const startGoogleAds = async () => {
    if (!companyId) return;
    setGoogleAdsStarting(true);
    try {
      const res = await apiRequest("GET", `/api/connectors/companies/${companyId}/google-ads/oauth-url`);
      const { url } = await res.json();
      window.location.href = url;
    } catch (error) {
      setGoogleAdsStarting(false);
      toast({ title: "Couldn't start Google sign-in", description: getErrorMessage(error, "Try again"), variant: "destructive" });
    }
  };

  // Meta Ads connects through Facebook Login for Business when the server has
  // the Meta app set up; otherwise the card falls back to pasting a token.
  const [metaAdsStarting, setMetaAdsStarting] = useState(false);
  const { data: metaAdsConfig } = useQuery<{ configured: boolean }>({
    queryKey: ["/api/connectors/meta-ads/config"],
    staleTime: 5 * 60_000,
  });
  const metaAdsOAuth = !!metaAdsConfig?.configured;

  const startMetaAds = async () => {
    if (!companyId) return;
    setMetaAdsStarting(true);
    try {
      const res = await apiRequest("GET", `/api/connectors/companies/${companyId}/meta-ads/oauth-url`);
      const { url } = await res.json();
      window.location.href = url;
    } catch (error) {
      setMetaAdsStarting(false);
      toast({ title: "Couldn't start Facebook sign-in", description: getErrorMessage(error, "Try again"), variant: "destructive" });
    }
  };

  // Zoho Books, QuickBooks, Xero, Gusto and Salesforce connect through the
  // provider's own sign-in once the server has that provider's OAuth app.
  const [oauthStarting, setOauthStarting] = useState<string | null>(null);
  const { data: oauthProviders } = useQuery<Record<string, { name: string; configured: boolean; sandbox?: boolean }>>({
    queryKey: ["/api/connectors/oauth/providers"],
    staleTime: 5 * 60_000,
  });
  const oauthReady = (id: string) => !!oauthProviders?.[id]?.configured;

  const startOAuth = async (providerId: string, sandbox = false) => {
    if (!companyId) return;
    setOauthStarting(providerId);
    try {
      const qs = sandbox ? "?sandbox=true" : "";
      const res = await apiRequest("GET", `/api/connectors/companies/${companyId}/oauth/${providerId}/url${qs}`);
      const { url } = await res.json();
      window.location.href = url;
    } catch (error) {
      setOauthStarting(null);
      const name = oauthProviders?.[providerId]?.name ?? "the provider";
      toast({ title: `Couldn't start ${name} sign-in`, description: getErrorMessage(error, "Try again"), variant: "destructive" });
    }
  };

  // Back from Google or Facebook: say what happened, then tidy the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const gError = params.get("google_ads_error");
    const mError = params.get("meta_ads_error");
    const oError = params.get("oauth_error");
    if (connected === "google_ads" || connected === "meta_ads") {
      const name = connected === "google_ads" ? "Google Ads" : "Meta Ads";
      toast({ title: `${name} connected`, description: "Run a sync to pull the last 3 months of spend." });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
    } else if (connected) {
      toast({ title: "Connected", description: "Run a sync to pull your data." });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
    } else if (gError) {
      toast({ title: "Google Ads not connected", description: gError, variant: "destructive" });
    } else if (mError) {
      toast({ title: "Meta Ads not connected", description: mError, variant: "destructive" });
    } else if (oError) {
      toast({ title: "Not connected", description: oError, variant: "destructive" });
    }
    if (connected || gError || mError || oError) window.history.replaceState(null, "", window.location.pathname);
  }, [companyId]);

  const spreadsheetIntegrations = getIntegrationsByCategory('spreadsheets');
  const analyticsIntegrations = getIntegrationsByCategory('analytics');

  // Only integrations with a real backend connector can be connected from these
  // cards; the rest are flagged isComingSoon in the registry and render disabled.
  const handleConnectIntegration = (integration: IntegrationConfig) => {
    if (integration.isComingSoon || !integration.connectorProviderId) return;
    setSelectedIntegration(integration);
    setApiKeyModalOpen(true);
  };

  const handleApiKeyModalClose = () => {
    setApiKeyModalOpen(false);
    setSelectedIntegration(null);
  };

  const handleApiKeyConnect = async (integrationId: string, credentials: Record<string, string>) => {
    const integration = selectedIntegration;
    const providerId = integration?.connectorProviderId;
    if (!integration || integration.id !== integrationId || !providerId) {
      throw new Error("This integration cannot be connected yet.");
    }
    if (!companyId) {
      throw new Error("Select a company before connecting a data source.");
    }
    try {
      // The server checks the credentials with the provider before saving them.
      await apiRequest("POST", `/api/connectors/companies/${companyId}/connect`, {
        provider_id: providerId,
        credentials,
      });
    } catch (error) {
      throw new Error(getErrorMessage(error, "Connection failed. Check your credentials."));
    }
    trackEvent('integration_connected', { integration_id: integrationId, auth_type: integration.authType, name: integration.name });
    toast({
      title: "Integration Connected",
      description: `${integration.name} credentials were verified and saved.`,
    });
    queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
  };

  const { data: availableIntegrations, isLoading: availableLoading } = useQuery<{
    accounting: IntegrationProvider[];
    crm: IntegrationProvider[];
  }>({
    queryKey: ["/api/integrations/available"],
  });

  const { data: status, isLoading: statusLoading } = useQuery<{
    integrations: {
      accounting: IntegrationStatus;
      crm: IntegrationStatus;
      payments?: IntegrationStatus;
    };
  }>({
    queryKey: ["/api/integrations/companies", companyId, "status"],
    enabled: !!companyId,
  });
  
  const { data: connectorStatus, isLoading: connectorStatusLoading } = useQuery<{
    company_id: number;
    connectors: Array<{
      provider_id: string;
      connected: boolean;
      last_sync: string | null;
      records_synced: number;
      error: string | null;
      needs_reauth?: boolean;
      account_hint?: string | null;
    }>;
  }>({
    queryKey: ["/api/connectors/companies", companyId, "status"],
    enabled: !!companyId,
  });

  // Status tiles: the legacy /api/integrations status only knows the old
  // QuickBooks/HubSpot/Stripe paths, so a connected Zoho CRM or Pipedrive
  // showed "CRM: Not connected". Fall back to the connector registry.
  const firstConnected = (ids: string[]) =>
    connectorStatus?.connectors
      ?.find((c) => ids.includes(c.provider_id) && c.connected)
      ?.provider_id?.replace(/_/g, " ");
  const accountingConnected =
    status?.integrations.accounting.connected ||
    firstConnected(["quickbooks", "xero", "freshbooks", "wave", "netsuite"]);
  const crmConnected =
    status?.integrations.crm.connected ||
    firstConnected(["hubspot", "salesforce", "pipedrive", "close_crm", "zoho_crm"]);
  const paymentsConnected =
    status?.integrations.payments?.connected ||
    firstConnected(["stripe", "razorpay", "chargebee", "recurly"]);

  // Only some providers have a sample to preview; offering the button on the
  // rest ended in a bare "400: Bad Request".
  const { data: sampleProviders } = useQuery<Array<{ provider_id: string }>>({
    queryKey: ["/api/connectors/sample-providers"],
  });
  const sampleProviderIds = new Set((sampleProviders ?? []).map((p) => p.provider_id));

  const connectorSyncIds = ["razorpayx", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks", "shopify", "woocommerce", "shiprocket", "razorpay", "meta_ads", "google_ads", "salesforce", "google_analytics", "pipedrive", "close_crm", "mixpanel", "mercury", "brex", "ramp", "freshbooks", "wave", "chargebee", "recurly", "rippling", "deel", "netsuite", "profitwell", "amplitude", "onepassword", "zoho_crm", "bamboohr"];
  
  const syncMutation = useMutation({
    mutationFn: async ({ type, provider }: { type: "accounting" | "crm" | "payments" | "payroll" | "erp" | "captable"; provider: string }) => {
      setSyncingProvider(provider);
      if (type === "payroll" || type === "erp" || connectorSyncIds.includes(provider)) {
        const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/sync/${provider}`);
        return res.json();
      }
      const res = await apiRequest("POST", `/api/integrations/companies/${companyId}/${type}/sync?provider=${provider}`);
      return res.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Sync Complete",
        description: `Synced ${data.records_synced} records successfully`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
      queryClient.invalidateQueries({ queryKey: [`/api/connectors/companies/${companyId}/software-spend`] });
      queryClient.invalidateQueries({ queryKey: [`/api/connectors/companies/${companyId}/crm-pipeline`] });
      setSyncingProvider(null);
    },
    onError: (error: unknown) => {
      toast({
        title: "Sync Failed",
        description: getErrorMessage(error, 'Sync operation failed'),
        variant: "destructive",
      });
      setSyncingProvider(null);
    },
  });

  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

  const disconnectMutation = useMutation({
    mutationFn: async ({ provider }: { provider: string }) => {
      setDisconnectingProvider(provider);
      const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/disconnect/${provider}`);
      return res.json();
    },
    onSuccess: () => {
      toast({ title: "Integration Disconnected", description: "The data source has been disconnected." });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
      setDisconnectingProvider(null);
    },
    onError: (error: unknown) => {
      toast({ title: "Disconnect Failed", description: getErrorMessage(error, 'Could not disconnect integration'), variant: "destructive" });
      setDisconnectingProvider(null);
    },
  });

  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  const testSampleMutation = useMutation({
    mutationFn: async (provider: string) => {
      setTestingProvider(provider);
      const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/test-sample/${provider}`);
      return res.json();
    },
    onSuccess: (data) => {
      const metrics = Object.entries(data.verification || {})
        .filter(([, v]: [string, any]) => v.stored !== null && v.stored !== undefined)
        .map(([k]: [string, any]) => k);
      toast({
        title: "Sample Preview",
        description: `${data.provider_name}: ${metrics.length} metrics would sync (${metrics.slice(0, 4).join(", ")}${metrics.length > 4 ? "..." : ""}). Nothing was saved.`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
      queryClient.invalidateQueries({ queryKey: ["/api/financials"] });
      queryClient.invalidateQueries({ queryKey: ["/api/realtime"] });
      setTestingProvider(null);
    },
    onError: (error: unknown) => {
      toast({
        title: "Sample Test Failed",
        description: getErrorMessage(error, 'Sample test failed'),
        variant: "destructive",
      });
      setTestingProvider(null);
    },
  });

  const allAccountingProviders = [
    ...(availableIntegrations?.accounting || []),
    ...additionalAccountingProviders,
  ];

  const allCrmProviders = [
    ...(availableIntegrations?.crm || []),
    ...additionalCrmProviders,
  ];

  type IntegrationType = "accounting" | "crm" | "payments" | "payroll" | "erp" | "captable";
  
  const getConnectorInfo = (providerId: string) => {
    // razorpayx_payroll is the legacy id for razorpayx; rows stored under it still count.
    const ids = RAZORPAYX_IDS.includes(providerId) ? RAZORPAYX_IDS : [providerId];
    const matches = connectorStatus?.connectors?.filter(c => ids.includes(c.provider_id)) ?? [];
    return matches.find(c => c.connected) ?? matches[0];
  };

  const isRegistryIntegrationConnected = (integration: IntegrationConfig) =>
    !!integration.connectorProviderId && !!getConnectorInfo(integration.connectorProviderId)?.connected;

  const handleDisconnectRegistryIntegration = (integrationId: string) => {
    const integration = [...spreadsheetIntegrations, ...analyticsIntegrations].find(i => i.id === integrationId);
    if (integration?.connectorProviderId) {
      disconnectMutation.mutate({ provider: integration.connectorProviderId });
    }
  };
  
  const connectorBackedIds = ["razorpayx", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks", "shopify", "woocommerce", "shiprocket", "razorpay", "meta_ads", "google_ads", "salesforce", "google_analytics", "pipedrive", "close_crm", "mixpanel", "mercury", "brex", "ramp", "freshbooks", "wave", "chargebee", "recurly", "rippling", "deel", "netsuite", "profitwell", "amplitude", "onepassword", "zoho_crm", "bamboohr"];
  
  const renderProviderCard = (provider: IntegrationProvider, type: IntegrationType) => {
    const connectorInfo = getConnectorInfo(provider.id);
    const isConnectorBacked = type === "payroll" || type === "erp" || connectorBackedIds.includes(provider.id);
    const legacyType = type === "accounting" || type === "crm" ? type : undefined;
    const isConnected = isConnectorBacked
      ? connectorInfo?.connected || false
      : type === "payments"
        ? status?.integrations.payments?.connected === provider.id
        : legacyType ? status?.integrations[legacyType]?.connected === provider.id : false;
    const integrationStatus = isConnectorBacked
      ? undefined
      : type === "payments"
        ? status?.integrations.payments
        : legacyType ? status?.integrations[legacyType] : undefined;
    const lastSync = isConnectorBacked
      ? connectorInfo?.last_sync
      : integrationStatus?.last_sync;
    const syncDetails = isConnectorBacked
      ? connectorInfo ? { records_synced: connectorInfo.records_synced, last_error: connectorInfo.error } : undefined
      : integrationStatus?.sync_details;
    const isSyncing = syncingProvider === provider.id && syncMutation.isPending;

    const setupTime = getConnectorSetupTime(provider.id);
    const isRecommended = connectorMetadata[provider.id]?.isRecommended;

    return (
      <Card key={provider.id} className="hover-elevate" data-testid={`card-integration-${provider.id}`}>
        <CardHeader className="flex flex-row items-center gap-4">
          <div className="p-2 bg-muted rounded-lg">
            {providerIcons[provider.id] || <Link2 className="h-6 w-6" />}
          </div>
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2 flex-wrap">
              {provider.name}
              {isRecommended && (
                <Badge variant="default" className="bg-amber-600 flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  Recommended
                </Badge>
              )}
              {provider.comingSoon && (
                <Badge variant="secondary" className="text-xs">
                  Coming Soon
                </Badge>
              )}
              {isConnected && (
                <Badge variant="default" className="bg-green-600">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              )}
            </CardTitle>
            <CardDescription>{provider.description}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {provider.features.map((feature) => (
              <Badge key={feature} variant="secondary" className="text-xs">
                {feature}
              </Badge>
            ))}
          </div>

          {!provider.comingSoon && (
            <div className="p-2 bg-blue-50 dark:bg-blue-950 rounded-lg flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
              <span className="text-xs text-blue-700 dark:text-blue-300">Setup time: {setupTime}</span>
            </div>
          )}

          {isConnected && (
            <SyncStatusDisplay
              lastSync={lastSync ?? null}
              syncDetails={syncDetails}
              isSyncing={isSyncing}
              accountHint={connectorInfo?.account_hint}
            />
          )}

          <div className="flex gap-2 flex-wrap">
            {provider.comingSoon || !CONNECTOR_BACKED_PROVIDERS.has(provider.id) || (provider.id === "google_ads" && !googleAdsConfigured) ? (
              <Button size="sm" variant="outline" disabled data-testid={`button-coming-soon-${provider.id}`}>
                <Clock className="h-4 w-4 mr-2" />
                Coming Soon
              </Button>
            ) : isConnected ? (
              <>
                {connectorInfo?.needs_reauth && provider.id === "google_ads" && (
                  <Button size="sm" variant="outline" onClick={startGoogleAds} disabled={googleAdsStarting} data-testid="button-reconnect-google_ads">
                    Reconnect
                  </Button>
                )}
                {connectorInfo?.needs_reauth && provider.id === "meta_ads" && metaAdsOAuth && (
                  <Button size="sm" variant="outline" onClick={startMetaAds} disabled={metaAdsStarting} data-testid="button-reconnect-meta_ads">
                    Reconnect
                  </Button>
                )}
                {connectorInfo?.needs_reauth && oauthReady(provider.id) && (
                  <Button size="sm" variant="outline" onClick={() => startOAuth(provider.id)} disabled={oauthStarting === provider.id} data-testid={`button-reconnect-${provider.id}`}>
                    Reconnect
                  </Button>
                )}
                {connectorInfo?.needs_reauth && provider.id !== "google_ads" && !(provider.id === "meta_ads" && metaAdsOAuth) && !oauthReady(provider.id) && (
                  <ConnectDialog provider={provider} type={type as React.ComponentProps<typeof ConnectDialog>["type"]} companyId={companyId} triggerLabel="Reconnect" />
                )}
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => syncMutation.mutate({ type, provider: provider.id })}
                  disabled={isSyncing}
                  data-testid={`button-sync-${provider.id}`}
                >
                  {isSyncing ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  {isSyncing ? "Syncing..." : "Sync Now"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => disconnectMutation.mutate({ provider: provider.id })}
                  disabled={disconnectingProvider === provider.id && disconnectMutation.isPending}
                  data-testid={`button-disconnect-${provider.id}`}
                >
                  {disconnectingProvider === provider.id && disconnectMutation.isPending ? "Disconnecting..." : "Disconnect"}
                </Button>
              </>
            ) : (
              <>
                {provider.id === 'stripe' ? (
                  <Button size="sm" onClick={() => setStripeModalOpen(true)} data-testid={`button-connect-${provider.id}`}>
                    <Link2 className="h-4 w-4 mr-2" />
                    Connect
                  </Button>
                ) : provider.id === 'google_ads' ? (
                  <Button size="sm" onClick={startGoogleAds} disabled={googleAdsStarting} data-testid="button-connect-google_ads">
                    {googleAdsStarting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                    Connect with Google
                  </Button>
                ) : oauthReady(provider.id) ? (
                  <>
                    <Button size="sm" onClick={() => startOAuth(provider.id)} disabled={oauthStarting === provider.id} data-testid={`button-connect-${provider.id}`}>
                      {oauthStarting === provider.id ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                      Connect with {oauthProviders?.[provider.id]?.name}
                    </Button>
                    {oauthProviders?.[provider.id]?.sandbox && (
                      <Button size="sm" variant="ghost" onClick={() => startOAuth(provider.id, true)} disabled={oauthStarting === provider.id} data-testid={`button-connect-sandbox-${provider.id}`}>
                        Sandbox org
                      </Button>
                    )}
                  </>
                ) : provider.id === 'meta_ads' && metaAdsOAuth ? (
                  <Button size="sm" onClick={startMetaAds} disabled={metaAdsStarting} data-testid="button-connect-meta_ads">
                    {metaAdsStarting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                    Connect with Facebook
                  </Button>
                ) : (
                  <ConnectDialog provider={provider} type={type} companyId={companyId} />
                )}
                {sampleProviderIds.has(provider.id) && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => testSampleMutation.mutate(provider.id)}
                  disabled={testingProvider === provider.id && testSampleMutation.isPending}
                  data-testid={`button-test-sample-${provider.id}`}
                >
                  {testingProvider === provider.id && testSampleMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Database className="h-4 w-4 mr-2" />
                  )}
                  Test with Sample Data
                </Button>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const providerMap: Record<string, IntegrationProvider> = {};
  [...allAccountingProviders, ...payrollProviders, ...paymentsProviders, ...capTableProviders].forEach((provider) => {
    providerMap[provider.id] = provider;
  });

  const recommendedProviders: IntegrationProvider[] = Object.entries(providerMap)
    .filter(([id]) => connectorMetadata[id]?.isRecommended)
    .slice(0, 3)
    .map(([, provider]) => provider);

  const getConnectorsByCategory = (category: ConnectorCategory) => {
    const allProviders = [
      ...allAccountingProviders,
      ...payrollProviders,
      ...erpProviders,
      ...allCrmProviders,
      ...paymentsProviders,
      ...capTableProviders,
      ...securityProviders,
    ];

    return allProviders.filter((p) => shouldShowConnector(p, category));
  };

  const connectorsLoading = availableLoading || (!!companyId && connectorStatusLoading);

  const getActiveConnectors = (category: ConnectorCategory) => {
    return getConnectorsByCategory(category).filter((p) => !p.comingSoon);
  };

  const getUpcomingConnectors = (category: ConnectorCategory) => {
    return getConnectorsByCategory(category).filter((p) => p.comingSoon);
  };

  const handleRequestAccess = (providerName: string) => {
    toast({
      title: "Access Requested",
      description: `You'll be notified when ${providerName} becomes available`,
    });
  };

  return (
    <FadeIn delay={0.05} duration={0.4}>
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-page-title">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your accounting, payroll, and ERP systems to import financial data automatically
        </p>
      </div>

      <SlackLinkCard companyId={slackCompanyId} />

      <CrmPipelineCard companyId={companyId} />

      <WebTrafficCard companyId={companyId} />

      <SoftwareSpendCard companyId={companyId} />

      {/* Quick Setup Banner */}
      {recommendedProviders.length > 0 && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border-blue-200 dark:border-blue-800">
          <CardHeader>
            <div className="flex items-center gap-3">
              <Zap className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <div>
                <CardTitle className="text-blue-900 dark:text-blue-100">Quick Setup</CardTitle>
                <CardDescription className="text-blue-700 dark:text-blue-300">
                  Connect your key data sources in 15 minutes
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              {recommendedProviders.map((provider) => {
                const setupTime = getConnectorSetupTime(provider.id);
                const connectorInfo = getConnectorInfo(provider.id);
                const isConnected = connectorInfo?.connected || status?.integrations[provider.id === "stripe" || provider.id === "plaid" ? "payments" : "accounting"]?.connected === provider.id;

                return (
                  <div key={provider.id} className="bg-white dark:bg-slate-900 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                    <div className="flex items-start gap-3 mb-3">
                      <div className="p-2 bg-muted rounded-lg">
                        {providerIcons[provider.id] || <Link2 className="h-5 w-5" />}
                      </div>
                      <div>
                        <h4 className="font-medium text-sm">{provider.name}</h4>
                        <p className="text-xs text-muted-foreground mt-1">{setupTime} to set up</p>
                      </div>
                    </div>
                    {isConnected ? (
                      <Badge variant="default" className="w-full justify-center bg-green-600">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Connected
                      </Badge>
                    ) : oauthReady(provider.id) ? (
                      <Button size="sm" className="w-full" onClick={() => startOAuth(provider.id)} disabled={oauthStarting === provider.id}>
                        <Link2 className="h-4 w-4 mr-2" />
                        Connect with {oauthProviders?.[provider.id]?.name}
                      </Button>
                    ) : (
                      <ConnectDialog
                        provider={provider}
                        type={provider.id === "stripe" || provider.id === "plaid" ? "payments" : "accounting"}
                        companyId={companyId}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connector Category Filter */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Data Connectors</h2>
        <div className="flex flex-wrap gap-2">
          {(["all", "recommended", "revenue", "accounting", "hr", "analytics", "crm", "captable", "security"] as const).map((category) => (
            <Button
              key={category}
              variant={selectedConnectorCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedConnectorCategory(category)}
              className="flex items-center gap-2"
            >
              {categoryLabels[category].icon}
              {categoryLabels[category].label}
            </Button>
          ))}
        </div>
      </div>

      {/* Active Integrations Grid */}
      <div className="space-y-4">
        {selectedConnectorCategory !== "all" && (
          <div className="p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">{categoryLabels[selectedConnectorCategory].description}</p>
          </div>
        )}
        {/* Until the provider list and connection status load, show placeholders:
            rendering the empty list first flashed "0 connectors" / "No connectors". */}
        {connectorsLoading ? (
          <div className="grid md:grid-cols-2 gap-4" data-testid="connectors-loading">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="p-4">
                <div className="flex items-start gap-4">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                  <Skeleton className="h-9 w-20" />
                </div>
              </Card>
            ))}
          </div>
        ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {getActiveConnectors(selectedConnectorCategory).map((provider) =>
            renderProviderCard(provider, getProviderType(provider.id))
          )}
        </div>
        )}
        {!connectorsLoading && getActiveConnectors(selectedConnectorCategory).length === 0 && getUpcomingConnectors(selectedConnectorCategory).length === 0 && (
          <div className="text-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-muted-foreground">No connectors available in this category</p>
          </div>
        )}
      </div>

      {/* Upcoming Integrations Section */}
      {getUpcomingConnectors(selectedConnectorCategory).length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold" data-testid="text-upcoming-integrations-heading">Upcoming Integrations</h2>
            <p className="text-sm text-muted-foreground">
              These integrations are currently in development. Request early access to be notified when they launch.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {getUpcomingConnectors(selectedConnectorCategory).map((provider) => {
              return (
                <Card key={provider.id} className="opacity-80" data-testid={`card-upcoming-${provider.id}`}>
                  <CardHeader className="flex flex-row items-center gap-4">
                    <div className="p-2 bg-muted rounded-lg">
                      {providerIcons[provider.id] || <Link2 className="h-6 w-6" />}
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-lg flex items-center gap-2 flex-wrap">
                        {provider.name}
                        <Badge variant="secondary" className="text-xs">
                          In Development
                        </Badge>
                      </CardTitle>
                      <CardDescription>{provider.description}</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      {provider.features.map((feature) => (
                        <Badge key={feature} variant="secondary" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRequestAccess(provider.name)}
                        data-testid={`button-request-access-${provider.id}`}
                      >
                        <Bell className="h-4 w-4 mr-2" />
                        Request Access
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      <Separator className="my-8" />

      <Tabs defaultValue="spreadsheets">
        <TabsList data-testid="tabs-integration-type" className="flex-wrap gap-1">
          <TabsTrigger value="spreadsheets" data-testid="tab-spreadsheets">Spreadsheets</TabsTrigger>
          <TabsTrigger value="analytics" data-testid="tab-analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="spreadsheets" className="space-y-4">
          <div className="mb-4 p-4 bg-muted/50 rounded-lg">
            <h3 className="font-medium mb-2">Spreadsheet Integrations</h3>
            <p className="text-sm text-muted-foreground">
              Import data from spreadsheets like Google Sheets. Perfect for custom metrics, budgets, and manual KPI tracking.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {spreadsheetIntegrations.map((integration) => {
              const connected = isRegistryIntegrationConnected(integration);
              return (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                  isConnected={connected}
                  onConnect={handleConnectIntegration}
                  onDisconnect={handleDisconnectRegistryIntegration}
                  status={connected ? 'connected' : 'disconnected'}
                />
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="mb-4 p-4 bg-muted/50 rounded-lg">
            <h3 className="font-medium mb-2">Analytics & Product Data</h3>
            <p className="text-sm text-muted-foreground">
              Connect analytics platforms to import user engagement, retention, and product metrics for your financial models.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {analyticsIntegrations.map((integration) => {
              const connected = isRegistryIntegrationConnected(integration);
              return (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                  isConnected={connected}
                  onConnect={handleConnectIntegration}
                  onDisconnect={handleDisconnectRegistryIntegration}
                  status={connected ? 'connected' : 'disconnected'}
                />
              );
            })}
          </div>
        </TabsContent>

      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Integration Status</CardTitle>
          <CardDescription>Overview of your connected data sources</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-4">
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {accountingConnected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Accounting</p>
                <p className="text-sm text-muted-foreground truncate">
                  {accountingConnected || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {connectorStatus?.connectors?.some(c => 
                  ["razorpayx", "razorpayx_payroll", "greythr", "keka", "gusto", "bamboohr", "rippling", "deel"].includes(c.provider_id) && c.connected
                ) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Payroll</p>
                <p className="text-sm text-muted-foreground truncate">
                  {connectorStatus?.connectors?.find(c => 
                    ["razorpayx", "razorpayx_payroll", "greythr", "keka", "gusto", "bamboohr", "rippling", "deel"].includes(c.provider_id) && c.connected
                  )?.provider_id?.replace(/_/g, " ") || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {connectorStatus?.connectors?.some(c => 
                  ["tally", "zoho_books"].includes(c.provider_id) && c.connected
                ) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">ERP</p>
                <p className="text-sm text-muted-foreground truncate">
                  {connectorStatus?.connectors?.find(c => 
                    ["tally", "zoho_books"].includes(c.provider_id) && c.connected
                  )?.provider_id?.replace(/_/g, " ") || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {crmConnected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">CRM</p>
                <p className="text-sm text-muted-foreground truncate">
                  {crmConnected || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {paymentsConnected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Payments</p>
                <p className="text-sm text-muted-foreground truncate">
                  {paymentsConnected || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg" data-testid="status-captable">
              <div className="p-2 bg-background rounded-full shrink-0">
                {connectorStatus?.connectors?.some(c => 
                  ["carta", "pulley", "angellist_stack", "shareworks", "ledgy"].includes(c.provider_id) && c.connected
                ) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Cap Table</p>
                <p className="text-sm text-muted-foreground truncate">
                  {connectorStatus?.connectors?.find(c => 
                    ["carta", "pulley", "angellist_stack", "shareworks", "ledgy"].includes(c.provider_id) && c.connected
                  )?.provider_id?.replace(/_/g, " ") || "Not connected"}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <ApiKeyConnectModal
        integration={selectedIntegration}
        isOpen={apiKeyModalOpen}
        onClose={handleApiKeyModalClose}
        onConnect={handleApiKeyConnect}
      />

      <StripeConnectModal
        isOpen={stripeModalOpen}
        onClose={() => setStripeModalOpen(false)}
        companyId={companyId}
        onConnected={() => {
          queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
          queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
        }}
      />
    </div>
    </FadeIn>
  );
}

function SyncStatusDisplay({ 
  lastSync, 
  syncDetails, 
  isSyncing,
  accountHint,
}: { 
  lastSync: string | null; 
  syncDetails?: SyncDetails;
  isSyncing: boolean;
  accountHint?: string | null;
}) {
  return (
    <div className="p-3 bg-muted/50 rounded-lg space-y-2">
      {accountHint && (
        <div className="flex items-center gap-2 text-sm" data-testid="saved-account-hint">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Account {accountHint}</span>
        </div>
      )}
      {isSyncing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span>Syncing data...</span>
          </div>
          <Progress value={undefined} className="h-1" />
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Last synced: {lastSync ? formatDistanceToNow(parseServerDate(lastSync), { addSuffix: true }) : "Never"}
            </span>
          </div>
          {syncDetails && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <Database className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {syncDetails.records_synced.toLocaleString()} records imported
                </span>
              </div>
              {syncDetails.last_error && (
                <div className="flex items-start gap-2 text-sm text-destructive">
                  <AlertTriangle className="h-4 w-4 mt-0.5" />
                  <span>{syncDetails.last_error}</span>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

type CredentialField = { field: string; label: string; placeholder: string; hint?: string; optional?: boolean };

// Providers that accept one of several credential sets. The connect button
// enables once every required field and at least one full set is filled.
const providerCredentialAlternatives: Record<string, string[][]> = {
  shopify: [["access_token"], ["client_id", "client_secret"]],
  mixpanel: [["service_account_user", "service_account_secret"], ["api_secret"]],
  netsuite: [["client_id", "certificate_id"], ["consumer_key", "consumer_secret", "token_id", "token_secret"]],
};

const providerCredentialFields: Record<string, CredentialField[]> = {
  razorpayx: [
    { field: "api_key", label: "API Key", placeholder: "RazorpayX Key Id" },
    { field: "api_secret", label: "API Secret", placeholder: "RazorpayX Key Secret" },
    { field: "account_number", label: "Account number", placeholder: "Customer Identifier or current account number" },
  ],
  greythr: [
    { field: "domain", label: "greytHR domain", placeholder: "acme or acme.greythr.com", hint: "The address you use to sign in to greytHR, e.g. acme.greythr.com." },
    { field: "api_access_id", label: "API Access ID (user name)", placeholder: "API user name", hint: "greytHR Admin > Settings > API Details. Ask greytHR support to enable API access if you don't see it." },
    { field: "api_secret", label: "API Secret (password)", placeholder: "API password", hint: "Shown next to the Access ID when the API user is created." },
  ],
  bamboohr: [
    { field: "company_domain", label: "BambooHR subdomain", placeholder: "acme (from acme.bamboohr.com)", hint: "The first part of your BambooHR address: acme for acme.bamboohr.com." },
    { field: "api_key", label: "API Key", placeholder: "BambooHR API key", hint: "In BambooHR: your name (top right) > API Keys > Add New Key. Use an admin's key to see everyone." },
  ],
  keka: [
    { field: "company", label: "Keka company", placeholder: "acme (from acme.keka.com)", hint: "The first part of your Keka address: acme for acme.keka.com." },
    { field: "client_id", label: "Client ID", placeholder: "Keka API Client ID", hint: "Keka > Settings > Integrations > API access (needs Keka's API add-on)." },
    { field: "client_secret", label: "Client Secret", placeholder: "Keka API Client Secret", hint: "Shown with the Client ID on the same API access page." },
    { field: "api_key", label: "API Key", placeholder: "Keka API Key", hint: "Generate it on the API access page; give it HRIS and Payroll read access." },
  ],
  zoho_books: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Zoho Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Zoho Client Secret" },
    { field: "organization_id", label: "Organization ID", placeholder: "Enter Zoho Organization ID" },
  ],
  tally: [
    { field: "tally_url", label: "Tally Server URL", placeholder: "https://tally.yourcompany.com:9000" },
    { field: "company_name", label: "Company Name", placeholder: "Enter your Tally Company name" },
  ],
  plaid: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Plaid Client ID" },
    { field: "secret", label: "Secret Key", placeholder: "Enter Plaid Secret" },
    { field: "access_token", label: "Access Token", placeholder: "access-production-... or access-sandbox-...", hint: "Sandbox or Production is read from the token's prefix." },
    { field: "environment", label: "Environment (optional)", placeholder: "production (default) or sandbox", hint: "Only needed if your token doesn't start with access-production- or access-sandbox-.", optional: true },
  ],
  hubspot: [
    { field: "access_token", label: "Private App Token", placeholder: "pat-na1-...", hint: "HubSpot stopped new legacy private apps in Oct 2026. An existing token still works; new HubSpot users should use Connect with HubSpot." },
  ],
  gusto: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Gusto Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Gusto Client Secret" },
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
    { field: "refresh_token", label: "Refresh Token", placeholder: "OAuth2 Refresh Token", hint: "Your company is detected from the token, no company UUID needed." },
  ],
  xero: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Xero Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Xero Client Secret" },
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
    { field: "refresh_token", label: "Refresh Token", placeholder: "OAuth2 Refresh Token" },
    { field: "tenant_id", label: "Tenant ID", placeholder: "Xero Organization Tenant ID" },
  ],
  stripe: [
    { field: "api_key", label: "Secret Key", placeholder: "sk_live_... or sk_test_..." },
  ],
  salesforce: [
    { field: "instance_url", label: "Instance URL", placeholder: "https://yourorg.salesforce.com" },
    { field: "access_token", label: "Access Token", placeholder: "Bearer access token" },
  ],
  google_analytics: [
    { field: "property_id", label: "GA4 Property ID", placeholder: "123456789" },
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
  ],
  pipedrive: [
    { field: "api_token", label: "API Token", placeholder: "Enter Pipedrive API Token" },
    { field: "company_domain", label: "Company Domain", placeholder: "yourcompany" },
  ],
  close_crm: [
    { field: "api_key", label: "API Key", placeholder: "Enter Close CRM API Key" },
  ],
  mixpanel: [
    { field: "project_id", label: "Project ID", placeholder: "Enter Mixpanel Project ID" },
    { field: "service_account_user", label: "Service account username", placeholder: "name.123abc.mp-service-account", hint: "Mixpanel > Organization Settings > Service Accounts. New projects have no API Secret, and Mixpanel retires API Secrets on 3 March 2027.", optional: true },
    { field: "service_account_secret", label: "Service account secret", placeholder: "Service account secret", optional: true },
    { field: "api_secret", label: "API Secret (older projects only)", placeholder: "Leave blank if you use a service account", optional: true },
    { field: "region", label: "Data residency (optional)", placeholder: "us (default), eu or in", optional: true },
  ],
  mercury: [
    { field: "api_token", label: "API Token", placeholder: "Enter Mercury API Token" },
  ],
  brex: [
    { field: "api_key", label: "User Token", placeholder: "Enter Brex User Token" },
  ],
  ramp: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Ramp Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Ramp Client Secret" },
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
  ],
  shiprocket: [
    { field: "email", label: "API User Email", placeholder: "Shiprocket > Settings > API > Create API user" },
    { field: "password", label: "API User Password", placeholder: "Password of that API user" },
  ],
  razorpay: [
    { field: "key_id", label: "Key ID", placeholder: "rzp_live_... (Razorpay Dashboard > Account & Settings > API Keys)" },
    { field: "key_secret", label: "Key Secret", placeholder: "Shown once when the key is generated" },
  ],
  meta_ads: [
    { field: "access_token", label: "Access Token (ads_read)", placeholder: "System user token from Meta Business Settings" },
    { field: "ad_account_ids", label: "Ad Account IDs", placeholder: "act_1234567890, act_2345678901" },
  ],
  shopify: [
    { field: "shop_domain", label: "Shop Domain", placeholder: "yourstore (without .myshopify.com)" },
    { field: "access_token", label: "Admin API Token (legacy custom app)", placeholder: "shpat_... (or leave blank and use Client ID + Secret)", optional: true },
    { field: "client_id", label: "Client ID (Dev Dashboard app) - or use the Admin API Token above", placeholder: "Dev Dashboard app Client ID", optional: true },
    { field: "client_secret", label: "Client Secret (Dev Dashboard app)", placeholder: "Dev Dashboard app Client Secret", optional: true },
  ],
  woocommerce: [
    { field: "store_url", label: "Store URL", placeholder: "https://yourstore.com" },
    { field: "consumer_key", label: "Consumer Key", placeholder: "ck_..." },
    { field: "consumer_secret", label: "Consumer Secret", placeholder: "cs_..." },
  ],
  mysql: [
    { field: "host", label: "Host", placeholder: "localhost or IP address" },
    { field: "port", label: "Port", placeholder: "3306" },
    { field: "database", label: "Database", placeholder: "Enter database name" },
    { field: "username", label: "Username", placeholder: "Enter MySQL username" },
    { field: "password", label: "Password", placeholder: "Enter MySQL password" },
  ],
  freshbooks: [
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
    { field: "account_id", label: "Account ID", placeholder: "Enter FreshBooks Account ID" },
  ],
  wave: [
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
  ],
  bench: [
    { field: "api_key", label: "API Key", placeholder: "Enter Bench API Key" },
  ],
  chargebee: [
    { field: "site", label: "Site Name", placeholder: "yoursite (from yoursite.chargebee.com)" },
    { field: "api_key", label: "API Key", placeholder: "Enter Chargebee API Key" },
  ],
  recurly: [
    { field: "api_key", label: "API Key", placeholder: "Enter Recurly Private API Key" },
    { field: "region", label: "Data Center (optional)", placeholder: "us (default) or eu", optional: true },
  ],
  rippling: [
    { field: "api_key", label: "API Token", placeholder: "Rippling API token", hint: "Rippling > Tools > Developer > API Tokens. Give it the workers.read scope." },
  ],
  deel: [
    { field: "api_key", label: "API Token", placeholder: "Deel API token", hint: "Deel > More > Developer > Access tokens. Organization token with people, contracts and accounting read scopes." },
  ],
  netsuite: [
    { field: "account_id", label: "Account ID", placeholder: "1234567 or 1234567_SB1", hint: "Setup > Company > Company Information > Account ID." },
    { field: "client_id", label: "Client ID", placeholder: "From the integration record", hint: "Shown once when you save the integration record.", optional: true },
    { field: "certificate_id", label: "Certificate ID", placeholder: "From OAuth 2.0 Client Credentials (M2M) Setup", hint: "NetSuite shows it after you upload the certificate above.", optional: true },
    { field: "consumer_key", label: "Consumer Key (older TBA setup only)", placeholder: "Leave blank if you use the certificate", optional: true },
    { field: "consumer_secret", label: "Consumer Secret (TBA)", placeholder: "Leave blank if you use the certificate", optional: true },
    { field: "token_id", label: "Token ID (TBA)", placeholder: "Leave blank if you use the certificate", optional: true },
    { field: "token_secret", label: "Token Secret (TBA)", placeholder: "Leave blank if you use the certificate", optional: true },
  ],
  profitwell: [
    { field: "api_token", label: "Private API Token", placeholder: "Enter ProfitWell API Token" },
  ],
  amplitude: [
    { field: "api_key", label: "API Key", placeholder: "Enter Amplitude API Key" },
    { field: "secret_key", label: "Secret Key", placeholder: "Enter Amplitude Secret Key" },
    { field: "region", label: "Data center (optional)", placeholder: "us (default) or eu", optional: true },
  ],
  onepassword: [
    { field: "bearer_token", label: "Events API token", placeholder: "Bearer token from Events Reporting", hint: "1Password > Integrations > Events Reporting. Add an integration with Sign-in attempts ticked and copy its token." },
    { field: "region", label: "Account region (optional)", placeholder: "us (default), ent, ca or eu", hint: "Where you sign in: 1password.com = us, ent.1password.com = ent, 1password.ca = ca, 1password.eu = eu.", optional: true },
    { field: "seat_price_monthly", label: "Price per seat per month (optional)", placeholder: "7.99", hint: "Adds 1Password to software spend as seats x price.", optional: true },
    { field: "seats", label: "Paid seats (optional)", placeholder: "10", hint: "Used for seat utilization. Without it, cost is based on active users.", optional: true },
  ],
};


// Providers with a real server-side connector. Anything else has no backend to
// connect to, so its card says "Coming Soon" instead of playing a fake
// "authorizing" animation and accepting any key.
export const CONNECTOR_BACKED_PROVIDERS = new Set(["google_ads", "razorpayx", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks", "salesforce", "google_analytics", "pipedrive", "close_crm", "mixpanel", "mercury", "brex", "ramp", "shopify", "woocommerce", "shiprocket", "razorpay", "meta_ads", "freshbooks", "wave", "chargebee", "recurly", "rippling", "deel", "netsuite", "profitwell", "amplitude", "onepassword", "zoho_crm", "bamboohr", "google_sheets", "rest_api"]);

const providerSetupHelp: Record<string, string> = {
  meta_ads:
    "In Meta Business Settings, open Users → System users, add a system user, assign it your ad accounts, then Generate token with the ads_read permission. Ad account IDs (act_…) are in Ads Manager's account menu.",
  shopify:
    "Shopify stopped new admin-created custom apps on 1 Jan 2026. Create an app in the Shopify Dev Dashboard with read_orders, read_all_orders and read_products, install it on your store and paste its Client ID and Client Secret. An existing legacy app's Admin API token still works.",
  razorpay:
    "In the Razorpay Dashboard, open Account & Settings → API Keys and generate a key. FounderConsole only reads payments and settlements with it.",
  netsuite:
    "In NetSuite: 1) Setup > Integration > Manage Integrations > New: tick 'Client Credentials (Machine to Machine) Grant' and 'REST Web Services', save, and copy the Client ID. 2) Download the certificate below. 3) Setup > Integration > Manage Authentication > OAuth 2.0 Client Credentials (M2M) Setup > Create New: pick a user, a role that can read accounts, invoices and transactions, and that integration; upload the certificate and copy the Certificate ID.",
};

function NetSuiteCertificate({ companyId }: { companyId: number }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/netsuite/certificate`);
      const { certificate } = await res.json();
      const url = URL.createObjectURL(new Blob([certificate], { type: "application/x-pem-file" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "founderconsole-netsuite.pem";
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast({ title: "Couldn't get the certificate", description: getErrorMessage(error, "Try again"), variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex items-center justify-between gap-3 p-3 border rounded-lg">
      <p className="text-sm text-muted-foreground">Public certificate for NetSuite. Your company's private key stays encrypted with FounderConsole.</p>
      <Button size="sm" variant="outline" onClick={download} disabled={busy} data-testid="button-netsuite-certificate">
        {busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
        Certificate
      </Button>
    </div>
  );
}

function isSecretField(field: string): boolean {
  return /secret|key|password|token/i.test(field);
}

function ConnectDialog({
  provider,
  type,
  companyId,
  triggerLabel = "Connect",
}: {
  provider: IntegrationProvider;
  type: "accounting" | "crm" | "payments" | "payroll" | "erp" | "captable";
  companyId: number;
  triggerLabel?: string;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"benefits" | "oauth" | "credentials">("benefits");
  const [apiKey, setApiKey] = useState("");
  const [oauthProgress, setOauthProgress] = useState(0);
  const [credentials, setCredentials] = useState<Record<string, string>>({});

  const credentialFields: CredentialField[] = providerCredentialFields[provider.id] || [
    { field: "api_key", label: "API Key", placeholder: "Enter API Key" },
  ];
  const filled = (field: string) => Boolean((credentials[field] || "").trim());
  const alternatives = providerCredentialAlternatives[provider.id];
  const credentialsComplete =
    credentialFields.every(cf => cf.optional || filled(cf.field)) &&
    (!alternatives || alternatives.some(set => set.every(filled)));
  

  const benefits = integrationBenefits[provider.id] || {
    dataImported: ["Financial data", "Transaction history"],
    permissions: ["Read-only access"],
  };

  const connectMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/connect`, {
        provider_id: provider.id,
        credentials,
      });
      return res.json();
    },
    onSuccess: () => {
      toast({
        title: "Connected",
        description: `Successfully connected to ${provider.name}`,
      });
      setOpen(false);
      setStep("benefits");
      setApiKey("");
      setCredentials({});
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
    },
    onError: (error: unknown) => {
      toast({
        title: "Connection Failed",
        description: getErrorMessage(error, 'Connection failed'),
        variant: "destructive",
      });
    },
  });

  const handleContinue = () => setStep("credentials");

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      setStep("benefits");
      setApiKey("");
      setOauthProgress(0);
      setCredentials({});
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid={`button-${triggerLabel.toLowerCase()}-${provider.id}`}>
          <Link2 className="h-4 w-4 mr-2" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        {step === "benefits" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {providerIcons[provider.id]}
                Connect to {provider.name}
              </DialogTitle>
              <DialogDescription>
                Import your financial data automatically to power AI-driven insights
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <FileText className="h-4 w-4 text-primary" />
                  Data that will be imported
                </div>
                <ul className="grid gap-2 text-sm text-muted-foreground pl-6">
                  {benefits.dataImported.map((item, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Shield className="h-4 w-4 text-primary" />
                  Required permissions
                </div>
                <ul className="grid gap-2 text-sm text-muted-foreground pl-6">
                  {benefits.permissions.map((perm, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-muted-foreground" />
                      {perm}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
                <AlertCircle className="h-4 w-4 mt-0.5 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Your data is encrypted and securely stored. We only request read-only access.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleContinue} data-testid="button-continue-connect">
                Continue
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "credentials" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {providerIcons[provider.id]}
                Complete Connection
              </DialogTitle>
              <DialogDescription>
                Paste the credentials from your {provider.name} account. We check them with {provider.name} before saving.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {providerSetupHelp[provider.id] && (
                <div className="p-3 bg-muted/60 border rounded-lg text-sm text-muted-foreground" data-testid="text-setup-help">
                  {providerSetupHelp[provider.id]}
                </div>
              )}
              {provider.id === "netsuite" && <NetSuiteCertificate companyId={companyId} />}

              <div className="space-y-4">
                {credentialFields.map((cf) => (
                  <div key={cf.field} className="space-y-2">
                    <Label htmlFor={cf.field}>{cf.label}</Label>
                    <Input
                      id={cf.field}
                      type={isSecretField(cf.field) ? "password" : "text"}
                      autoComplete="off"
                      placeholder={cf.placeholder}
                      value={credentials[cf.field] || ""}
                      onChange={(e) => setCredentials(prev => ({ ...prev, [cf.field]: e.target.value }))}
                      data-testid={`input-${cf.field}`}
                    />
                    {cf.hint && <p className="text-xs text-muted-foreground">{cf.hint}</p>}
                  </div>
                ))}
              </div>

              <div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
                <Shield className="h-4 w-4 mt-0.5 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Your credentials are encrypted and securely stored. They are only used to sync data with {provider.name}.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep("benefits")}>
                Back
              </Button>
              <Button
                onClick={() => connectMutation.mutate()}
                disabled={!credentialsComplete || connectMutation.isPending}
                data-testid="button-confirm-connect"
              >
                {connectMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Complete Connection
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
