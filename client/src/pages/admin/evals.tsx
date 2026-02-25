import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { 
  Play, RefreshCw, CheckCircle2, XCircle, Clock, AlertTriangle,
  TrendingUp, ChevronLeft, ChevronRight, FlaskConical, BarChart3
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/api/client';
import { getErrorMessage } from '@/lib/errors';

interface EvalRun {
  id: string;
  suite_name: string;
  inputs_json: Record<string, any> | null;
  outputs_json: Record<string, any> | null;
  scores_json: Record<string, {
    score: number;
    max_score: number;
    percentage: number;
    details: Record<string, any>;
  }> | null;
  overall_score: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface EvalSuite {
  name: string;
  description: string;
  metrics: string[];
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-600 border-yellow-500/30',
  running: 'bg-blue-500/20 text-blue-600 border-blue-500/30',
  completed: 'bg-green-500/20 text-green-600 border-green-500/30',
  failed: 'bg-red-500/20 text-red-600 border-red-500/30',
};

const STATUS_ICONS: Record<string, any> = {
  pending: Clock,
  running: RefreshCw,
  completed: CheckCircle2,
  failed: XCircle,
};

export default function EvalsPage() {
  const [page, setPage] = useState(1);
  const [selectedRun, setSelectedRun] = useState<EvalRun | null>(null);
  const [selectedSuite, setSelectedSuite] = useState<string>('copilot_quality');
  const perPage = 10;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: runsResponse, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['/admin/evals/runs', page],
    queryFn: () => api.admin.evals.runs(page, perPage),
  });

  const { data: suitesResponse } = useQuery({
    queryKey: ['/admin/evals/suites'],
    queryFn: () => api.admin.evals.suites(),
  });

  const runEvalMutation = useMutation({
    mutationFn: (suiteName: string) => api.admin.evals.run(suiteName),
    onSuccess: () => {
      toast({ title: 'Evaluation Started', description: 'The evaluation suite is now running.' });
      queryClient.invalidateQueries({ queryKey: ['/admin/evals/runs'] });
    },
    onError: (error: unknown) => {
      toast({ 
        title: 'Evaluation Failed', 
        description: getErrorMessage(error, 'Evaluation failed'),
        variant: 'destructive'
      });
    }
  });

  const runs = runsResponse?.runs || [];
  const total = runsResponse?.total || 0;
  const totalPages = Math.ceil(total / perPage);
  const suites = suitesResponse?.suites || [];

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-muted-foreground';
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const StatusIcon = ({ status }: { status: string }) => {
    const Icon = STATUS_ICONS[status] || Clock;
    return <Icon className={`h-4 w-4 ${status === 'running' ? 'animate-spin' : ''}`} />;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <FlaskConical className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-evals-title">Evaluation Dashboard</h1>
            <p className="text-muted-foreground text-sm">Run and monitor quality evaluation suites</p>
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

      <Card>
        <CardHeader>
          <CardTitle>Run New Evaluation</CardTitle>
          <CardDescription>Select an evaluation suite to test system quality</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">Evaluation Suite</label>
              <Select value={selectedSuite} onValueChange={setSelectedSuite}>
                <SelectTrigger data-testid="select-eval-suite">
                  <SelectValue placeholder="Select suite" />
                </SelectTrigger>
                <SelectContent>
                  {suites.map(suite => (
                    <SelectItem key={suite.name} value={suite.name}>
                      {suite.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {suites.find(s => s.name === selectedSuite) && (
                <p className="text-xs text-muted-foreground mt-1">
                  {suites.find(s => s.name === selectedSuite)?.description}
                </p>
              )}
            </div>
            <Button 
              onClick={() => runEvalMutation.mutate(selectedSuite)}
              disabled={runEvalMutation.isPending}
              data-testid="button-run-eval"
            >
              {runEvalMutation.isPending ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Run Evaluation
            </Button>
          </div>

          {suites.find(s => s.name === selectedSuite) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {suites.find(s => s.name === selectedSuite)?.metrics.map(metric => (
                <Badge key={metric} variant="outline">
                  {metric}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Evaluation History</CardTitle>
              <CardDescription>{total} total runs</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No evaluation runs yet. Run your first evaluation above.
            </div>
          ) : (
            <div className="space-y-2">
              {runs.map((run: EvalRun) => (
                <div 
                  key={run.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover-elevate cursor-pointer"
                  onClick={() => setSelectedRun(run)}
                  data-testid={`row-eval-${run.id}`}
                >
                  <div className="flex items-center gap-4">
                    <Badge className={STATUS_COLORS[run.status] || 'bg-muted'}>
                      <StatusIcon status={run.status} />
                      <span className="ml-1">{run.status}</span>
                    </Badge>
                    <span className="font-medium">{run.suite_name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    {run.overall_score !== null && (
                      <div className="flex items-center gap-2">
                        <TrendingUp className={`h-4 w-4 ${getScoreColor(run.overall_score)}`} />
                        <span className={`font-bold ${getScoreColor(run.overall_score)}`}>
                          {run.overall_score.toFixed(1)}%
                        </span>
                      </div>
                    )}
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
                    </span>
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

      <Dialog open={!!selectedRun} onOpenChange={() => setSelectedRun(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Evaluation Results
            </DialogTitle>
            <DialogDescription>
              {selectedRun?.suite_name} - {selectedRun?.status}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRun && (
            <ScrollArea className="max-h-[60vh]">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Badge className={STATUS_COLORS[selectedRun.status] || 'bg-muted'}>
                    <StatusIcon status={selectedRun.status} />
                    <span className="ml-1">{selectedRun.status}</span>
                  </Badge>
                  {selectedRun.overall_score !== null && (
                    <div className="text-right">
                      <span className={`text-2xl font-bold ${getScoreColor(selectedRun.overall_score)}`}>
                        {selectedRun.overall_score.toFixed(1)}%
                      </span>
                      <p className="text-xs text-muted-foreground">Overall Score</p>
                    </div>
                  )}
                </div>

                {selectedRun.error_message && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <div className="flex items-center gap-2 text-red-500">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="font-medium">Error</span>
                    </div>
                    <p className="text-sm mt-1">{selectedRun.error_message}</p>
                  </div>
                )}

                {selectedRun.scores_json && Object.keys(selectedRun.scores_json).length > 0 && (
                  <div>
                    <label className="text-sm font-medium mb-2 block">Metric Scores</label>
                    <div className="space-y-3">
                      {Object.entries(selectedRun.scores_json).map(([name, score]) => (
                        <div key={name} className="space-y-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium">{name}</span>
                            <span className={getScoreColor(score.percentage)}>
                              {score.percentage.toFixed(1)}%
                            </span>
                          </div>
                          <Progress value={score.percentage} className="h-2" />
                          {score.details && Object.keys(score.details).length > 0 && (
                            <p className="text-xs text-muted-foreground">
                              {JSON.stringify(score.details).slice(0, 100)}...
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-xs text-muted-foreground space-y-1">
                  <p>Started: {format(new Date(selectedRun.created_at), 'PPpp')}</p>
                  {selectedRun.completed_at && (
                    <p>Completed: {format(new Date(selectedRun.completed_at), 'PPpp')}</p>
                  )}
                </div>
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
