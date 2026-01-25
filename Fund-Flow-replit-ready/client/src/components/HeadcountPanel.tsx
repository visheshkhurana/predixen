import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Users, UserPlus, DollarSign } from 'lucide-react';
import { formatCurrencyAbbrev } from '@/lib/utils';

interface HeadcountPanelProps {
  headcount: number | null;
  plannedHires: number | null;
  revenuePerEmployee: number | null;
  currency?: string;
}

export function HeadcountPanel({ 
  headcount, 
  plannedHires, 
  revenuePerEmployee,
  currency = 'USD' 
}: HeadcountPanelProps) {
  const formatCurrency = (value: number | null) => {
    if (value == null) return 'N/A';
    return formatCurrencyAbbrev(value, currency);
  };

  // Revenue per employee benchmarks
  const getRpeVariant = (): 'success' | 'warning' | 'default' => {
    if (revenuePerEmployee == null) return 'default';
    if (revenuePerEmployee >= 15000) return 'success';  // $15k+ per employee/month is good
    if (revenuePerEmployee >= 8000) return 'default';
    return 'warning';
  };

  return (
    <Card className="overflow-visible">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Users className="h-4 w-4 text-primary" />
          Headcount & Hiring
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="p-0.5">
                <HelpCircle className="h-3 w-3 text-muted-foreground" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="text-sm">
                Current team size, planned hiring, and revenue efficiency per employee.
              </p>
            </TooltipContent>
          </Tooltip>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-headcount">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <Users className="h-3 w-3" />
                  <span className="text-xs">Current</span>
                </div>
                <p className="text-2xl font-bold font-mono">{headcount ?? 'N/A'}</p>
                <p className="text-xs text-muted-foreground">employees</p>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <div className="space-y-2">
                <p className="font-medium">Current Headcount</p>
                <p className="text-xs">Total number of full-time equivalent employees on payroll.</p>
                <p className="text-xs text-primary">Benchmark: Early stage (1-10), Seed (5-20), Series A (15-50).</p>
                <p className="text-xs text-amber-400">Impact: Headcount is your largest expense. Each hire should unlock $3-5x their cost in value.</p>
              </div>
            </TooltipContent>
          </Tooltip>
          
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-planned-hires">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <UserPlus className="h-3 w-3" />
                  <span className="text-xs">Planned</span>
                </div>
                <p className="text-2xl font-bold font-mono text-emerald-500">+{plannedHires ?? 0}</p>
                <p className="text-xs text-muted-foreground">hires</p>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <div className="space-y-2">
                <p className="font-medium">Planned Hires</p>
                <p className="text-xs">Number of employees you plan to add in the next 6-12 months.</p>
                <p className="text-xs text-primary">Rule of thumb: Don't grow headcount faster than 50% per year unless you have strong revenue growth.</p>
                <p className="text-xs text-amber-400">Impact: Each new hire increases burn by $8-15K/month on average. Plan runway accordingly.</p>
              </div>
            </TooltipContent>
          </Tooltip>
          
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="text-center p-3 rounded-lg bg-muted/30 cursor-help hover:bg-muted/50 transition-colors" data-testid="metric-rev-per-emp">
                <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                  <DollarSign className="h-3 w-3" />
                  <span className="text-xs">Rev/Emp</span>
                </div>
                <p className={`text-2xl font-bold font-mono ${
                  getRpeVariant() === 'success' ? 'text-emerald-500' : 
                  getRpeVariant() === 'warning' ? 'text-amber-500' : ''
                }`}>
                  {formatCurrency(revenuePerEmployee)}
                </p>
                <p className="text-xs text-muted-foreground">monthly</p>
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <div className="space-y-2">
                <p className="font-medium">Revenue Per Employee</p>
                <p className="text-xs">Monthly revenue divided by total headcount - measures operational efficiency.</p>
                <p className="text-xs text-primary">Benchmark: $10K-15K/month is good. $20K+ is excellent. Below $8K needs attention.</p>
                <p className="text-xs text-amber-400">Impact: Low rev/emp suggests overstaffing or underpriced product. High rev/emp enables profitable scaling.</p>
              </div>
            </TooltipContent>
          </Tooltip>
        </div>

        {headcount && plannedHires && plannedHires > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">After hiring:</span>
              <Badge variant="secondary">
                {headcount + plannedHires} employees ({((plannedHires / headcount) * 100).toFixed(0)}% growth)
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
