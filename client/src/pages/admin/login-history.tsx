import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  History, Search, CheckCircle, XCircle, Monitor, Smartphone, Tablet,
  Globe, RefreshCw, Filter
} from 'lucide-react';
import { api } from '@/api/client';
import { format, formatDistanceToNow } from 'date-fns';

function getDeviceIcon(deviceType: string | null) {
  switch (deviceType?.toLowerCase()) {
    case 'mobile':
      return Smartphone;
    case 'tablet':
      return Tablet;
    default:
      return Monitor;
  }
}

export default function LoginHistory() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data: loginHistory, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['/admin/login-history'],
    queryFn: () => api.admin.loginHistory(100),
    refetchInterval: 60000,
  });

  const filteredHistory = loginHistory?.filter((entry) => {
    const matchesSearch = entry.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || 
      (statusFilter === 'success' && entry.success) ||
      (statusFilter === 'failed' && !entry.success);
    return matchesSearch && matchesStatus;
  });

  const successCount = loginHistory?.filter(e => e.success).length ?? 0;
  const failedCount = loginHistory?.filter(e => !e.success).length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <History className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Login History</h1>
            <p className="text-muted-foreground text-sm">Track all user authentication attempts</p>
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
                <p className="text-sm text-muted-foreground">Total Logins</p>
                <p className="text-2xl font-bold">{loginHistory?.length ?? 0}</p>
              </div>
              <History className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Successful</p>
                <p className="text-2xl font-bold text-green-600">{successCount}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed</p>
                <p className="text-2xl font-bold text-red-600">{failedCount}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Authentication Log
              </CardTitle>
              <CardDescription>Complete record of all login attempts</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search by email..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64"
                  data-testid="input-search-history"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-36" data-testid="select-filter-status">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="success">Successful</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="table-login-history">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">User</th>
                    <th className="p-3 font-medium text-muted-foreground">Status</th>
                    <th className="p-3 font-medium text-muted-foreground">Device</th>
                    <th className="p-3 font-medium text-muted-foreground">Browser / OS</th>
                    <th className="p-3 font-medium text-muted-foreground">IP Address</th>
                    <th className="p-3 font-medium text-muted-foreground">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredHistory?.map((entry) => {
                    const DeviceIcon = getDeviceIcon(entry.device_type);
                    return (
                      <tr 
                        key={entry.id} 
                        className="border-b hover:bg-muted/50 transition-colors" 
                        data-testid={`row-login-${entry.id}`}
                      >
                        <td className="p-3">
                          <div className="flex items-center gap-3">
                            <Avatar className="h-9 w-9">
                              <AvatarFallback className={`text-sm ${entry.success ? 'bg-green-500/20 text-green-600' : 'bg-red-500/20 text-red-600'}`}>
                                {entry.email.charAt(0).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium text-sm">{entry.email}</p>
                              {entry.user_id && (
                                <p className="text-xs text-muted-foreground">ID: {entry.user_id}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            {entry.success ? (
                              <>
                                <CheckCircle className="h-4 w-4 text-green-500" />
                                <Badge variant="secondary" className="bg-green-500/20 text-green-600 border-0">
                                  Success
                                </Badge>
                              </>
                            ) : (
                              <>
                                <XCircle className="h-4 w-4 text-red-500" />
                                <Badge variant="secondary" className="bg-red-500/20 text-red-600 border-0">
                                  Failed
                                </Badge>
                              </>
                            )}
                          </div>
                          {!entry.success && entry.failure_reason && (
                            <p className="text-xs text-red-500 mt-1">{entry.failure_reason}</p>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <DeviceIcon className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm">{entry.device_type || 'Unknown'}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="text-sm">
                            <p>{entry.browser || 'Unknown'}</p>
                            <p className="text-xs text-muted-foreground">{entry.os || 'Unknown OS'}</p>
                          </div>
                        </td>
                        <td className="p-3">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {entry.ip_address || 'Unknown'}
                          </code>
                        </td>
                        <td className="p-3">
                          <div className="text-sm">
                            <p>{format(new Date(entry.created_at), 'MMM d, HH:mm')}</p>
                            <p className="text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(entry.created_at), { addSuffix: true })}
                            </p>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              
              {filteredHistory?.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No login history found</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
