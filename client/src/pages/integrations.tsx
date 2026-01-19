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
  netsuite: <Database className="h-6 w-6" />,
  pipedrive: <Users className="h-6 w-6" />,
  zoho: <Users className="h-6 w-6" />,
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
};

const additionalAccountingProviders: IntegrationProvider[] = [
  {
    id: "netsuite",
    name: "NetSuite",
    description: "Oracle NetSuite ERP for enterprise accounting",
    features: ["Multi-subsidiary", "Revenue Recognition", "Advanced Reporting"],
    comingSoon: true,
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

const paymentsProviders: IntegrationProvider[] = [
  {
    id: "stripe",
    name: "Stripe",
    description: "Payment processing and subscription billing data",
    features: ["MRR/ARR Tracking", "Churn Analytics", "Payment History", "Revenue Recognition"],
  },
];

export default function IntegrationsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [companyId] = useState(1);
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);

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

  const syncMutation = useMutation({
    mutationFn: async ({ type, provider }: { type: "accounting" | "crm" | "payments"; provider: string }) => {
      setSyncingProvider(provider);
      const res = await apiRequest("POST", `/api/integrations/companies/${companyId}/${type}/sync?provider=${provider}`);
      return res.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Sync Complete",
        description: `Synced ${data.records_synced} records successfully`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
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

  const allAccountingProviders = [
    ...(availableIntegrations?.accounting || []),
    ...additionalAccountingProviders,
  ];

  const allCrmProviders = [
    ...(availableIntegrations?.crm || []),
    ...additionalCrmProviders,
  ];

  const renderProviderCard = (provider: IntegrationProvider, type: "accounting" | "crm" | "payments") => {
    const isConnected = type === "payments" 
      ? status?.integrations.payments?.connected === provider.id
      : status?.integrations[type]?.connected === provider.id;
    const integrationStatus = type === "payments" 
      ? status?.integrations.payments 
      : status?.integrations[type];
    const lastSync = integrationStatus?.last_sync;
    const syncDetails = integrationStatus?.sync_details;
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
              <ConnectDialog provider={provider} type={type} companyId={companyId} />
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold" data-testid="text-page-title">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your accounting and CRM systems to import financial data automatically
        </p>
      </div>

      <Tabs defaultValue="accounting">
        <TabsList data-testid="tabs-integration-type">
          <TabsTrigger value="accounting" data-testid="tab-accounting">Accounting</TabsTrigger>
          <TabsTrigger value="crm" data-testid="tab-crm">CRM</TabsTrigger>
          <TabsTrigger value="payments" data-testid="tab-payments">Payments</TabsTrigger>
        </TabsList>

        <TabsContent value="accounting" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {allAccountingProviders.map((provider) =>
              renderProviderCard(provider, "accounting")
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
          <div className="grid md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full">
                {status?.integrations.accounting.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1">
                <p className="font-medium">Accounting</p>
                <p className="text-sm text-muted-foreground">
                  {status?.integrations.accounting.connected || "Not connected"}
                </p>
                {status?.integrations.accounting.last_sync && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Last synced: {formatDistanceToNow(new Date(status.integrations.accounting.last_sync), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full">
                {status?.integrations.crm.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1">
                <p className="font-medium">CRM</p>
                <p className="text-sm text-muted-foreground">
                  {status?.integrations.crm.connected || "Not connected"}
                </p>
                {status?.integrations.crm.last_sync && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Last synced: {formatDistanceToNow(new Date(status.integrations.crm.last_sync), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full">
                {status?.integrations.payments?.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1">
                <p className="font-medium">Payments</p>
                <p className="text-sm text-muted-foreground">
                  {status?.integrations.payments?.connected || "Not connected"}
                </p>
                {status?.integrations.payments?.last_sync && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Last synced: {formatDistanceToNow(new Date(status.integrations.payments.last_sync), { addSuffix: true })}
                  </p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
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

function ConnectDialog({
  provider,
  type,
  companyId,
}: {
  provider: IntegrationProvider;
  type: "accounting" | "crm" | "payments";
  companyId: number;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"benefits" | "oauth" | "credentials">("benefits");
  const [apiKey, setApiKey] = useState("");
  const [oauthProgress, setOauthProgress] = useState(0);

  const benefits = integrationBenefits[provider.id] || {
    dataImported: ["Financial data", "Transaction history"],
    permissions: ["Read-only access"],
  };

  const connectMutation = useMutation({
    mutationFn: async () => {
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
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
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
                disabled={!apiKey || connectMutation.isPending}
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
