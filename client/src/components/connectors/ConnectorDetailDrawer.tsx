import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConnectorBadge, RefreshBadge } from "./ConnectorBadge";
import { 
  Database, 
  DollarSign, 
  Users, 
  FileText, 
  BarChart3, 
  Settings,
  Link2,
  Shield,
  Clock,
  RefreshCw,
  CheckCircle,
  Lock,
  Key,
  Webhook,
  ArrowRight,
  ExternalLink
} from "lucide-react";
import { 
  SiStripe, 
  SiQuickbooks, 
  SiXero, 
  SiHubspot, 
  SiSalesforce, 
  SiGoogleanalytics,
  SiShopify,
  SiMixpanel,
  SiPostgresql,
  SiMysql,
  SiGooglesheets
} from "react-icons/si";

interface ConnectorDetailDrawerProps {
  connector: {
    id: string;
    name: string;
    category: string;
    description: string;
    longDescription?: string;
    authType: string;
    supportsWebhooks: boolean;
    supportsPolling: boolean;
    supportsIncremental: boolean;
    typicalRefresh: string;
    native: boolean;
    beta: boolean;
    implemented: boolean;
    setupComplexity: string;
    documentationUrl?: string;
    metricsUnlocked: string[];
    requiredPermissions: string[];
    dataCollected: string[];
  } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnect: (id: string) => void;
}

const connectorIcons: Record<string, React.ReactNode> = {
  stripe: <SiStripe className="h-12 w-12 text-[#635BFF]" />,
  quickbooks: <SiQuickbooks className="h-12 w-12 text-[#2CA01C]" />,
  xero: <SiXero className="h-12 w-12 text-[#13B5EA]" />,
  hubspot: <SiHubspot className="h-12 w-12 text-[#FF7A59]" />,
  salesforce: <SiSalesforce className="h-12 w-12 text-[#00A1E0]" />,
  google_analytics: <SiGoogleanalytics className="h-12 w-12 text-[#E37400]" />,
  shopify: <SiShopify className="h-12 w-12 text-[#96BF48]" />,
  mixpanel: <SiMixpanel className="h-12 w-12 text-[#7856FF]" />,
  postgresql: <SiPostgresql className="h-12 w-12 text-[#336791]" />,
  mysql: <SiMysql className="h-12 w-12 text-[#4479A1]" />,
  google_sheets: <SiGooglesheets className="h-12 w-12 text-[#0F9D58]" />,
};

const categoryIcons: Record<string, React.ReactNode> = {
  Finance: <DollarSign className="h-12 w-12 text-emerald-500" />,
  CRM: <Users className="h-12 w-12 text-blue-500" />,
  Payroll: <DollarSign className="h-12 w-12 text-amber-500" />,
  ERP: <Database className="h-12 w-12 text-purple-500" />,
  Analytics: <BarChart3 className="h-12 w-12 text-cyan-500" />,
  Databases: <Database className="h-12 w-12 text-slate-500" />,
  Files: <FileText className="h-12 w-12 text-orange-500" />,
  Custom: <Settings className="h-12 w-12 text-gray-500" />,
};

const getAuthIcon = (authType: string) => {
  switch (authType) {
    case "oauth": return <Key className="h-4 w-4" />;
    case "api_key": return <Key className="h-4 w-4" />;
    case "webhook": return <Webhook className="h-4 w-4" />;
    case "db_connection": return <Database className="h-4 w-4" />;
    case "file_upload": return <FileText className="h-4 w-4" />;
    default: return <Key className="h-4 w-4" />;
  }
};

const getAuthLabel = (authType: string) => {
  switch (authType) {
    case "oauth": return "OAuth 2.0";
    case "api_key": return "API Key";
    case "webhook": return "Webhook";
    case "db_connection": return "Database Connection";
    case "file_upload": return "File Upload";
    default: return authType;
  }
};

export function ConnectorDetailDrawer({ connector, open, onOpenChange, onConnect }: ConnectorDetailDrawerProps) {
  if (!connector) return null;
  
  const getIcon = () => {
    return connectorIcons[connector.id] || categoryIcons[connector.category] || <Database className="h-12 w-12" />;
  };
  
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto" data-testid="connector-detail-drawer">
        <SheetHeader className="pb-4">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-muted">
              {getIcon()}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <SheetTitle className="text-xl">{connector.name}</SheetTitle>
                {connector.native && <ConnectorBadge type="native" size="sm" />}
                {connector.beta && <ConnectorBadge type="beta" size="sm" />}
              </div>
              <SheetDescription>{connector.description}</SheetDescription>
            </div>
          </div>
        </SheetHeader>
        
        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="data" data-testid="tab-data">Data</TabsTrigger>
            <TabsTrigger value="sync" data-testid="tab-sync">Sync</TabsTrigger>
            <TabsTrigger value="security" data-testid="tab-security">Security</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4 mt-4">
            <div>
              <h4 className="font-medium mb-2">About</h4>
              <p className="text-sm text-muted-foreground">
                {connector.longDescription || connector.description}
              </p>
            </div>
            
            <Separator />
            
            <div>
              <h4 className="font-medium mb-3">Metrics Unlocked</h4>
              <div className="flex flex-wrap gap-2">
                {connector.metricsUnlocked.length > 0 ? (
                  connector.metricsUnlocked.map((metric) => (
                    <Badge key={metric} variant="secondary">
                      <BarChart3 className="h-3 w-3 mr-1" />
                      {metric}
                    </Badge>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Custom metrics based on your data</p>
                )}
              </div>
            </div>
            
            <Separator />
            
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg border">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Clock className="h-4 w-4" />
                  Refresh Rate
                </div>
                <p className="font-medium capitalize">{connector.typicalRefresh}</p>
              </div>
              <div className="p-3 rounded-lg border">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Settings className="h-4 w-4" />
                  Setup Complexity
                </div>
                <p className="font-medium capitalize">{connector.setupComplexity}</p>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="data" className="space-y-4 mt-4">
            <div>
              <h4 className="font-medium mb-3">Data Collected</h4>
              <div className="space-y-2">
                {connector.dataCollected.length > 0 ? (
                  connector.dataCollected.map((item) => (
                    <div key={item} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                      {item}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Data structure depends on your configuration</p>
                )}
              </div>
            </div>
            
            <div className="p-4 rounded-lg bg-muted/50 border">
              <div className="flex items-start gap-3">
                <Lock className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Your data is read-only</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    FounderConsole only reads your data. We never modify, delete, or write to your connected systems.
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="sync" className="space-y-4 mt-4">
            <div>
              <h4 className="font-medium mb-3">Sync Behavior</h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Polling</span>
                  </div>
                  <Badge variant={connector.supportsPolling ? "default" : "secondary"}>
                    {connector.supportsPolling ? "Supported" : "Not Supported"}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <Webhook className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Webhooks</span>
                  </div>
                  <Badge variant={connector.supportsWebhooks ? "default" : "secondary"}>
                    {connector.supportsWebhooks ? "Supported" : "Not Supported"}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-2">
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Incremental Sync</span>
                  </div>
                  <Badge variant={connector.supportsIncremental ? "default" : "secondary"}>
                    {connector.supportsIncremental ? "Supported" : "Full Sync Only"}
                  </Badge>
                </div>
              </div>
            </div>
            
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-sm">
                <span className="font-medium">Typical refresh:</span>{" "}
                <span className="capitalize">{connector.typicalRefresh}</span>
              </p>
            </div>
          </TabsContent>
          
          <TabsContent value="security" className="space-y-4 mt-4">
            <div>
              <h4 className="font-medium mb-3">Authentication</h4>
              <div className="flex items-center gap-2 p-3 rounded-lg border">
                {getAuthIcon(connector.authType)}
                <span className="text-sm">{getAuthLabel(connector.authType)}</span>
              </div>
            </div>
            
            {connector.requiredPermissions.length > 0 && (
              <div>
                <h4 className="font-medium mb-3">Required Permissions</h4>
                <div className="space-y-2">
                  {connector.requiredPermissions.map((perm) => (
                    <div key={perm} className="flex items-center gap-2 text-sm">
                      <Shield className="h-4 w-4 text-blue-500" />
                      {perm}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="space-y-3 p-4 rounded-lg bg-muted/50 border">
              <div className="flex items-start gap-3">
                <Lock className="h-5 w-5 text-emerald-500 mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Secrets are encrypted at rest</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    All credentials are encrypted using AES-256 and stored securely.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Shield className="h-5 w-5 text-emerald-500 mt-0.5" />
                <div>
                  <p className="font-medium text-sm">Raw data is never modified</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Your source systems remain unchanged. We only read data.
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
        
        <SheetFooter className="mt-6 pt-4 border-t">
          <div className="flex items-center justify-between w-full gap-4">
            {connector.documentationUrl && (
              <Button variant="outline" size="sm" asChild>
                <a href={connector.documentationUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Docs
                </a>
              </Button>
            )}
            <Button 
              className="flex-1"
              onClick={() => onConnect(connector.id)}
              disabled={!connector.implemented}
              data-testid="button-connect-drawer"
            >
              <Link2 className="h-4 w-4 mr-2" />
              Connect {connector.name}
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
