import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useMutation } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';
import { getErrorMessage } from '@/lib/errors';
import { Calendar, FileText, Loader2, CheckCircle } from 'lucide-react';

interface RaiseWindowData {
  optimal_start_month?: number;
  optimal_end_month?: number;
  estimated_duration_months?: number;
  optimalStartMonth?: number;
  optimalEndMonth?: number;
  estimatedDurationMonths?: number;
}

const timelineSteps = [
  { label: 'Prep', description: 'Materials & data room' },
  { label: 'Outreach', description: 'Investor introductions' },
  { label: 'Meetings', description: 'Partner meetings' },
  { label: 'Term Sheets', description: 'Negotiate terms' },
  { label: 'Close', description: 'Legal & wire' },
];

function getMonthName(monthOffset: number | null | undefined): string {
  if (monthOffset == null || isNaN(monthOffset) || !isFinite(monthOffset)) return 'TBD';
  const safeOffset = Math.max(0, Math.min(Math.round(monthOffset), 36));
  try {
    const now = new Date();
    now.setMonth(now.getMonth() + safeOffset);
    if (isNaN(now.getTime())) return 'TBD';
    return now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  } catch {
    return 'TBD';
  }
}

export function RaiseWindow({ raiseWindow: raw, companyId }: { raiseWindow: RaiseWindowData; companyId: number }) {
  const raiseWindow = {
    optimal_start_month: raw.optimal_start_month ?? raw.optimalStartMonth ?? 0,
    optimal_end_month: raw.optimal_end_month ?? raw.optimalEndMonth ?? 3,
    estimated_duration_months: raw.estimated_duration_months ?? raw.estimatedDurationMonths ?? 4,
  };
  const { toast } = useToast();
  const [onePagerContent, setOnePagerContent] = useState<string | null>(null);

  const generateOnePagerMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest('POST', `/api/companies/${companyId}/fundraising/one-pager`);
      return res.json();
    },
    onSuccess: (data: any) => {
      setOnePagerContent(data.markdown || data.content || data.one_pager || '');
      toast({ title: 'One-Pager Generated', description: 'Your investment memo has been generated.' });
    },
    onError: (error: unknown) => {
      toast({ title: 'Error', description: getErrorMessage(error, 'Failed to generate one-pager'), variant: 'destructive' });
    },
  });

  return (
    <div className="space-y-6">
      <Card data-testid="card-raise-window">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Optimal Raise Window
          </CardTitle>
          <CardDescription>Based on your current trajectory and metrics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-3 flex-wrap">
            <Badge variant="outline" data-testid="badge-raise-window-start">
              {getMonthName(raiseWindow.optimal_start_month)}
            </Badge>
            <span className="text-muted-foreground">to</span>
            <Badge variant="outline" data-testid="badge-raise-window-end">
              {getMonthName(raiseWindow.optimal_end_month)}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {raiseWindow.estimated_duration_months != null && !isNaN(raiseWindow.estimated_duration_months) 
                ? `(~${raiseWindow.estimated_duration_months} months)` 
                : ''}
            </span>
          </div>

          <div data-testid="display-fundraising-timeline">
            <h4 className="text-sm font-medium mb-4 text-muted-foreground">Fundraising Timeline</h4>
            <div className="flex items-start gap-0">
              {timelineSteps.map((step, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center" data-testid={`timeline-step-${idx}`}>
                  <div className="flex items-center w-full">
                    {idx > 0 && <div className="flex-1 h-0.5 bg-muted-foreground/20" />}
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <CheckCircle className="h-4 w-4 text-primary" />
                    </div>
                    {idx < timelineSteps.length - 1 && <div className="flex-1 h-0.5 bg-muted-foreground/20" />}
                  </div>
                  <span className="text-xs font-medium mt-2 text-center">{step.label}</span>
                  <span className="text-[10px] text-muted-foreground text-center hidden sm:block">{step.description}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="card-one-pager">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Investment One-Pager
          </CardTitle>
          <CardDescription>AI-generated investment memo based on your data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={() => generateOnePagerMutation.mutate()}
            disabled={generateOnePagerMutation.isPending}
            data-testid="button-generate-one-pager"
          >
            {generateOnePagerMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {generateOnePagerMutation.isPending ? 'Generating...' : 'Generate One-Pager'}
          </Button>

          {generateOnePagerMutation.isPending && (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          )}

          {onePagerContent && (
            <div
              className="max-w-none p-4 rounded-md border space-y-2"
              data-testid="display-one-pager-content"
            >
              {onePagerContent.split('\n').map((line: string, i: number) => {
                const trimmed = line.trim();
                if (trimmed.startsWith('### ')) return <h3 key={i} className="text-base font-semibold mt-4 mb-1">{trimmed.slice(4)}</h3>;
                if (trimmed.startsWith('## ')) return <h2 key={i} className="text-lg font-semibold mt-4 mb-1">{trimmed.slice(3)}</h2>;
                if (trimmed.startsWith('# ')) return <h1 key={i} className="text-xl font-bold mt-4 mb-2">{trimmed.slice(2)}</h1>;
                if (trimmed === '') return <div key={i} className="h-2" />;
                return <p key={i} className="text-sm text-muted-foreground">{trimmed}</p>;
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
