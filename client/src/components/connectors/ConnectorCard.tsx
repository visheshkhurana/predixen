import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ConnectorBadge, RefreshBadge } from "./ConnectorBadge";
import { 
  Database, 
  DollarSign, 
  Users, 
  FileText, 
  BarChart3, 
  Settings, 
  Link2,
  CheckCircle,
  AlertCircle,
  Clock,
  Lock
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

interface ConnectorCardProps {
  connector: {
    id: string;
    name: string;
    category: string;
    description: string;
    longDescription?: string;
    authType: string;
    supportsWebhooks: boolean;
    typicalRefresh: string;
    native: boolean;
    beta: boolean;
    implemented: boolean;
    setupComplexity: string;
    installStatus?: {
      status: string;
      lastSync?: string | null;
    } | null;
  };
  onConnect: (id: string) => void;
  onManage: (id: string) => void;
}

const connectorIcons: Record<string, React.ReactNode> = {
  stripe: <SiStripe className="h-8 w-8 text-[#635BFF]" />,
  quickbooks: <SiQuickbooks className="h-8 w-8 text-[#2CA01C]" />,
  xero: <SiXero className="h-8 w-8 text-[#13B5EA]" />,
  hubspot: <SiHubspot className="h-8 w-8 text-[#FF7A59]" />,
  salesforce: <SiSalesforce className="h-8 w-8 text-[#00A1E0]" />,
  google_analytics: <SiGoogleanalytics className="h-8 w-8 text-[#E37400]" />,
  shopify: <SiShopify className="h-8 w-8 text-[#96BF48]" />,
  mixpanel: <SiMixpanel className="h-8 w-8 text-[#7856FF]" />,
  postgresql: <SiPostgresql className="h-8 w-8 text-[#336791]" />,
  mysql: <SiMysql className="h-8 w-8 text-[#4479A1]" />,
  google_sheets: <SiGooglesheets className="h-8 w-8 text-[#0F9D58]" />,
};

const categoryIcons: Record<string, React.ReactNode> = {
  Finance: <DollarSign className="h-8 w-8 text-emerald-500" />,
  CRM: <Users className="h-8 w-8 text-blue-500" />,
  Payroll: <DollarSign className="h-8 w-8 text-amber-500" />,
  ERP: <Database className="h-8 w-8 text-purple-500" />,
  Analytics: <BarChart3 className="h-8 w-8 text-cyan-500" />,
  Databases: <Database className="h-8 w-8 text-slate-500" />,
  Files: <FileText className="h-8 w-8 text-orange-500" />,
  Custom: <Settings className="h-8 w-8 text-gray-500" />,
};

export function ConnectorCard({ connector, onConnect, onManage }: ConnectorCardProps) {
  const isInstalled = connector.installStatus?.status === "active" || 
                      connector.installStatus?.status === "paused" ||
                      connector.installStatus?.status === "error";
  
  const getIcon = () => {
    return connectorIcons[connector.id] || categoryIcons[connector.category] || <Database className="h-8 w-8" />;
  };
  
  const getStatusBadge = () => {
    if (!connector.installStatus) return null;
    
    switch (connector.installStatus.status) {
      case "active":
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
            <CheckCircle className="h-3 w-3 mr-1" />
            Active
          </Badge>
        );
      case "error":
        return (
          <Badge className="bg-red-500/10 text-red-600 border-red-500/20">
            <AlertCircle className="h-3 w-3 mr-1" />
            Error
          </Badge>
        );
      case "paused":
        return (
          <Badge className="bg-amber-500/10 text-amber-600 border-amber-500/20">
            <Clock className="h-3 w-3 mr-1" />
            Paused
          </Badge>
        );
      default:
        return null;
    }
  };
  
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Card 
          className="overflow-visible hover-elevate cursor-pointer transition-all group"
          data-testid={`connector-card-${connector.id}`}
        >
          <CardContent className="p-4">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 p-2 rounded-lg bg-muted/50 group-hover:bg-muted transition-colors">
                {getIcon()}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <h3 className="font-semibold truncate">{connector.name}</h3>
                  {connector.native && <ConnectorBadge type="native" size="sm" />}
                  {connector.beta && <ConnectorBadge type="beta" size="sm" />}
                  {getStatusBadge()}
                </div>
                
                <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                  {connector.description}
                </p>
                
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-xs">
                    {connector.category}
                  </Badge>
                  {connector.typicalRefresh === "real-time" && (
                    <ConnectorBadge type="realtime" size="sm" />
                  )}
                  {connector.supportsWebhooks && connector.typicalRefresh !== "real-time" && (
                    <ConnectorBadge type="webhook" size="sm" />
                  )}
                </div>
              </div>
              
              <div className="flex-shrink-0">
                {isInstalled ? (
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onManage(connector.id);
                    }}
                    data-testid={`button-manage-${connector.id}`}
                  >
                    Manage
                  </Button>
                ) : (
                  <Button 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onConnect(connector.id);
                    }}
                    disabled={!connector.implemented}
                    data-testid={`button-connect-${connector.id}`}
                  >
                    <Link2 className="h-4 w-4 mr-1" />
                    Connect
                  </Button>
                )}
              </div>
            </div>
            
            <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Lock className="h-3 w-3" />
                <span>Read-only access</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span className="capitalize">{connector.typicalRefresh} sync</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs p-4" align="start">
        <div className="space-y-2">
          <p className="font-medium">{connector.name}</p>
          <p className="text-sm text-muted-foreground">{connector.longDescription || connector.description}</p>
          <div className="pt-2 border-t space-y-1">
            <p className="text-xs"><span className="font-medium">Refresh:</span> {connector.typicalRefresh}</p>
            <p className="text-xs"><span className="font-medium">Setup:</span> {connector.setupComplexity} complexity</p>
            <p className="text-xs"><span className="font-medium">Auth:</span> {connector.authType.replace("_", " ")}</p>
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
