import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  RefreshCw, Shield, Eye, Clock, 
  AlertTriangle, ChevronLeft, ChevronRight, Hash, Zap
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { api } from '@/api/client';

interface LLMAuditLog {
  id: string;
  company_id: number | null;
  user_id: number | null;
  endpoint: string;
  model: string;
  pii_mode: string;
  prompt_hash: string;
  input_chars_original: number;
  input_chars_redacted: number;
  pii_findings_json: Array<{
    type: string;
    count: number;
    examples: string[];
    confidence: string;
  }> | null;
  redacted_prompt_preview: string | null;
  redacted_output_preview: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  created_at: string;
}

const PII_MODE_COLORS: Record<string, string> = {
  off: 'bg-red-500/20 text-red-600 border-red-500/30',
  standard: 'bg-blue-500/20 text-blue-600 border-blue-500/30',
  strict: 'bg-green-500/20 text-green-600 border-green-500/30',
};

export default function LLMAuditPage() {
  const [page, setPage] = useState(1);
  const [piiModeFilter, setPiiModeFilter] = useState<string>('all');
  const [selectedLog, setSelectedLog] = useState<LLMAuditLog | null>(null);
  const perPage = 20;

  const { data: logsResponse, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['/admin/llm-audit', page, piiModeFilter],
    queryFn: () => api.admin.llmAudit.list(page, perPage, piiModeFilter !== 'all' ? piiModeFilter : undefined),
  });

  const { data: stats } = useQuery({
    queryKey: ['/admin/llm-audit/stats/summary'],
    queryFn: () => api.admin.llmAudit.stats(),
  });

  const logs = logsResponse?.logs || [];
  const total = logsResponse?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  const getTotalPiiCount = (findings: LLMAuditLog['pii_findings_json']) => {
    if (!findings) return 0;
    return findings.reduce((sum, f) => sum + f.count, 0);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-llm-audit-title">LLM Audit Logs</h1>
            <p className="text-muted-foreground text-sm">Track all OpenAI API calls with privacy metrics</p>
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

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Requests</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold" data-testid="text-total-requests">{stats.total_requests.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Last {stats.period_days} days</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Tokens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(stats.total_tokens_in + stats.total_tokens_out).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">{stats.total_tokens_in.toLocaleString()} in / {stats.total_tokens_out.toLocaleString()} out</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Avg Latency</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.avg_latency_ms.toLocaleString()}ms</div>
              <p className="text-xs text-muted-foreground">Response time</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">PII Detected</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-amber-500" data-testid="text-pii-detected">{stats.requests_with_pii_detected.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">Requests with PII redacted</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Audit Log Entries</CardTitle>
              <CardDescription>{total} total entries</CardDescription>
            </div>
            <Select value={piiModeFilter} onValueChange={setPiiModeFilter}>
              <SelectTrigger className="w-40" data-testid="select-pii-mode-filter">
                <SelectValue placeholder="Filter by mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Modes</SelectItem>
                <SelectItem value="off">Off</SelectItem>
                <SelectItem value="standard">Standard</SelectItem>
                <SelectItem value="strict">Strict</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No audit logs found
            </div>
          ) : (
            <div className="space-y-2">
              {logs.map((log: LLMAuditLog) => (
                <div 
                  key={log.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover-elevate cursor-pointer"
                  onClick={() => setSelectedLog(log)}
                  data-testid={`row-audit-${log.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col">
                      <span className="font-medium text-sm">{log.endpoint}</span>
                      <span className="text-xs text-muted-foreground">{log.model}</span>
                    </div>
                    <Badge className={PII_MODE_COLORS[log.pii_mode] || 'bg-muted'}>
                      {log.pii_mode}
                    </Badge>
                    {getTotalPiiCount(log.pii_findings_json) > 0 && (
                      <Badge variant="outline" className="border-amber-500 text-amber-500">
                        <AlertTriangle className="h-3 w-3 mr-1" />
                        {getTotalPiiCount(log.pii_findings_json)} PII
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Hash className="h-3 w-3" />
                      {log.tokens_in || 0} / {log.tokens_out || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      {log.latency_ms || 0}ms
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                    </span>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Audit Log Details
            </DialogTitle>
            <DialogDescription>
              {selectedLog?.endpoint} - {selectedLog?.model}
            </DialogDescription>
          </DialogHeader>
          
          {selectedLog && (
            <ScrollArea className="max-h-[60vh]">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">PII Mode</label>
                    <Badge className={PII_MODE_COLORS[selectedLog.pii_mode] || 'bg-muted'}>
                      {selectedLog.pii_mode}
                    </Badge>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Prompt Hash</label>
                    <code className="text-xs block truncate">{selectedLog.prompt_hash}</code>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Input Characters</label>
                    <p className="text-sm">{selectedLog.input_chars_original} original / {selectedLog.input_chars_redacted} redacted</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Tokens</label>
                    <p className="text-sm">{selectedLog.tokens_in || 0} in / {selectedLog.tokens_out || 0} out</p>
                  </div>
                </div>

                {selectedLog.pii_findings_json && selectedLog.pii_findings_json.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">PII Findings</label>
                    <div className="mt-1 space-y-1">
                      {selectedLog.pii_findings_json.map((finding, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <Badge variant="outline">{finding.type}</Badge>
                          <span>{finding.count} found</span>
                          <span className="text-muted-foreground">({finding.confidence} confidence)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <label className="text-xs font-medium text-muted-foreground">Redacted Prompt Preview</label>
                  <pre className="mt-1 p-2 bg-muted rounded text-xs whitespace-pre-wrap max-h-40 overflow-auto">
                    {selectedLog.redacted_prompt_preview || 'No preview available'}
                  </pre>
                </div>

                <div>
                  <label className="text-xs font-medium text-muted-foreground">Redacted Output Preview</label>
                  <pre className="mt-1 p-2 bg-muted rounded text-xs whitespace-pre-wrap max-h-40 overflow-auto">
                    {selectedLog.redacted_output_preview || 'No preview available'}
                  </pre>
                </div>

                <div className="text-xs text-muted-foreground">
                  Created: {format(new Date(selectedLog.created_at), 'PPpp')}
                </div>
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
