import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RefreshCw, Link2, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { SiQuickbooks, SiXero, SiSalesforce, SiHubspot } from "react-icons/si";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface IntegrationProvider {
  id: string;
  name: string;
  description: string;
  features: string[];
}

interface IntegrationStatus {
  available: string[];
  connected: string | null;
  last_sync: string | null;
}

const providerIcons: Record<string, React.ReactNode> = {
  quickbooks: <SiQuickbooks className="h-6 w-6" />,
  xero: <SiXero className="h-6 w-6" />,
  salesforce: <SiSalesforce className="h-6 w-6" />,
  hubspot: <SiHubspot className="h-6 w-6" />,
};

export default function IntegrationsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [companyId] = useState(1);

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
    };
  }>({
    queryKey: ["/api/integrations/companies", companyId, "status"],
  });

  const syncMutation = useMutation({
    mutationFn: async ({ type, provider }: { type: "accounting" | "crm"; provider: string }) => {
      const res = await apiRequest("POST", `/api/integrations/companies/${companyId}/${type}/sync?provider=${provider}`);
      return res.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Sync Complete",
        description: `Synced ${data.records_synced} records successfully`,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/integrations"] });
    },
    onError: (error) => {
      toast({
        title: "Sync Failed",
        description: String(error),
        variant: "destructive",
      });
    },
  });

  const renderProviderCard = (provider: IntegrationProvider, type: "accounting" | "crm") => {
    const isConnected = status?.integrations[type]?.connected === provider.id;
    
    return (
      <Card key={provider.id} className="hover-elevate" data-testid={`card-integration-${provider.id}`}>
        <CardHeader className="flex flex-row items-center gap-4">
          <div className="p-2 bg-muted rounded-lg">
            {providerIcons[provider.id] || <Link2 className="h-6 w-6" />}
          </div>
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {provider.name}
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
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-4">
            {provider.features.map((feature) => (
              <Badge key={feature} variant="secondary" className="text-xs">
                {feature}
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            {isConnected ? (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => syncMutation.mutate({ type, provider: provider.id })}
                  disabled={syncMutation.isPending}
                  data-testid={`button-sync-${provider.id}`}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? "animate-spin" : ""}`} />
                  Sync Now
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
        </TabsList>

        <TabsContent value="accounting" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {availableIntegrations?.accounting.map((provider) =>
              renderProviderCard(provider, "accounting")
            )}
          </div>
        </TabsContent>

        <TabsContent value="crm" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {availableIntegrations?.crm.map((provider) =>
              renderProviderCard(provider, "crm")
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
          <div className="grid md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
              <div className="p-2 bg-background rounded-full">
                {status?.integrations.accounting.connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div>
                <p className="font-medium">Accounting</p>
                <p className="text-sm text-muted-foreground">
                  {status?.integrations.accounting.connected || "Not connected"}
                </p>
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
              <div>
                <p className="font-medium">CRM</p>
                <p className="text-sm text-muted-foreground">
                  {status?.integrations.crm.connected || "Not connected"}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ConnectDialog({
  provider,
  type,
  companyId,
}: {
  provider: IntegrationProvider;
  type: "accounting" | "crm";
  companyId: number;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");

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

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid={`button-connect-${provider.id}`}>
          <Link2 className="h-4 w-4 mr-2" />
          Connect
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {providerIcons[provider.id]}
            Connect to {provider.name}
          </DialogTitle>
          <DialogDescription>
            Enter your API credentials to connect your {provider.name} account
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key / Access Token</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="Enter your API key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              data-testid="input-api-key"
            />
          </div>
          <div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
            <AlertCircle className="h-4 w-4 mt-0.5 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Your credentials are securely stored and only used to sync data with {provider.name}.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => connectMutation.mutate()}
            disabled={!apiKey || connectMutation.isPending}
            data-testid="button-confirm-connect"
          >
            {connectMutation.isPending ? "Connecting..." : "Connect"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
