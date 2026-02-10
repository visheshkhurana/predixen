import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
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
  Loader2
} from "lucide-react";
import { SiQuickbooks, SiXero, SiSalesforce, SiHubspot, SiStripe } from "react-icons/si";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { formatDistanceToNow } from "date-fns";

import { IntegrationCard, OAuthConnectModal, ApiKeyConnectModal, GoogleSheetsConfigModal } from "@/components/integrations";
import { 
  IntegrationConfig, 
  integrationRegistry, 
  getIntegrationsByCategory,
  SheetMapping 
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

const providerIcons: Record<string, React.ReactNode> = {
  quickbooks: <SiQuickbooks className="h-6 w-6" />,
  xero: <SiXero className="h-6 w-6" />,
  salesforce: <SiSalesforce className="h-6 w-6" />,
  hubspot: <SiHubspot className="h-6 w-6" />,
  stripe: <SiStripe className="h-6 w-6" />,
  plaid: <Link2 className="h-6 w-6" />,
  gusto: <DollarSign className="h-6 w-6" />,
  netsuite: <Database className="h-6 w-6" />,
  pipedrive: <Users className="h-6 w-6" />,
  zoho: <Users className="h-6 w-6" />,
  zoho_books: <FileText className="h-6 w-6" />,
  tally: <Database className="h-6 w-6" />,
  razorpayx_payroll: <DollarSign className="h-6 w-6" />,
  greythr: <Users className="h-6 w-6" />,
  keka: <Users className="h-6 w-6" />,
  peoplestrong: <Users className="h-6 w-6" />,
  quikchex: <DollarSign className="h-6 w-6" />,
  deskera: <Database className="h-6 w-6" />,
  sap_b1: <Database className="h-6 w-6" />,
  odoo: <Database className="h-6 w-6" />,
  marg: <Database className="h-6 w-6" />,
};

const integrationBenefits: Record<string, { dataImported: string[]; permissions: string[] }> = {
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
  zoho: {
    dataImported: [
      "Sales pipeline",
      "Lead & contact data",
      "Revenue tracking",
      "Deal analytics",
      "Sales forecasts",
    ],
    permissions: [
      "Read CRM modules",
      "Access leads & contacts",
      "View reports",
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
  razorpayx_payroll: {
    dataImported: [
      "Employee salary data",
      "PF/ESI contributions",
      "TDS deductions",
      "Reimbursements",
      "Monthly payroll runs",
    ],
    permissions: [
      "Read employee data",
      "Access payroll records",
      "View compliance details",
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
};

const additionalAccountingProviders: IntegrationProvider[] = [
  {
    id: "netsuite",
    name: "NetSuite",
    description: "Oracle NetSuite ERP for enterprise accounting",
    features: ["Multi-subsidiary", "Revenue Recognition", "Advanced Reporting"],
    comingSoon: true,
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
    id: "pipedrive",
    name: "Pipedrive",
    description: "Sales-focused CRM for growing teams",
    features: ["Pipeline Management", "Activity Tracking", "Revenue Forecasting"],
    comingSoon: true,
  },
  {
    id: "zoho",
    name: "Zoho CRM",
    description: "Comprehensive CRM with sales automation",
    features: ["Lead Management", "Sales Automation", "Analytics"],
    comingSoon: true,
  },
];

const payrollProviders: IntegrationProvider[] = [
  {
    id: "gusto",
    name: "Gusto",
    description: "US payroll, benefits, and HR platform for modern businesses",
    features: ["Employee Costs", "Payroll Runs", "Headcount Tracking", "Tax Obligations"],
  },
  {
    id: "razorpayx_payroll",
    name: "RazorpayX Payroll",
    description: "Automated payroll and compliance for Indian startups",
    features: ["Employee Salaries", "Statutory Payments (PF, ESI, TDS)", "Reimbursements", "Payslips"],
  },
  {
    id: "greythr",
    name: "GreytHR",
    description: "Full-suite HRMS and payroll management",
    features: ["Employee Data", "Leave & Attendance", "Salary Structures", "Payroll Processing"],
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
];

export default function IntegrationsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [companyId] = useState(1);
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);
  
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationConfig | null>(null);
  const [oauthModalOpen, setOauthModalOpen] = useState(false);
  const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false);
  const [sheetsConfigOpen, setSheetsConfigOpen] = useState(false);
  const [connectedNewIntegrations, setConnectedNewIntegrations] = useState<Set<string>>(new Set());
  const [sheetMappings, setSheetMappings] = useState<SheetMapping[]>([]);

  const spreadsheetIntegrations = getIntegrationsByCategory('spreadsheets');
  const analyticsIntegrations = getIntegrationsByCategory('analytics');

  const handleConnectIntegration = (integration: IntegrationConfig) => {
    setSelectedIntegration(integration);
    if (integration.authType === 'oauth2') {
      setOauthModalOpen(true);
    } else if (integration.authType === 'api_key' || integration.authType === 'basic_auth' || integration.authType === 'service_account') {
      setApiKeyModalOpen(true);
    }
  };

  const handleModalClose = (modalType: 'oauth' | 'apikey' | 'sheets') => {
    if (modalType === 'oauth') {
      setOauthModalOpen(false);
    } else if (modalType === 'apikey') {
      setApiKeyModalOpen(false);
    } else if (modalType === 'sheets') {
      setSheetsConfigOpen(false);
    }
    setSelectedIntegration(null);
  };

  const handleOAuthConnect = (integrationId: string, selectedDataPoints: string[]) => {
    setConnectedNewIntegrations(prev => new Set(prev).add(integrationId));
    toast({
      title: "Integration Connected",
      description: `Successfully connected ${selectedIntegration?.name}. Data will sync shortly.`,
    });
    setOauthModalOpen(false);
    
    if (integrationId === 'google-sheets') {
      setSheetsConfigOpen(true);
    } else {
      setSelectedIntegration(null);
    }
  };

  const handleApiKeyConnect = (integrationId: string, credentials: Record<string, string>, selectedDataPoints: string[]) => {
    setConnectedNewIntegrations(prev => new Set(prev).add(integrationId));
    toast({
      title: "Integration Connected",
      description: `Successfully connected ${selectedIntegration?.name}. Initial sync started.`,
    });
    setApiKeyModalOpen(false);
    setSelectedIntegration(null);
  };

  const handleDisconnectIntegration = (integrationId: string) => {
    setConnectedNewIntegrations(prev => {
      const newSet = new Set(prev);
      newSet.delete(integrationId);
      return newSet;
    });
    toast({
      title: "Integration Disconnected",
      description: "The integration has been removed.",
    });
  };

  const handleConfigureIntegration = (integrationId: string) => {
    if (integrationId === 'google-sheets') {
      setSheetsConfigOpen(true);
    }
  };

  const handleSaveSheetMappings = (mappings: SheetMapping[]) => {
    setSheetMappings(mappings);
    toast({
      title: "Configuration Saved",
      description: `Configured ${mappings.length} sheet mapping(s). Data will sync on schedule.`,
    });
  };

  const { data: availableIntegrations } = useQuery<{
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
  });
  
  const { data: connectorStatus } = useQuery<{
    company_id: number;
    connectors: Array<{
      provider_id: string;
      connected: boolean;
      last_sync: string | null;
      records_synced: number;
      error: string | null;
    }>;
  }>({
    queryKey: ["/api/connectors/companies", companyId, "status"],
  });

  const connectorSyncIds = ["razorpayx_payroll", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks"];
  
  const syncMutation = useMutation({
    mutationFn: async ({ type, provider }: { type: "accounting" | "crm" | "payments" | "payroll" | "erp"; provider: string }) => {
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
      setSyncingProvider(null);
    },
    onError: (error) => {
      toast({
        title: "Sync Failed",
        description: String(error),
        variant: "destructive",
      });
      setSyncingProvider(null);
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
        title: "Sample Data Synced",
        description: `${data.provider_name}: ${metrics.length} metrics stored (${metrics.slice(0, 4).join(", ")}${metrics.length > 4 ? "..." : ""})`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/connectors/companies", companyId, "status"] });
      queryClient.invalidateQueries({ queryKey: ["/api/financials"] });
      queryClient.invalidateQueries({ queryKey: ["/api/realtime"] });
      setTestingProvider(null);
    },
    onError: (error) => {
      toast({
        title: "Sample Test Failed",
        description: String(error),
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

  type IntegrationType = "accounting" | "crm" | "payments" | "payroll" | "erp";
  
  const getConnectorInfo = (providerId: string) => {
    return connectorStatus?.connectors?.find(c => c.provider_id === providerId);
  };
  
  const connectorBackedIds = ["razorpayx_payroll", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks"];
  
  const renderProviderCard = (provider: IntegrationProvider, type: IntegrationType) => {
    const connectorInfo = getConnectorInfo(provider.id);
    const isConnectorBacked = type === "payroll" || type === "erp" || connectorBackedIds.includes(provider.id);
    const isConnected = isConnectorBacked
      ? connectorInfo?.connected || false
      : type === "payments" 
        ? status?.integrations.payments?.connected === provider.id
        : status?.integrations[type]?.connected === provider.id;
    const integrationStatus = isConnectorBacked
      ? undefined
      : type === "payments" 
        ? status?.integrations.payments 
        : status?.integrations[type];
    const lastSync = isConnectorBacked 
      ? connectorInfo?.last_sync 
      : integrationStatus?.last_sync;
    const syncDetails = isConnectorBacked
      ? connectorInfo ? { records_synced: connectorInfo.records_synced, last_error: connectorInfo.error } : undefined
      : integrationStatus?.sync_details;
    const isSyncing = syncingProvider === provider.id && syncMutation.isPending;
    
    return (
      <Card key={provider.id} className="hover-elevate" data-testid={`card-integration-${provider.id}`}>
        <CardHeader className="flex flex-row items-center gap-4">
          <div className="p-2 bg-muted rounded-lg">
            {providerIcons[provider.id] || <Link2 className="h-6 w-6" />}
          </div>
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2 flex-wrap">
              {provider.name}
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

          {isConnected && (
            <SyncStatusDisplay 
              lastSync={lastSync ?? null} 
              syncDetails={syncDetails}
              isSyncing={isSyncing}
            />
          )}

          <div className="flex gap-2 flex-wrap">
            {provider.comingSoon ? (
              <Button size="sm" variant="outline" disabled data-testid={`button-coming-soon-${provider.id}`}>
                <Clock className="h-4 w-4 mr-2" />
                Coming Soon
              </Button>
            ) : isConnected ? (
              <>
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
                <Button size="sm" variant="ghost" data-testid={`button-disconnect-${provider.id}`}>
                  Disconnect
                </Button>
              </>
            ) : (
              <>
                <ConnectDialog provider={provider} type={type} companyId={companyId} />
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
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-page-title">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your accounting, payroll, and ERP systems to import financial data automatically
        </p>
      </div>

      <Tabs defaultValue="spreadsheets">
        <TabsList data-testid="tabs-integration-type" className="flex-wrap gap-1">
          <TabsTrigger value="spreadsheets" data-testid="tab-spreadsheets">Spreadsheets</TabsTrigger>
          <TabsTrigger value="analytics" data-testid="tab-analytics">Analytics</TabsTrigger>
          <TabsTrigger value="accounting" data-testid="tab-accounting">Accounting</TabsTrigger>
          <TabsTrigger value="payroll" data-testid="tab-payroll">Payroll</TabsTrigger>
          <TabsTrigger value="erp" data-testid="tab-erp">ERP</TabsTrigger>
          <TabsTrigger value="crm" data-testid="tab-crm">CRM</TabsTrigger>
          <TabsTrigger value="payments" data-testid="tab-payments">Payments</TabsTrigger>
        </TabsList>

        <TabsContent value="spreadsheets" className="space-y-4">
          <div className="mb-4 p-4 bg-muted/50 rounded-lg">
            <h3 className="font-medium mb-2">Spreadsheet Integrations</h3>
            <p className="text-sm text-muted-foreground">
              Import data from spreadsheets like Google Sheets. Perfect for custom metrics, budgets, and manual KPI tracking.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {spreadsheetIntegrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                isConnected={connectedNewIntegrations.has(integration.id)}
                onConnect={handleConnectIntegration}
                onDisconnect={handleDisconnectIntegration}
                onConfigure={handleConfigureIntegration}
                status={connectedNewIntegrations.has(integration.id) ? 'connected' : 'disconnected'}
              />
            ))}
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
            {analyticsIntegrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                isConnected={connectedNewIntegrations.has(integration.id)}
                onConnect={handleConnectIntegration}
                onDisconnect={handleDisconnectIntegration}
                onConfigure={handleConfigureIntegration}
                status={connectedNewIntegrations.has(integration.id) ? 'connected' : 'disconnected'}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="accounting" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {allAccountingProviders.map((provider) =>
              renderProviderCard(provider, "accounting")
            )}
          </div>
        </TabsContent>

        <TabsContent value="payroll" className="space-y-4">
          <div className="mb-4 p-4 bg-muted/50 rounded-lg">
            <h3 className="font-medium mb-2">Indian Payroll Providers</h3>
            <p className="text-sm text-muted-foreground">
              Connect your payroll system to automatically import employee costs, statutory contributions (PF, ESI, TDS), 
              and compensation data for accurate financial modeling.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {payrollProviders.map((provider) =>
              renderProviderCard(provider, "payroll")
            )}
          </div>
        </TabsContent>

        <TabsContent value="erp" className="space-y-4">
          <div className="mb-4 p-4 bg-muted/50 rounded-lg">
            <h3 className="font-medium mb-2">Enterprise Resource Planning</h3>
            <p className="text-sm text-muted-foreground">
              Connect your ERP system to sync inventory, operations, and financial data for comprehensive business insights.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {erpProviders.map((provider) =>
              renderProviderCard(provider, "erp")
            )}
          </div>
        </TabsContent>

        <TabsContent value="crm" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {allCrmProviders.map((provider) =>
              renderProviderCard(provider, "crm")
            )}
          </div>
        </TabsContent>

        <TabsContent value="payments" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {paymentsProviders.map((provider) =>
              renderProviderCard(provider, "payments")
            )}
          </div>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Integration Status</CardTitle>
          <CardDescription>Overview of your connected data sources</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {status?.integrations.accounting.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Accounting</p>
                <p className="text-sm text-muted-foreground truncate">
                  {status?.integrations.accounting.connected || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {connectorStatus?.connectors?.some(c => 
                  ["razorpayx_payroll", "greythr", "keka", "gusto"].includes(c.provider_id) && c.connected
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
                    ["razorpayx_payroll", "greythr", "keka", "gusto"].includes(c.provider_id) && c.connected
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
                {status?.integrations.crm.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">CRM</p>
                <p className="text-sm text-muted-foreground truncate">
                  {status?.integrations.crm.connected || "Not connected"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full shrink-0">
                {status?.integrations.payments?.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Payments</p>
                <p className="text-sm text-muted-foreground truncate">
                  {status?.integrations.payments?.connected || "Not connected"}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedIntegration && (
        <>
          <OAuthConnectModal
            integration={selectedIntegration}
            isOpen={oauthModalOpen}
            onClose={() => handleModalClose('oauth')}
            onConnect={handleOAuthConnect}
          />
          <ApiKeyConnectModal
            integration={selectedIntegration}
            isOpen={apiKeyModalOpen}
            onClose={() => handleModalClose('apikey')}
            onConnect={handleApiKeyConnect}
          />
        </>
      )}

      <GoogleSheetsConfigModal
        isOpen={sheetsConfigOpen}
        onClose={() => handleModalClose('sheets')}
        onSave={handleSaveSheetMappings}
        existingMappings={sheetMappings}
      />
    </div>
  );
}

function SyncStatusDisplay({ 
  lastSync, 
  syncDetails, 
  isSyncing 
}: { 
  lastSync: string | null; 
  syncDetails?: SyncDetails;
  isSyncing: boolean;
}) {
  return (
    <div className="p-3 bg-muted/50 rounded-lg space-y-2">
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
              Last synced: {lastSync ? formatDistanceToNow(new Date(lastSync), { addSuffix: true }) : "Never"}
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

const providerCredentialFields: Record<string, { field: string; label: string; placeholder: string }[]> = {
  razorpayx_payroll: [
    { field: "api_key", label: "API Key", placeholder: "Enter RazorpayX API Key" },
    { field: "api_secret", label: "API Secret", placeholder: "Enter RazorpayX API Secret" },
  ],
  greythr: [
    { field: "api_access_id", label: "API Access ID", placeholder: "Enter GreytHR Access ID" },
    { field: "api_secret", label: "API Secret", placeholder: "Enter GreytHR API Secret" },
    { field: "base_url", label: "Base URL", placeholder: "https://yourcompany.greythr.com" },
  ],
  keka: [
    { field: "api_key", label: "API Key", placeholder: "Enter Keka API Key" },
    { field: "tenant_id", label: "Tenant ID", placeholder: "Enter your Keka Tenant ID" },
  ],
  zoho_books: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Zoho Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Zoho Client Secret" },
    { field: "organization_id", label: "Organization ID", placeholder: "Enter Zoho Organization ID" },
  ],
  tally: [
    { field: "tally_url", label: "Tally Server URL", placeholder: "http://localhost:9000" },
    { field: "company_name", label: "Company Name", placeholder: "Enter your Tally Company name" },
  ],
  plaid: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Plaid Client ID" },
    { field: "secret", label: "Secret Key", placeholder: "Enter Plaid Secret" },
    { field: "access_token", label: "Access Token", placeholder: "access-sandbox-..." },
  ],
  hubspot: [
    { field: "access_token", label: "Private App Token", placeholder: "pat-na1-..." },
  ],
  gusto: [
    { field: "client_id", label: "Client ID", placeholder: "Enter Gusto Client ID" },
    { field: "client_secret", label: "Client Secret", placeholder: "Enter Gusto Client Secret" },
    { field: "access_token", label: "Access Token", placeholder: "OAuth2 Access Token" },
    { field: "refresh_token", label: "Refresh Token", placeholder: "OAuth2 Refresh Token" },
    { field: "company_uuid", label: "Company UUID", placeholder: "Gusto Company UUID" },
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
    { field: "api_secret", label: "API Secret", placeholder: "Enter Mixpanel API Secret" },
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
  shopify: [
    { field: "shop_domain", label: "Shop Domain", placeholder: "yourstore (without .myshopify.com)" },
    { field: "access_token", label: "Admin API Token", placeholder: "shpat_..." },
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
  ],
  rippling: [
    { field: "api_key", label: "API Key", placeholder: "Enter Rippling API Key" },
  ],
  deel: [
    { field: "api_key", label: "API Token", placeholder: "Enter Deel API Token" },
  ],
  netsuite: [
    { field: "account_id", label: "Account ID", placeholder: "Enter NetSuite Account ID" },
    { field: "consumer_key", label: "Consumer Key", placeholder: "Enter Consumer Key" },
    { field: "consumer_secret", label: "Consumer Secret", placeholder: "Enter Consumer Secret" },
    { field: "token_id", label: "Token ID", placeholder: "Enter Token ID" },
    { field: "token_secret", label: "Token Secret", placeholder: "Enter Token Secret" },
  ],
  profitwell: [
    { field: "api_token", label: "Private API Token", placeholder: "Enter ProfitWell API Token" },
  ],
  amplitude: [
    { field: "api_key", label: "API Key", placeholder: "Enter Amplitude API Key" },
    { field: "secret_key", label: "Secret Key", placeholder: "Enter Amplitude Secret Key" },
  ],
};

function ConnectDialog({
  provider,
  type,
  companyId,
}: {
  provider: IntegrationProvider;
  type: "accounting" | "crm" | "payments" | "payroll" | "erp";
  companyId: number;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"benefits" | "oauth" | "credentials">("benefits");
  const [apiKey, setApiKey] = useState("");
  const [oauthProgress, setOauthProgress] = useState(0);
  const [credentials, setCredentials] = useState<Record<string, string>>({});

  const credentialFields = providerCredentialFields[provider.id] || [
    { field: "api_key", label: "API Key", placeholder: "Enter API Key" },
  ];
  
  const connectorBackedProviders = ["razorpayx_payroll", "greythr", "keka", "zoho_books", "tally", "plaid", "hubspot", "gusto", "xero", "stripe", "quickbooks", "salesforce", "google_analytics", "pipedrive", "close_crm", "mixpanel", "mercury", "brex", "ramp", "shopify", "mysql", "freshbooks", "wave", "bench", "chargebee", "recurly", "rippling", "deel", "netsuite", "profitwell", "amplitude", "google_sheets", "rest_api"];
  const isPayrollOrErp = type === "payroll" || type === "erp" || connectorBackedProviders.includes(provider.id);

  const benefits = integrationBenefits[provider.id] || {
    dataImported: ["Financial data", "Transaction history"],
    permissions: ["Read-only access"],
  };

  const connectMutation = useMutation({
    mutationFn: async () => {
      if (isPayrollOrErp) {
        const creds = credentialFields.length > 1 ? credentials : { api_key: apiKey };
        const res = await apiRequest("POST", `/api/connectors/companies/${companyId}/connect`, {
          provider_id: provider.id,
          credentials: creds,
        });
        return res.json();
      }
      const res = await apiRequest("POST", `/api/integrations/companies/${companyId}/${type}/connect`, {
        provider: provider.id,
        credentials: { access_token: apiKey },
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
    onError: (error) => {
      toast({
        title: "Connection Failed",
        description: String(error),
        variant: "destructive",
      });
    },
  });

  const handleOAuthSimulation = () => {
    if (isPayrollOrErp) {
      setStep("credentials");
      return;
    }
    setStep("oauth");
    setOauthProgress(0);
    
    const interval = setInterval(() => {
      setOauthProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setStep("credentials");
          return 100;
        }
        return prev + 20;
      });
    }, 500);
  };

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
        <Button size="sm" data-testid={`button-connect-${provider.id}`}>
          <Link2 className="h-4 w-4 mr-2" />
          Connect
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
              <Button onClick={handleOAuthSimulation} data-testid="button-continue-connect">
                Continue
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </DialogFooter>
          </>
        )}

        {step === "oauth" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {providerIcons[provider.id]}
                Authorizing with {provider.name}
              </DialogTitle>
              <DialogDescription>
                Simulating OAuth authorization flow...
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-8">
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <div className="p-4 bg-muted rounded-full">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                </div>
                
                <div className="text-center space-y-2">
                  <p className="text-sm font-medium">Connecting to {provider.name}</p>
                  <p className="text-xs text-muted-foreground">
                    In production, you would be redirected to {provider.name} to authorize access
                  </p>
                </div>

                <Progress value={oauthProgress} className="h-2" />
                
                <div className="space-y-2 text-sm">
                  <div className={`flex items-center gap-2 ${oauthProgress >= 20 ? "text-foreground" : "text-muted-foreground"}`}>
                    {oauthProgress >= 20 ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Clock className="h-4 w-4" />}
                    Opening authorization window...
                  </div>
                  <div className={`flex items-center gap-2 ${oauthProgress >= 40 ? "text-foreground" : "text-muted-foreground"}`}>
                    {oauthProgress >= 40 ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Clock className="h-4 w-4" />}
                    Waiting for user authorization...
                  </div>
                  <div className={`flex items-center gap-2 ${oauthProgress >= 60 ? "text-foreground" : "text-muted-foreground"}`}>
                    {oauthProgress >= 60 ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Clock className="h-4 w-4" />}
                    Exchanging authorization code...
                  </div>
                  <div className={`flex items-center gap-2 ${oauthProgress >= 80 ? "text-foreground" : "text-muted-foreground"}`}>
                    {oauthProgress >= 80 ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Clock className="h-4 w-4" />}
                    Storing secure credentials...
                  </div>
                  <div className={`flex items-center gap-2 ${oauthProgress >= 100 ? "text-foreground" : "text-muted-foreground"}`}>
                    {oauthProgress >= 100 ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Clock className="h-4 w-4" />}
                    Authorization complete!
                  </div>
                </div>
              </div>
            </div>
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
                Enter your API credentials to finalize the connection
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <p className="text-sm text-green-600 dark:text-green-400">
                  Authorization successful! Complete the setup below.
                </p>
              </div>

              {isPayrollOrErp && credentialFields.length > 1 ? (
                <div className="space-y-4">
                  {credentialFields.map((cf) => (
                    <div key={cf.field} className="space-y-2">
                      <Label htmlFor={cf.field}>{cf.label}</Label>
                      <Input
                        id={cf.field}
                        type={cf.field.includes("secret") || cf.field.includes("key") || cf.field.includes("password") ? "password" : "text"}
                        placeholder={cf.placeholder}
                        value={credentials[cf.field] || ""}
                        onChange={(e) => setCredentials(prev => ({ ...prev, [cf.field]: e.target.value }))}
                        data-testid={`input-${cf.field}`}
                      />
                    </div>
                  ))}
                  <p className="text-xs text-muted-foreground">
                    For demo purposes, enter any values to simulate a connection.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Label htmlFor="api-key">API Key / Access Token</Label>
                  <Input
                    id="api-key"
                    type="password"
                    placeholder="Enter your API key (demo: any value)"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    data-testid="input-api-key"
                  />
                  <p className="text-xs text-muted-foreground">
                    For demo purposes, enter any value to simulate a connection.
                  </p>
                </div>
              )}

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
                disabled={(isPayrollOrErp && credentialFields.length > 1 
                  ? !credentialFields.every(cf => credentials[cf.field])
                  : !apiKey) || connectMutation.isPending}
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
