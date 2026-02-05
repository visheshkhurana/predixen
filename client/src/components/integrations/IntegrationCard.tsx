import { IntegrationConfig, IntegrationStatus } from '@/lib/integrations/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Link2, Settings, Unplug, Clock, Loader2 } from 'lucide-react';
import { SiGooglesheets, SiGoogleanalytics, SiMixpanel, SiStripe, SiHubspot, SiSalesforce, SiQuickbooks, SiXero } from 'react-icons/si';
import { cn } from '@/lib/utils';

interface IntegrationCardProps {
  integration: IntegrationConfig;
  isConnected: boolean;
  onConnect: (integration: IntegrationConfig) => void;
  onDisconnect: (integrationId: string) => void;
  onConfigure: (integrationId: string) => void;
  lastSyncAt?: Date;
  status?: IntegrationStatus;
  testId?: string;
}

const statusConfig = {
  connected: { color: 'bg-green-500', label: 'Connected' },
  disconnected: { color: 'bg-muted', label: 'Disconnected' },
  error: { color: 'bg-red-500', label: 'Error' },
  syncing: { color: 'bg-blue-500 animate-pulse', label: 'Syncing' },
};

function getIntegrationIcon(iconName: string) {
  const iconClass = "w-6 h-6";
  switch (iconName) {
    case 'sheets': return <SiGooglesheets className={cn(iconClass, "text-green-500")} />;
    case 'analytics': return <SiGoogleanalytics className={cn(iconClass, "text-orange-500")} />;
    case 'mixpanel': return <SiMixpanel className={cn(iconClass, "text-purple-500")} />;
    case 'chartmogul': return <div className={cn(iconClass, "bg-blue-500 rounded text-white flex items-center justify-center text-xs font-bold")}>CM</div>;
    case 'stripe': return <SiStripe className={cn(iconClass, "text-purple-400")} />;
    case 'hubspot': return <SiHubspot className={cn(iconClass, "text-orange-500")} />;
    case 'salesforce': return <SiSalesforce className={cn(iconClass, "text-blue-400")} />;
    case 'quickbooks': return <SiQuickbooks className={cn(iconClass, "text-green-600")} />;
    case 'xero': return <SiXero className={cn(iconClass, "text-blue-500")} />;
    default: return <Link2 className={iconClass} />;
  }
}

export function IntegrationCard({
  integration,
  isConnected,
  onConnect,
  onDisconnect,
  onConfigure,
  lastSyncAt,
  status = 'disconnected',
  testId,
}: IntegrationCardProps) {
  const statusInfo = statusConfig[status];

  return (
    <Card 
      className={cn(
        "transition-all",
        isConnected && "border-green-500/30"
      )}
      data-testid={testId || `card-integration-${integration.id}`}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
              {getIntegrationIcon(integration.icon)}
            </div>
            <div>
              <h3 className="font-medium flex items-center gap-2">
                {integration.name}
                {integration.isComingSoon && (
                  <Badge variant="secondary" className="text-xs">
                    Coming Soon
                  </Badge>
                )}
              </h3>
              <p className="text-muted-foreground text-xs capitalize">{integration.category}</p>
            </div>
          </div>
          
          {isConnected && (
            <div className="flex items-center gap-2">
              <div className={cn("w-2 h-2 rounded-full", statusInfo.color)} />
              <span className="text-xs text-muted-foreground">{statusInfo.label}</span>
            </div>
          )}
        </div>

        <p className="text-muted-foreground text-sm mb-4 line-clamp-2">
          {integration.description}
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          {integration.dataPoints.slice(0, 4).map((dp) => (
            <Badge 
              key={dp.id}
              variant="secondary"
              className="text-xs"
            >
              {dp.name}
            </Badge>
          ))}
          {integration.dataPoints.length > 4 && (
            <Badge variant="outline" className="text-xs">
              +{integration.dataPoints.length - 4} more
            </Badge>
          )}
        </div>

        {isConnected && lastSyncAt && (
          <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Last synced: {new Date(lastSyncAt).toLocaleString()}
          </p>
        )}

        <div className="flex gap-2">
          {integration.isComingSoon ? (
            <Button
              disabled
              variant="secondary"
              className="flex-1"
              data-testid={`button-coming-soon-${integration.id}`}
            >
              Coming Soon
            </Button>
          ) : isConnected ? (
            <>
              <Button
                onClick={() => onConfigure(integration.id)}
                variant="secondary"
                className="flex-1"
                data-testid={`button-configure-${integration.id}`}
              >
                <Settings className="w-4 h-4 mr-2" />
                Configure
              </Button>
              <Button
                onClick={() => onDisconnect(integration.id)}
                variant="outline"
                className="text-destructive hover:text-destructive"
                data-testid={`button-disconnect-${integration.id}`}
              >
                <Unplug className="w-4 h-4" />
              </Button>
            </>
          ) : (
            <Button
              onClick={() => onConnect(integration)}
              className="flex-1"
              data-testid={`button-connect-${integration.id}`}
            >
              {status === 'syncing' ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Link2 className="w-4 h-4 mr-2" />
              )}
              Connect
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default IntegrationCard;
