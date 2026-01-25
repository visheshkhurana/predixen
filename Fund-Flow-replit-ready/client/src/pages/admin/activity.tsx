import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Activity, Search, Clock, RefreshCw, Filter, FileText,
  User, Building2, Settings, Shield, Zap, AlertTriangle
} from 'lucide-react';
import { api } from '@/api/client';
import { format, formatDistanceToNow } from 'date-fns';

const ACTION_ICONS: Record<string, any> = {
  user_suspended: AlertTriangle,
  user_activated: User,
  role_changed: Shield,
  company_created: Building2,
  settings_updated: Settings,
  subscription_updated: Zap,
};

const ACTION_COLORS: Record<string, string> = {
  user_suspended: 'bg-red-500/20 text-red-600',
  user_activated: 'bg-green-500/20 text-green-600',
  role_changed: 'bg-blue-500/20 text-blue-600',
  company_created: 'bg-purple-500/20 text-purple-600',
  settings_updated: 'bg-yellow-500/20 text-yellow-600',
  subscription_updated: 'bg-indigo-500/20 text-indigo-600',
};

export default function ActivityLogs() {
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState<string>('all');

  const { data: auditLogs, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['/admin/audit-logs'],
    queryFn: () => api.admin.auditLogs(100),
  });

  const uniqueActions = Array.from(new Set(auditLogs?.map(log => log.action) || []));

  const filteredLogs = auditLogs?.filter((log) => {
    const matchesSearch = 
      (log.user_email?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAction = actionFilter === 'all' || log.action === actionFilter;
    return matchesSearch && matchesAction;
  });

  const getActionIcon = (action: string) => {
    return ACTION_ICONS[action] || Activity;
  };

  const getActionColor = (action: string) => {
    return ACTION_COLORS[action] || 'bg-muted text-muted-foreground';
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Activity Logs</h1>
            <p className="text-muted-foreground text-sm">Audit trail of all admin actions</p>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => refetch()}
          disabled={isFetching}
          data-testid="button-refresh"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Actions</p>
                <p className="text-2xl font-bold">{auditLogs?.length ?? 0}</p>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Unique Actions</p>
                <p className="text-2xl font-bold">{uniqueActions.length}</p>
              </div>
              <Zap className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Today's Actions</p>
                <p className="text-2xl font-bold">
                  {auditLogs?.filter(log => {
                    const today = new Date();
                    const logDate = new Date(log.created_at);
                    return logDate.toDateString() === today.toDateString();
                  }).length ?? 0}
                </p>
              </div>
              <Clock className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Audit Trail
              </CardTitle>
              <CardDescription>Complete record of administrative actions</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search logs..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64"
                  data-testid="input-search-logs"
                />
              </div>
              <Select value={actionFilter} onValueChange={setActionFilter}>
                <SelectTrigger className="w-44" data-testid="select-filter-action">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Action type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  {uniqueActions.map((action) => (
                    <SelectItem key={action} value={action}>
                      {action.replace(/_/g, ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : filteredLogs && filteredLogs.length > 0 ? (
            <div className="space-y-3">
              {filteredLogs.map((log) => {
                const ActionIcon = getActionIcon(log.action);
                const actionColor = getActionColor(log.action);
                
                return (
                  <div 
                    key={log.id} 
                    className="flex items-start gap-4 p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                    data-testid={`log-entry-${log.id}`}
                  >
                    <div className={`h-10 w-10 rounded-full flex items-center justify-center ${actionColor}`}>
                      <ActionIcon className="h-5 w-5" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm">{log.user_email || 'System'}</span>
                        <Badge variant="secondary" className="text-xs">
                          {log.action.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      
                      <div className="text-sm text-muted-foreground">
                        {log.resource_type && (
                          <span>
                            on <span className="font-medium">{log.resource_type}</span>
                            {log.resource_id && ` #${log.resource_id}`}
                          </span>
                        )}
                      </div>
                      
                      {log.details && (
                        <div className="mt-2 p-2 rounded bg-muted/50">
                          <pre className="text-xs text-muted-foreground overflow-x-auto">
                            {typeof log.details === 'object' 
                              ? JSON.stringify(log.details, null, 2)
                              : String(log.details)
                            }
                          </pre>
                        </div>
                      )}
                    </div>
                    
                    <div className="text-right shrink-0">
                      <p className="text-sm">{format(new Date(log.created_at), 'MMM d, HH:mm')}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                      </p>
                      {log.ip_address && (
                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded mt-1 inline-block">
                          {log.ip_address}
                        </code>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium">No activity logs found</p>
              <p className="text-sm">Admin actions will appear here</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
